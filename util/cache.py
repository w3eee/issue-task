# coding: utf-8
"""Cache工具。

用法1：
    import hqby.cache
    conn = hqby.cache.get_sync_conn('mobile')
    conn.set('13812345678', 'username')
    uname = conn.get('13812345678')

用法2：
    import hqby.cache
    @hqyb.cache.SyncCache('/taojie/mobile/data/', 300)
    def get_mobile_user(mobile):
        ...
        return uname
    def update_mobile_user(mobile):
        ...
        get_mobile_user._del_cache(mobile)
        # get_mobile_user._clr_cache()
"""

import hashlib
import cPickle
import inspect

import redis
import tornadoredis

from config import configs


_SYNC_CONNS_ = {}
_ASYNC_CONNS_ = {}
_IO_LOOP_ = None


def get_sync_conn(id):
    if id in _SYNC_CONNS_:
        return _SYNC_CONNS_[id]
    _SYNC_CONNS_[id] = conn = redis.Redis(**configs['redis'][id])
    return conn


def get_async_conn(id):
    if id in _ASYNC_CONNS_:
        return _ASYNC_CONNS_[id]
    _ASYNC_CONNS_[id] = conn = tornadoredis.Client(
        io_loop=_IO_LOOP_, **configs['redis'][id])
    conn.connect()
    return conn


def set_ioloop(ioloop):
    global _IO_LOOP_
    while _ASYNC_CONNS_:
        _ASYNC_CONNS_.popitem()[1].disconnect()
    _IO_LOOP_ = ioloop


def gen_key(prefix, args, kwargs):
    key = prefix + ','.join([str(i) for i in args]) \
                 + ','.join([(str(i), str(j)) for i, j in kwargs.items()])
    if len(key) > 200:
        key = prefix + hashlib.md5(key).hexdigest()
    return key


class SyncCache(object):

    def __init__(self, conn_id, prefix_key, ttl=None):
        self.conn_id = conn_id
        self.prefix_key = prefix_key
        self.ttl = ttl

    def __call__(self, func):
        self.func = func
        self.skip_self_arg = (inspect.getargspec(func).args[:1] == ['self'])
        def deco_func(*args, **kwargs):
            return self.call_func(*args, **kwargs)
        setattr(deco_func, '_del_cache', self._del_cache)
        setattr(deco_func, '_clr_cache', self._clr_cache)
        return deco_func

    def call_func(self, *args, **kwargs):
        key = gen_key(self.prefix_key, args[1:], kwargs) if self.skip_self_arg \
                else gen_key(self.prefix_key, args, kwargs)
        conn = get_sync_conn(self.conn_id)
        ret = conn.get(key)
        if ret:
            return cPickle.loads(ret)
        ret = self.func(*args, **kwargs)
        if self.ttl == None:
            conn.set(key, cPickle.dumps(ret))
        else:
            conn.setex(key, cPickle.dumps(ret), self.ttl)
        return ret

    def _del_cache(self, *args, **kwargs):
        key = gen_key(self.prefix_key, args, kwargs)
        get_sync_conn(self.conn_id).delete(key)

    def _clr_cache(self, *args, **kwargs):
        key = gen_key(self.prefix_key, args, kwargs)
        conn = get_sync_conn(self.conn_id)
        keys = conn.keys(key + '*')
        if keys:
            conn.delete(*keys)


def id_cache(conn_id, key):
    def deco_func(func):
        id = func()
        conn = get_sync_conn(conn_id)
        id2 = int(conn.get(key) or 0)
        if id > id2:
            conn.set(key, id)
        def call_func():
            return conn.incr(key) - 1
        return call_func
    return deco_func

