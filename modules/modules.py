import re
import subprocess
import platform
import ipaddress
from tabulate import tabulate


def host_ping(args):
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    for arg in args:
        command = ['ping', param, '1', str(arg)]
        proc = subprocess.run(command, stdout=subprocess.PIPE)
        print(f'{arg} доступен' if proc.returncode == 0 else f'{arg} недоступен')


if __name__ == '__main__':
    ipv4_pattern = re.compile(r'([0-9]{1,3}[.]){3}[0-9]{1,3}')
    ipv6_pattern = re.compile(r'((^|:)([0-9a-fA-F]{0,4})){1,8}')
    user_input = input('Введите имя или адрес одного или нескольких хостов через запятую: ')
    hosts = [item if not re.match(ipv4_pattern, item) or not re.match(ipv6_pattern, item)
             else ipaddress.ip_address(item) for item in user_input.split(', ')]
    host_ping(hosts)


def host_range_ping(args):
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    for arg in args:
        command = ['ping', param, '1', str(arg)]
        proc = subprocess.run(command, stdout=subprocess.PIPE)
        print(f'{arg} доступен' if proc.returncode == 0 else f'{arg} недоступен')


if __name__ == '__main__':
    user_input = input('Введите начало и конец диапазона адресов в сети через запятую: ')
    start_addr, end_addr = user_input.split(', ')
    start_addr = ipaddress.ip_address(start_addr)
    end_addr = ipaddress.ip_address(end_addr)
    int_data = [_ for _ in range(int(start_addr), int(end_addr))]
    hosts = [ipaddress.ip_address(_) for _ in int_data]
    host_range_ping(hosts)


def host_range_ping_tab(args):
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    reachable = []
    unreachable = []
    for arg in args:
        command = ['ping', param, '1', str(arg)]
        proc = subprocess.run(command, stdout=subprocess.PIPE)
        reachable.append(arg) if proc.returncode == 0 else unreachable.append(arg)
    data = {'Reachable': reachable, 'Unreachable': unreachable}
    print(tabulate(data, headers='keys', tablefmt='grid'))


if __name__ == '__main__':
    user_input = input('Введите начало и конец диапазона адресов в сети через запятую: ')
    start_addr, end_addr = user_input.split(', ')
    start_addr = ipaddress.ip_address(start_addr)
    end_addr = ipaddress.ip_address(end_addr)
    int_data = [_ for _ in range(int(start_addr), int(end_addr))]
    hosts = [ipaddress.ip_address(_) for _ in int_data]
    host_range_ping_tab(hosts)
