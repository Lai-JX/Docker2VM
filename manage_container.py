
import yaml
import munch
import copy
import os
import time

def config_container(config):
    with open('template/template.yaml', 'r', encoding='utf-8') as f:
        template_yaml = yaml.load_all(f.read(), Loader=yaml.FullLoader)
    template_yaml = list(template_yaml)             # 包括pod和service

    container = munch.Munch.fromDict(template_yaml[0])  # 转化为类
    service = munch.Munch.fromDict(template_yaml[1])

    # 设置pod的name和label
    container.metadata.name = config['name']
    container.metadata.labels.user = config['name']

    # 设置存储卷
    container.spec.volumes[0].name = config['name'] + '-volumes'
    container.spec.volumes[0].hostPath.path = '/home/VM/' + config['name']

    # 设置镜像
    container.spec.containers[0].image = config['image']
    container.spec.containers[0].name = config['name']  # 容器名

    container.spec.containers[0].lifecycle.preStop.httpGet.path = f'?container={config["name"]}&image={config["image"]}'    # 传递参数，便于钩子函数保存镜像

    # 设置密码和启动命令，以及退出前保存镜像
    tmp = 'curl "http://192.168.1.104:8000/' + f'?container={config["name"]}&image={config["image"]}";'                        # 通知保存镜像

    file_path = 'template/base_cmd.txt'
    with open(file_path, 'r') as file:
        base_cmd = file.read().replace('\n', ' ')   # 包含更新源、更新环境变量的代码

    container.spec.containers[0].args = [ base_cmd + ' echo -e "{}\\n{}\\n"|passwd;  service ssh restart; {} while true; do sleep 3600; done; {}'.format(config['password'], config['password'], config['cmd'], tmp) ]
    # container.spec.containers[0].args = [ 'apt update; echo y|apt install openssh-server; echo -e "{}\\n{}\\n"|passwd;  service ssh restart; {} while true; do sleep 3600; done; '.format(config['password'], config['password'], config['cmd']) ]

    # 挂载
    container.spec.containers[0].volumeMounts[0].mountPath = config['path']
    container.spec.containers[0].volumeMounts[0].name = container.spec.volumes[0]['name'] 

    # 资源
    container.spec.containers[0].resources.requests['nvidia.com/gpu'] = config['num_gpu']
    container.spec.containers[0].resources.requests['nvidia.com/gpumem'] = config['gpumem']
    container.spec.containers[0].resources.requests['nvidia.com/gpucores'] = config['gpucores']
    container.spec.containers[0].resources.requests['cpu'] = config['cpu']
    container.spec.containers[0].resources.requests['memory'] = config['memory']
    container.spec.containers[0].resources.limits = copy.deepcopy(container.spec.containers[0].resources.requests)

    # 是否在master上运行
    if config['use_master']:
        container.spec.tolerations.append({'key':'node-role.kubernetes.io/master', 'operator': 'Exists', 'effect':'NoSchedule'})

    # 设置service
    service.metadata.name = config['name'] + '-ssh'
    service.spec.selector.user = config['name']
    service.spec.ports[0].nodePort=config['port']

    # 保存yaml文件
    save_path = './pod_config/{}.yaml'.format(config['name'])
    with open(save_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump_all(documents=[container, service], stream=f, allow_unicode=True)
    return save_path, container.metadata.name, service.metadata.name

def start_container(path, pod_name):
    os.system('kubectl apply -f {}'.format(path))
    print("----------------------\n \
          Wait for the creation to complete...\n \
          It can take a long time before the system can connect, depending on whether there is SSH inside the image and whether the network is stable or not...")
    while True:
        time.sleep(1)
        res = os.popen("kubectl get pod -A | grep {}".format(pod_name))   #   | awk '{print $1}'
        print(res)
        res = res.read().split()
        if len(res)>0 and res[3] == 'Running':
            break
    print("----------------------\n Finished Successfully!")

def create_container(config):

    # 根据要求创建容器（VM）
    path, pod_name, svc_name = config_container(config)

    # 启动容器
    start_container(path, pod_name)

    # 开启端口(其实可以用nodeport)
    # os.system('nohup kubectl port-forward --address 0.0.0.0 svc/{} {}:22 >> ./log/{} 2>&1 &'.format(svc_name,port,pod_name))    # 获取这条命令的进程（ljx-ssh记得替换）：ps -ef | grep forward | grep svc | grep ljx-ssh
    # nohup kubectl port-forward --address 0.0.0.0 svc/kube-prometheus-stack-1701401149-grafana  -n prometheus 32323:80 >> ./k8s/Docker_VM/log/grafana.txt  2>&1 &
if __name__ == '__main__':
    file_path = 'template/cmd.txt'
    with open(file_path, 'r') as file:
        file_content = file.read().replace('\n', ' ') 

    print(file_content.replace('\n', ' '))  # 打印文件内容（作为字符串）