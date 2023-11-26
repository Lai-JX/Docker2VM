from __future__ import print_function
import time
import math
import yaml
import munch

#parse args
import argparse
import copy
import os

# import utils
import flags

# import log

#parse input arguments
flags.DEFINE_string('username', 'myubuntu', 'The name of user')
flags.DEFINE_string('image','ubuntu-ssh:v1', 'The image to create VM, default is ubuntu22.04 with ssh')
flags.DEFINE_string('password', '123456', 'The password of you VM(root)')
flags.DEFINE_string('cmd', '', 'Commands to run after the VM starts（end with ;）')
flags.DEFINE_string('path', '/myubuntu', 'The directory of the persistent storage in the VM')
flags.DEFINE_integer('num_gpu', 1, 'The number of GPU')
flags.DEFINE_string('cpu', 1, 'The number of CPU cores(1 CPU = 1000m CPU)')
flags.DEFINE_string('memory', '1Gi', 'Memory size')
flags.DEFINE_boolean('use_master', False, 'Whether deploy the VM in master node')

flags.DEFINE_version('0.1')

FLAGS = flags.FLAGS


def create_container(template_yaml):
    container = munch.Munch.fromDict(template_yaml[0])  # 转化为类
    service = munch.Munch.fromDict(template_yaml[1])

    # 设置pod的name和label
    container.metadata.name = FLAGS.username
    container.metadata.labels.user = FLAGS.username

    # 设置存储卷
    container.spec.volumes[0].name = FLAGS.username + '-volumes'
    container.spec.volumes[0].hostPath.path = '/home/VM/' + FLAGS.username

    # 设置镜像
    container.spec.containers[0].image = FLAGS.image
    container.spec.containers[0].name = FLAGS.username  # 容器名

    # 设置密码和启动命令
    container.spec.containers[0].args = [ 'apt update; echo y|apt install openssh-server; echo -e "{}\\n{}\\n"|passwd;  service ssh restart; {} while true; do sleep 3600; done;'.format(FLAGS.password, FLAGS.password, FLAGS.cmd) ]

    # 挂载
    container.spec.containers[0].volumeMounts[0].mountPath = FLAGS.path
    container.spec.containers[0].volumeMounts[0].name = container.spec.volumes[0].name 

    # 资源
    container.spec.containers[0].resources.requests['nvidia.com/gpu'] = FLAGS.num_gpu
    container.spec.containers[0].resources.requests['cpu'] = FLAGS.cpu
    container.spec.containers[0].resources.requests['memory'] = FLAGS.memory
    container.spec.containers[0].resources.limits = copy.deepcopy(container.spec.containers[0].resources.requests)

    # 是否在master上运行
    if FLAGS.use_master:
        container.spec.tolerations.append({'key':'node-role.kubernetes.io/master', 'operator': 'Exists', 'effect':'NoSchedule'})


    # 设置service
    service.metadata.name = FLAGS.username + '-ssh'
    service.spec.selector.user = FLAGS.username

    # 保存yaml文件
    save_path = './pod_config/{}.yaml'.format(FLAGS.username)
    with open(save_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump_all(documents=[container, service], stream=f, allow_unicode=True)
    return save_path, container.metadata.name, service.metadata.name

def main():
    with open('./template.yaml', 'r', encoding='utf-8') as f:
        template_yaml = yaml.load_all(f.read(), Loader=yaml.FullLoader)
    template_yaml = list(template_yaml)             # 包括pod和service

    # 根据要求创建容器（VM）
    path, pod_name, svc_name = create_container(template_yaml)

    # 用户访问的端口
    port = 32322    # 先写死

    # 启动容器
    os.system('kubectl apply -f {}'.format(path))
    print("----------------------\n \
          Wait for the creation to complete...\n \
          This can take a long time, depending on whether there is SSH inside the image...")
    while True:
        time.sleep(1)
        res = os.popen("kubectl get pod -A | grep {}".format(pod_name))   #   | awk '{print $1}'
        status = res.read().split()[3]
        if status == 'Running':
            break
    print("----------------------\n Finished Successfully!")

    # 开启端口
    os.system('kubectl port-forward --address 0.0.0.0 svc/{} {}:22 >> ./log/{} 2>&1 &'.format(svc_name,port,pod_name))    # 获取这条命令的进程（ljx-ssh记得替换）：ps -ef | grep forward | grep svc | grep ljx-ssh



if __name__ == '__main__':
    # print('Hello world %d' % 2)
    main()