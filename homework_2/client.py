"""Программа-клиент"""

import argparse
import json
import logging
import socket
import sys
import threading
import time
import dis

from homework_2.common.decos import Log
from homework_2.common.errors import IncorrectDataRecivedError, ReqFieldMissingError, ServerError
from homework_2.common.utils import get_message, send_message
from homework_2.common.variables import ACTION, USER, TIME, ERROR, EXIT, ACCOUNT_NAME, MESSAGE, SENDER, MESSAGE_TEXT, \
    DESTINATION, PRESENCE, RESPONSE, DEFAULT_PORT, DEFAULT_IP_ADDRESS

LOGGER = logging.getLogger('client')


class ClientVerifier(type):
    # Вызывается для создания экземпляра класса, перед вызовом __init__
    def __init__(cls, future_class_name, future_class_parents, future_class_attrs):

        selection = []

        for func in cls.__dict__:
            try:
                ret = dis.get_instructions(cls.__dict__[func])
            except TypeError:
                pass
            else:
                selection = [el.argval for el in ret
                             if el.argval in ['listen', 'accept', 'SOCK_STREAM']]

        if 'listen' in selection or 'accept' in selection:
            raise AttributeError(f"Недопустимый метод 'listen' или 'accept' в сокете")

        if 'SOCK_STREAM' not in selection:
            raise AttributeError(f"Тип сокета не TCP")

        for attr in future_class_attrs.values():
            if issubclass(type(attr), socket.socket):
                raise AttributeError(f'Недопустимый атрибут класса {cls.__name__}: {attr}')

        super(ClientVerifier, cls).__init__(future_class_name,
                                            future_class_parents,
                                            future_class_attrs)


class Client(metaclass=ClientVerifier):
    def __init__(self):
        self.server_address, self.server_port, self.client_name = Client.arg_parser()

    @staticmethod
    @Log
    def create_exit_message(account_name):
        """Функция создаёт словарь с сообщением о выходе"""
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: account_name
        }

    @staticmethod
    @Log
    def message_from_server(sock, my_username):
        """Функция - обработчик сообщений других пользователей, поступающих с сервера"""
        while True:
            try:
                message = get_message(sock)
                if ACTION in message and message[ACTION] == MESSAGE and \
                        SENDER in message and DESTINATION in message \
                        and MESSAGE_TEXT in message and message[DESTINATION] == my_username:
                    print(f'\nПолучено сообщение от пользователя {message[SENDER]}:'
                          f'\n{message[MESSAGE_TEXT]}')
                    LOGGER.info(f'Получено сообщение от пользователя {message[SENDER]}:'
                                f'\n{message[MESSAGE_TEXT]}')
                else:
                    LOGGER.error(f'Получено некорректное сообщение с сервера: {message}')
            except IncorrectDataRecivedError:
                LOGGER.error(f'Не удалось декодировать полученное сообщение.')
            except (OSError, ConnectionError, ConnectionAbortedError,
                    ConnectionResetError, json.JSONDecodeError):
                LOGGER.critical(f'Потеряно соединение с сервером.')
                break

    @staticmethod
    @Log
    def create_message(sock, account_name='Guest'):
        """
        Функция запрашивает кому отправить сообщение и само сообщение,
        и отправляет полученные данные на сервер
        """
        to_user = input('Введите получателя сообщения: ')
        message = input('Введите сообщение для отправки: ')
        message_dict = {
            ACTION: MESSAGE,
            SENDER: account_name,
            DESTINATION: to_user,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')
        try:
            send_message(sock, message_dict)
            LOGGER.info(f'Отправлено сообщение для пользователя {to_user}')
        except Exception as e:
            print(e)
            LOGGER.critical('Потеряно соединение с сервером.')
            sys.exit(1)

    @staticmethod
    @Log
    def user_interactive(sock, username):
        """Функция взаимодействия с пользователем, запрашивает команды, отправляет сообщения"""

        while True:
            command = input('Введите команду: ')
            if command == 'message':
                Client.create_message(sock, username)
            elif command == 'help':
                Client.print_help()
            elif command == 'exit':
                send_message(sock, Client.create_exit_message(username))
                print('Завершение соединения.')
                LOGGER.info('Завершение работы по команде пользователя.')
                # Задержка неоходима, чтобы успело уйти сообщение о выходе
                time.sleep(0.5)
                break
            else:
                print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')

    @staticmethod
    @Log
    def create_presence(account_name):
        """Функция генерирует запрос о присутствии клиента"""
        out = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: account_name
            }
        }
        LOGGER.debug(f'Сформировано {PRESENCE} сообщение для пользователя {account_name}')
        return out

    @staticmethod
    def print_help():
        """Функция выводящяя справку по использованию"""
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')

    @staticmethod
    @Log
    def process_response_ans(message):
        """
        Функция разбирает ответ сервера на сообщение о присутствии,
        возвращает 200 если все ОК или генерирует исключение при ошибке
        """
        LOGGER.debug(f'Разбор приветственного сообщения от сервера: {message}')
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return '200 : OK'
            elif message[RESPONSE] == 400:
                raise ServerError(f'400 : {message[ERROR]}')
        raise ReqFieldMissingError(RESPONSE)

    @staticmethod
    @Log
    def arg_parser():
        """Парсер аргументов коммандной строки"""
        parser = argparse.ArgumentParser()
        parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
        parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
        parser.add_argument('-n', '--name', default=None, nargs='?')
        namespace = parser.parse_args(sys.argv[1:])
        server_address = namespace.addr
        server_port = namespace.port
        client_name = namespace.name

        if not 1023 < server_port < 65536:
            LOGGER.critical(
                f'Попытка запуска клиента с неподходящим номером порта: {server_port}. '
                f'Допустимы адреса с 1024 до 65535. Клиент завершается.')
            sys.exit(1)

        return server_address, server_port, client_name

    def main(self):
        print(f'Консольный месседжер. Клиентский модуль. Имя пользователя: {self.client_name}')

        # Если имя пользователя не было задано, необходимо запросить пользователя.
        if not self.client_name:
            client_name = input('Введите имя пользователя: ')

        LOGGER.info(
            f'Запущен клиент с параметрами: адрес сервера: {self.server_address}, '
            f'порт: {self.server_port}, имя пользователя: {self.client_name}')

        try:
            transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            transport.connect((self.server_address, self.server_port))
            send_message(transport, Client.create_presence(self.client_name))
            answer = Client.process_response_ans(get_message(transport))
            LOGGER.info(f'Установлено соединение с сервером. Ответ сервера: {answer}')
            print(f'Установлено соединение с сервером.')
        except json.JSONDecodeError:
            LOGGER.error('Не удалось декодировать полученную Json строку.')
            sys.exit(1)
        except ServerError as error:
            LOGGER.error(f'При установке соединения сервер вернул ошибку: {error.text}')
            sys.exit(1)
        except ReqFieldMissingError as missing_error:
            LOGGER.error(f'В ответе сервера отсутствует необходимое поле {missing_error.missing_field}')
            sys.exit(1)
        except (ConnectionRefusedError, ConnectionError):
            LOGGER.critical(
                f'Не удалось подключиться к серверу {self.server_address}:{self.server_port}, '
                f'конечный компьютер отверг запрос на подключение.')
            sys.exit(1)
        else:
            # Если соединение с сервером установлено корректно,
            # запускаем клиентский процесс приёма сообщений
            receiver = threading.Thread(target=Client.message_from_server, args=(transport, self.client_name))
            receiver.daemon = True
            receiver.start()

            # затем запускаем отправку сообщений и взаимодействие с пользователем.
            user_interface = threading.Thread(target=Client.user_interactive, args=(transport, self.client_name))
            user_interface.daemon = True
            user_interface.start()
            LOGGER.debug('Запущены процессы')

            while True:
                time.sleep(1)
                if receiver.is_alive() and user_interface.is_alive():
                    continue
                break


if __name__ == '__main__':
    client = Client()
    client.main()
