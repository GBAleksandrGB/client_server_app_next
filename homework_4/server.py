"""Программа-сервер"""

import argparse
import configparser
import dis
import logging
import os.path
import select
import socket
import sys
import threading

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox

from common.decos import Log
from common.utils import get_message, send_message
from homework_2.common.variables import ACTION, TIME, USER, ACCOUNT_NAME, SENDER, \
    PRESENCE, ERROR, MESSAGE, MESSAGE_TEXT, RESPONSE_400, DESTINATION, RESPONSE_200, EXIT
from homework_2.server_db import ServerStorage
from homework_4.server_gui import MainWindow, gui_create_model, HistoryWindow, create_stat_model, ConfigWindow

LOGGER = logging.getLogger('server')

new_connection = False

conflag_lock = threading.Lock()


class CheckPort:
    def __set__(self, instance, value):
        if not 1023 < value < 65536:
            LOGGER.critical(
                f'Попытка запуска сервера с указанием неподходящего порта {value}. '
                f'Допустимы адреса с 1024 до 65535.')
            sys.exit(1)
        instance.__dict__[self.my_attr] = value

    def __set_name__(self, owner, my_attr):
        self.my_attr = my_attr


class ServerVerifier(type):
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
                             if el.argval in ['connect', 'SOCK_STREAM']]

        if 'connect' in selection:
            raise AttributeError(f"Недопустимый метод 'connect' в сокете")

        if 'SOCK_STREAM' in selection:
            raise AttributeError(f"Тип сокета не TCP")

        super(ServerVerifier, cls).__init__(future_class_name,
                                            future_class_parents,
                                            future_class_attrs)


@Log
def arg_parser(default_port, default_address):
    """Парсер аргументов коммандной строки"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=default_port, type=int, nargs='?')
    parser.add_argument('-a', default=default_address, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p
    return listen_address, listen_port


class Server(threading.Thread):
    listen_port = CheckPort()

    def __init__(self, listen_address, listen_port, database):
        self.sock = None
        self.listen_address = listen_address
        self.listen_port = listen_port
        self.database = database
        self.clients = []
        self.messages = []
        self.names = dict()
        super().__init__()

    def init_sock(self):
        LOGGER.info(
            f'Запущен сервер, порт для подключений: {self.listen_port}, '
            f'адрес с которого принимаются подключения: {self.listen_address}. '
            f'Если адрес не указан, принимаются соединения с любых адресов.')

        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        transport.bind((self.listen_address, self.listen_port))
        transport.settimeout(0.5)
        self.sock = transport
        self.sock.listen()

    def run(self):
        self.init_sock()

        while True:
            # Ждём подключения, если таймаут вышел, ловим исключение.
            try:
                client, client_address = self.sock.accept()
            except OSError:
                pass
            else:
                LOGGER.info(f'Установлено соедение с ПК {client_address}')
                self.clients.append(client)

            recv_data_lst = []
            send_data_lst = []
            err_lst = []

            try:
                if self.clients:
                    recv_data_lst, send_data_lst, err_lst = select.select(self.clients, self.clients, [], 0)
            except OSError:
                pass

            # принимаем сообщения и, если ошибка, исключаем клиента.
            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    try:
                        Server.process_client_message(get_message(client_with_message), client_with_message)
                    except Exception:
                        LOGGER.info(f'Клиент {client_with_message.getpeername()} отключился от сервера.')
                        self.clients.remove(client_with_message)

                # Если есть сообщения, обрабатываем каждое.
            for message in self.messages:
                try:
                    self.process_message(message, send_data_lst)
                except Exception:
                    LOGGER.info(f'Связь с клиентом с именем {message[DESTINATION]} была потеряна')
                    self.clients.remove(self.names[message[DESTINATION]])
                    del self.names[message[DESTINATION]]
            self.messages.clear()

    def process_message(self, message, listen_socks):
        if message[DESTINATION] in self.names and self.names[message[DESTINATION]] in listen_socks:
            send_message(self.names[message[DESTINATION]], message)
            LOGGER.info(f'Отправлено сообщение пользователю {message[DESTINATION]} от пользователя {message[SENDER]}.')
        elif message[DESTINATION] in self.names and self.names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            LOGGER.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, отправка сообщения невозможна.')

    @Log
    def process_client_message(self, message, client):
        global new_connection
        LOGGER.debug(f'Разбор сообщения от клиента : {message}')

        # Если это сообщение о присутствии, принимаем и отвечаем
        if ACTION in message and message[ACTION] == PRESENCE and \
                TIME in message and USER in message:

            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                self.database.user_login(message[USER][ACCOUNT_NAME], client_ip, client_port)
                send_message(client, RESPONSE_200)
                with conflag_lock:
                    new_connection = True
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
            return
        # Если это сообщение, то добавляем его в очередь сообщений.
        elif ACTION in message and message[ACTION] == MESSAGE and \
                DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message:
            self.messages.append(message)
            return
        # Если клиент выходит
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
            self.database.user_logout(message[ACCOUNT_NAME])
            self.clients.remove(self.names[message[ACCOUNT_NAME]])
            self.names[message[ACCOUNT_NAME]].close()
            del self.names[message[ACCOUNT_NAME]]
            with conflag_lock:
                new_connection = True
            return
        # Иначе отдаём Bad request
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)
            return


def main():
    config = configparser.ConfigParser()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/{'server.ini'}")
    listen_address, listen_port = arg_parser(
        config['SETTINGS']['DefaultPort'], config['SETTINGS']['ListenAddress'])
    database = ServerStorage(os.path.join(config['SETTINGS']['DefaultPort'], config['SETTINGS']['ListenAddress']))
    server = Server(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    server_app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.statusBar().showMessage('Server working')
    main_window.active_clients_table.setModel(gui_create_model(database))
    main_window.active_clients_table.resizeColumnsToContents()
    main_window.active_clients_table.resizeRowToContents()

    def list_update():
        global new_connection
        if new_connection:
            main_window.active_clients_table.setModel(gui_create_model(database))
            main_window.active_clients_table.resizeColumnsToContents()
            main_window.active_clients_table.resizeRowToContents()
            with conflag_lock:
                new_connection = False

    def show_statistics():
        global stat_window
        stat_window = HistoryWindow()
        stat_window.history_table.setModel(create_stat_model(database))
        stat_window.history_table.resizeRowToContents()
        stat_window.history_table.resizeRowToContents()
        stat_window.show()

    def server_config():
        global config_window
        config_window = ConfigWindow()
        config_window.db_path.insert(config['SETTINGS']['DatabasePath'])
        config_window.db_file.insert(config['SETTINGS']['DatabaseFile'])
        config_window.port.insert(config['SETTINGS']['DefaultPort'])
        config_window.ip.insert(config['SETTINGS']['ListenAddress'])
        config_window.save_btn.clicked.connect(save_server_config)

    def save_server_config():
        global config_window
        message = QMessageBox()
        config['SETTINGS']['DatabasePath'] = config_window.db_path.text()
        config['SETTINGS']['DatabaseFile'] = config_window.db_file.text()
        try:
            port = int(config_window.port.text())
        except ValueError:
            message.warning(config_window, 'Ошибка', 'Порт должен быть числом')
        else:
            config['SETTINGS']['ListenAddress'] = config_window.ip.text()
            if 1023 < port < 65536:
                config['SETTINGS']['DefaultPort'] = str(port)
                with open('server.ini', 'w') as conf:
                    config.write(conf)
                    message.information(config_window, 'OK', 'Настройки успешно сохранены')
            else:
                message.warning(config_window, 'Ошибка', 'Порт должен быть от 1024 до 65536')

    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    main_window.refresh_button.triggered.connect(list_update)
    main_window.show_history_button.triggered.connect(show_statistics)
    main_window.config_button.triggered.connect(server_config)

    server_app.exec_()


if __name__ == '__main__':
    main()
