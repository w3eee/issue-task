# coding: utf8

from tornado.web import HTTPError

from util.base import BaseHandler, login_required
from project.model import Project, Auth
from user.model import User


def url_spec(**kwargs):
    return [
        (r'/', IndexHandler, kwargs),
        (r'/manager/?(?P<m>(?:project)|(?:auth))?/?', SysManagerHandler, kwargs),
    ]


class IndexHandler(BaseHandler):

    _mode_url = {
        'message': '/message',
        'focus': '/focus/task',
        'user_task': '/user_task',
    }

    @login_required
    def get(self, *args, **kwargs):  # 用户消息, 用户关注
        m = self.get_cookie('index-mode', 'message')
        return self.redirect(self._mode_url.get(m, '/message'))


class SysManagerHandler(BaseHandler):

    _mode = 'sys'

    @login_required
    def get(self, *args, **kwargs):
        if not self.user.admin:
            self.add_message(u'您没有访问该页面的权限, 请联系管理员')
            return self.render('failed.html')
        ps = Project.find(status__no=Project._status_del)
        users = User.find(status=User._status_ok)
        return self.render('manager.html', ps=ps, users=users)

    @login_required
    def post(self, *args, **kwargs):
        if not self.user.admin:
            raise HTTPError(404)
        m = kwargs.get('m')
        if m == 'project':
            data = self.post_data()
            Project.new(
                name=data['name'],
                note=data['note'],
                status=int(data['status']),
            )
        elif m == 'auth':
            data = self.post_data()
            pid, pname = data['project'].split('-')
            uid, uname = data['user'].split('-')
            Auth.new(
                project_id=int(pid),
                project_name=pname,
                user_id=int(uid),
                user_name=uname,
            )
        return self.redirect('/manager')
