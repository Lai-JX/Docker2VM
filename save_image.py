import sys
from os.path import abspath, join, dirname
# sys.path.insert(0, abspath(dirname(__file__)))
# sys.path.insert(0,'/home/jxlai/k8s')

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from utils import *

def save_image(ssh, image_pre, container):
    # 更新image版本
    image = manipulate_string(image_pre)
    command_to_run = '{} docker commit $({} docker ps --filter ancestor={} --format "{{{{.Names}}}}" | grep {}) {}'.format(ssh, ssh, image_pre, container, image)
    # print('run:', command_to_run)
    # 调用终端命令
    output = run_command(command_to_run)
    if output is not None:
        print("Command output:")
        print(output)
        return True
    


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):               # 保存镜像
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        # print(query_params)

        # 获取参数
        if 'container' in query_params and 'image' in query_params:
            container = query_params['container'][0]
            image_pre = query_params['image'][0]

            # TODO
            # 查询此容器在哪个node上运行，这里先写死
            ssh = 'ssh jxlai@192.168.1.107'
            
            output = save_image(ssh, image_pre, container)
            
            if output:
                self.send_response(200)
                # self.send_header('Content-type', 'text/html')
                self.end_headers()
        else:
            print('parameters errors')
            self.wfile.write(b"not enough parameters")
        
          
        
        
        

        

def save_image_serve(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting server on port {port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    save_image_serve()
