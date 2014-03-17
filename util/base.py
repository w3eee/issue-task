# coding: utf8

from tornado.web import RequestHandler, MissingArgumentError
import cPickle
from functools import wraps
from copy import deepcopy

import cache


def login_required(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.user:
            return self.redirect(self.get_login_url())
        return func(self, *args, **kwargs)
    return wrapper


##基础封装RequestHandler
class BaseHandler(RequestHandler):

    _mode = ''
    _messages = []

    def get_current_user(self):
        uid = self.get_secure_cookie('uid')
        if not uid:
            return None
        user = cache.get_sync_conn('hqerp').get('uid-' + str(uid))
        return cPickle.loads(user) if user else None

    def get_login_url(self):
        return '/login?' + 'next=' + self.request.uri

    def post_data(self):
        """ 获取表单全部数据 - 字典, unicode方式返回
        """
        data = {}
        for k in self.request.arguments:
            v = self.get_arguments(k)
            data[k] = v[0] if len(v) == 1 else v
        return data

    def login(self, user, expires_days=31):
        """ 用户登录, 写入cookie-uid, 用户对象保存到缓存
        """
        if not user:
            return
        self.clear_cookie('uid')
        self.set_secure_cookie('uid', str(user.id), expires_days=expires_days)
        cache.get_sync_conn('hqerp').set('uid-' + str(user.id), cPickle.dumps(user))

    def logout(self, user=None):
        if not user:
            user = self.current_user
        self.clear_cookie('uid')
        cache.get_sync_conn('hqerp').delete('uid-' + str(user.id))

    def get_args(self, key, default='', data_type=None):
        if not data_type:
            data_type = unicode
        try:
            value = self.get_argument(key)
            if callable(data_type):
                return data_type(value)
            return value
        except MissingArgumentError:
            return default

    def get_template_namespace(self):
        msg = deepcopy(self._messages)
        add_names = dict(
            mode=self._mode,
            messages=msg,
        )
        self.clear_message()
        name = super(BaseHandler, self).get_template_namespace()
        name.update(add_names)
        return name

    def clear_message(self):
        while self._messages:
            self._messages.pop()

    def add_message(self, msg):
        self.clear_message()
        self._messages.append(msg)

    @property
    def user(self):
        return self.current_user