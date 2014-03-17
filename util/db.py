# coding: utf-8

from torndb import Connection
from config import configs


_CONNS_ = {}


def get_conn(db_id):
    if db_id in _CONNS_:
        return _CONNS_[db_id]
    _CONNS_[db_id] = db = Connection(**configs['db'][db_id])
    db._db_args.pop('init_command', None)
    db.execute("SET TIME_ZONE = 'SYSTEM'")
    return db
