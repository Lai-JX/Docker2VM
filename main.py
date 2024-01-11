from __future__ import print_function


import argparse
import threading


from utils import *
from manage_image import *
from manage_container import *




if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--name', type=str, default='myubuntu', help='The name of user')
    parser.add_argument('--image', type=str, default='ubuntu-ssh:v1', help='The image to create VM, default is ubuntu22.04 with ssh')
    parser.add_argument('--password', type=str, default='123456', help='The password of you VM(root)')
    parser.add_argument('--cmd', type=str, default='', help='Commands to run after the VM starts（end with ;）') 
    parser.add_argument('--path', type=str, default='/myubuntu', help='The directory of the persistent storage in the VM')
    parser.add_argument('--num_gpu', type=int, default=1, help='The number of vGPU')
    parser.add_argument('--gpumem', type=int, default=3000, help='Memory per vGPU(M)')
    parser.add_argument('--gpucores', type=int, default=30, help='The capacity of each vGPU(%%)')
    parser.add_argument('--cpu', type=int, default=1, help='The number of CPU cores(1 CPU = 1000m CPU)')
    parser.add_argument('--port', type=int, default=32324, help='The port to communicate')
    parser.add_argument('--duration', type=int, default=3600, help='The duration of container(s)')
    parser.add_argument('--memory', type=str, default='1Gi', help='Memory size')
    parser.add_argument('--is_VM',
                              nargs='?',
                              const=True,
                              help='deploy VM or Task',
                              default='t',
                              type=str2bool)
    parser.add_argument('--use_master',
                              nargs='?',
                              const=False,
                              help='Whether deploy the VM in master node',
                              default='f',
                              type=str2bool)
    args = parser.parse_args()

    config = vars(args)
    # config['port'] = 32325    #  先写死(这个应该是系统指定而不是用户指定)

    # 创建job (VM or Task)
    if config['is_VM']:
        config['backoffLimit'] = 0 
        config['cmd'] = 'sleep ' + str(config['duration'])
        print("create VM")
    else:
        config['backoffLimit'] = 3
        print("create Task")
    create_job(config)

    exit(0)
    # 启动提交镜像的服务
    server_thread = threading.Thread(
        target=save_image_serve,
        )
    server_thread.setDaemon(True)
    server_thread.start()

    # 等待服务线程完成后再退出
    server_thread.join()