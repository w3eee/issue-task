# coding: utf-8
""" 配置模块
"""

from tornado import options

configs = {
    'debug': True,
    'cookie_secret': 'hqerp-secret-3',
    'db_name': 'hqerp',
    'db': {
        'hqerp': {'host': 'localhost', 'database': 'hqerp', 'user': 'root', 'password': ''},
    },
    'redis': {
        'hqerp': {'host': 'localhost', 'port': 6379},
        'message': {'host': 'localhost', 'port': 6379},
    }
}


def load_py_file(path):
    if not path:
        return
    execfile(path, {}, configs)


options.define('port', default=8887, help='server listening port', type=int)
options.define('conf', default=None, help='configuration file', type=str)
options.parse_command_line()
load_py_file(options.options['conf'])
configs['port'] = options.options['port']
