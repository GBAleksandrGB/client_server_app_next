"""Декораторы"""

import sys
import logging


class Log:
    def __init__(self, func_to_log):
        self.func_to_log = func_to_log

    def __call__(self, *args, **kwargs):
        logger_name = 'server' if 'main_server.py' in sys.argv[0] else 'client'
        LOGGER = logging.getLogger(logger_name)
        ret = self.func_to_log(*args, **kwargs)
        LOGGER.debug(f'Была вызвана функция {self.func_to_log.__name__} c параметрами {args}, {kwargs}. '
                     f'Вызов из модуля {self.func_to_log.__module__}')
        return ret
