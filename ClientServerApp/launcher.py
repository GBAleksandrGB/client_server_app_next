import os
import subprocess
import sys


def main():
    """
    Функция, запускающая сервер и два тестовых клиента.
    Пароль клиента по умолчанию: 123456.
    """
    process = []

    PYTHON_PATH = sys.executable
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))

    while True:
        action = input(
            'Выберите действие: q - выход , s - запустить сервер, k - запустить клиенты x - закрыть все окна:')
        if action == 'q':
            break
        elif action == 's':
            process.append(subprocess.Popen(f'{PYTHON_PATH} {BASE_PATH}/server.py',
                                            creationflags=subprocess.CREATE_NEW_CONSOLE))
        elif action == 'k':
            clients_count = int(input('Введите количество тестовых клиентов для запуска: '))
            for i in range(clients_count):
                process.append(subprocess.Popen(f'{PYTHON_PATH} {BASE_PATH}/client.py -n test{i + 1} -p 123456',
                                                creationflags=subprocess.CREATE_NEW_CONSOLE))
        elif action == 'x':
            while process:
                process.pop().kill()


if __name__ == '__main__':
    main()
