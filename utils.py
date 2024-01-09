import subprocess

# 判断参数是否表示真
def str2bool(v):
    return v.lower() in ('true', 't', '1')

# 执行终端命令
def run_command(command):
    try:
        # 执行命令并等待返回结果
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        # 如果命令执行失败，捕获异常并处理
        print(f"Command execution failed with error: {e}")
        return None

# 更新镜像版本号
def manipulate_string(input_string):
    # 如果字符串为空，则直接返回 '-1'
    if not input_string:
        return '-1'

    # 获取字符串最后一个字符
    last_character = input_string[-1]

    # 判断最后一个字符是否为数字
    if last_character.isdigit():
        # 如果是数字，则将最后一个字符转换为整数后加 1
        new_last_character = str(int(last_character) + 1)
        # 替换字符串中的最后一个字符为加 1 后的数字
        manipulated_string = input_string[:-1] + new_last_character
    else:
        # 如果不是数字，则在字符串末尾拼接 '-1'
        manipulated_string = input_string + '-1'

    return manipulated_string

if __name__ == '__main__':
    # 测试函数
    input_str = "abcd"  # 替换为您想要测试的字符串
    result = manipulate_string(input_str)
    print(f"Manipulated string: {result}")
