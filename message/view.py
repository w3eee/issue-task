#coding: utf8

from util.base import BaseHandler, login_required
from model import Message


def url_spec(**kwargs):
    return [
        (r'/message/(?P<mid>\d+)/del', MessageDelHandler, kwargs),
    ]


class MessageDelHandler(BaseHandler):

    @login_required
    def post(self, *args, **kwargs):
        """ 删除消息
        """
        mid = kwargs.get('mid')
        message = Message.get(id=mid, status__no=Message._status_del)
        if message.user_id != self.user.id or not message:
            self.write({
                'status': 0
            })
            return
        message.status = Message._status_del
        message.save()
        self.write({
            'status': 1,
            'msg_id': message.id,
        })