from __future__ import print_function
import time
import math
import yaml
import munch

#parse args
import argparse
import copy
import os

from utils import *
from save_image import *
import threading

import sys
from os.path import abspath, join, dirname
sys.path.insert(0, abspath(dirname(__file__)))



def create_container(config):
    with open('./template.yaml', 'r', encoding='utf-8') as f:
        template_yaml = yaml.load_all(f.read(), Loader=yaml.FullLoader)
    template_yaml = list(template_yaml)             # 包括pod和service

    container = munch.Munch.fromDict(template_yaml[0])  # 转化为类
    service = munch.Munch.fromDict(template_yaml[1])

    # 设置pod的name和label
    container.metadata.name = config['username']
    container.metadata.labels.user = config['username']

    # 设置存储卷
    container.spec.volumes[0].name = config['username'] + '-volumes'
    container.spec.volumes[0].hostPath.path = '/home/VM/' + config['username']

    # 设置镜像
    container.spec.containers[0].image = config['image']
    container.spec.containers[0].name = config['username']  # 容器名

    container.spec.containers[0].lifecycle.preStop.httpGet.path = f'?container={config["username"]}&image={config["image"]}'    # 传递参数，便于钩子函数保存镜像

    # 设置密码和启动命令，以及退出前保存镜像
    tmp = 'curl "http://192.168.1.104:8000/' + f'?container={config["username"]}&image={config["image"]}";'                        # 通知保存镜像
    container.spec.containers[0].args = [ 'apt update; echo y|apt install openssh-server; echo -e "{}\\n{}\\n"|passwd;  service ssh restart; {} while true; do sleep 3600; done; {}'.format(config['password'], config['password'], config['cmd'], tmp) ]
    # container.spec.containers[0].args = [ 'apt update; echo y|apt install openssh-server; echo -e "{}\\n{}\\n"|passwd;  service ssh restart; {} while true; do sleep 3600; done; '.format(config['password'], config['password'], config['cmd']) ]

    # 挂载
    container.spec.containers[0].volumeMounts[0].mountPath = config['path']
    container.spec.containers[0].volumeMounts[0].name = container.spec.volumes[0]['name'] 

    # 资源
    container.spec.containers[0].resources.requests['nvidia.com/gpu'] = config['num_gpu']
    container.spec.containers[0].resources.requests['cpu'] = config['cpu']
    container.spec.containers[0].resources.requests['memory'] = config['memory']
    container.spec.containers[0].resources.limits = copy.deepcopy(container.spec.containers[0].resources.requests)

    # 是否在master上运行
    if config['use_master']:
        container.spec.tolerations.append({'key':'node-role.kubernetes.io/master', 'operator': 'Exists', 'effect':'NoSchedule'})

    # 设置service
    service.metadata.name = config['username'] + '-ssh'
    service.spec.selector.user = config['username']
    service.spec.ports[0].nodePort=config['port']

    # 保存yaml文件
    save_path = './pod_config/{}.yaml'.format(config['username'])
    with open(save_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump_all(documents=[container, service], stream=f, allow_unicode=True)
    return save_path, container.metadata.name, service.metadata.name

def start_container(path, pod_name):
    os.system('kubectl apply -f {}'.format(path))
    print("----------------------\n \
          Wait for the creation to complete...\n \
          This can take a long time, depending on whether there is SSH inside the image and whether the network is stable or not...")
    while True:
        time.sleep(1)
        res = os.popen("kubectl get pod -A | grep {}".format(pod_name))   #   | awk '{print $1}'
        print(res)
        res = res.read().split()
        if len(res)>0 and res[3] == 'Running':
            break
    print("----------------------\n Finished Successfully!")

def main(config):

    # 根据要求创建容器（VM）
    path, pod_name, svc_name = create_container(config)

    # 启动容器
    start_container(path, pod_name)

    # 开启端口(其实可以用nodeport)
    # os.system('nohup kubectl port-forward --address 0.0.0.0 svc/{} {}:22 >> ./log/{} 2>&1 &'.format(svc_name,port,pod_name))    # 获取这条命令的进程（ljx-ssh记得替换）：ps -ef | grep forward | grep svc | grep ljx-ssh
    # nohup kubectl port-forward --address 0.0.0.0 svc/kube-prometheus-stack-1701401149-grafana  -n prometheus 32323:80 >> ./k8s/Docker_VM/log/grafana.txt  2>&1 &


if __name__ == '__main__':
    # print('Hello world %d' % 2)
    #parse input arguments


    parser = argparse.ArgumentParser()
    parser.add_argument('--username', type=str, default='myubuntu', help='The name of user')
    parser.add_argument('--image', type=str, default='ubuntu-ssh:v1', help='The image to create VM, default is ubuntu22.04 with ssh')
    parser.add_argument('--password', type=str, default='123456', help='The password of you VM(root)')
    parser.add_argument('--cmd', type=str, default='', help='Commands to run after the VM starts（end with ;）') 
    parser.add_argument('--path', type=str, default='/myubuntu', help='The directory of the persistent storage in the VM')
    parser.add_argument('--num_gpu', type=int, default=1, help='The number of GPU')
    parser.add_argument('--cpu', type=int, default=1, help='The number of CPU cores(1 CPU = 1000m CPU)')
    parser.add_argument('--memory', type=str, default='1Gi', help='Memory size')
    
    parser.add_argument('--use_master',
                              nargs='?',
                              const=False,
                              help='Whether deploy the VM in master node',
                              default='f',
                              type=str2bool)
    args = parser.parse_args()

    config = vars(args)
    config['port'] = 32324    #  先写死(这个应该是系统指定而不是用户指定)
    main(config)
    server_thread = threading.Thread(
        target=save_image_serve,
        )
    server_thread.setDaemon(True)
    server_thread.start()
    # 等待服务线程完成后再退出
    server_thread.join()