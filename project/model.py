# coding: utf8

from util.Hqorm import HqOrm
from user.model import User


class Project(HqOrm):

    _table_name = 'project'

    _status_secret = 2
    _status_del = 0
    _status_open = 1

    _rows = [
        'id', 'name', 'created', 'note', 'status'
    ]

    @property
    def users(self):
        us = []
        auths = Auth.find_project_users(pid=self.id)
        for auth in auths:
            u = User.get(id=auth.user_id, status=User._status_ok)
            if u:
                us.append(u)
        return us

    @classmethod
    def new(cls, **kwargs):
        p = super(Project, cls).new(**kwargs)
        if p.status == cls._status_open:
            for u in User.find(status=User._status_ok):
                Auth.new(
                    project_id=p.id,
                    project_name=p.name,
                    user_id=u.id,
                    user_name=u.name
                )
        return p


class Auth(HqOrm):

    _table_name = 'auth'
    _status_allow = 1
    _status_deny = 0

    _rows = [
        'id', 'project_id', 'project_name', 'user_id', 'user_name', 'status'
    ]

    @classmethod
    def new(cls, project_id, project_name, user_id, user_name):
        auth = cls.get(user_id=user_id, project_id=project_id)
        if auth:
            if auth.status == cls._status_deny:
                auth.status = cls._status_allow
                auth = auth.save()
            return auth
        return super(Auth, cls).new(
            project_id=project_id,
            project_name=project_name,
            user_id=user_id,
            user_name=user_name,
            status=cls._status_allow,
        )


    @classmethod
    def find_user_projects(cls, uid):
        """ 获取用户可访问的项目
        """
        return cls.find(user_id=uid, status=cls._status_allow)

    @classmethod
    def find_project_users(cls, pid):
        """ 获取项目的用户
        """
        return cls.find(project_id=pid, status=cls._status_allow)

    @classmethod
    def add_default(cls, user):
        """ 添加公开的项目权限
        """
        for p in Project.find(status=Project._status_open):
            cls.new(
                project_id=p.id,
                project_name=p.name,
                user_id=user.id,
                user_name=user.name,
            )

    @classmethod
    def check_auth(cls, pid, uid, is_admin=False):
        auth = cls.get(user_id=uid, project_id=pid, status=cls._status_allow)
        if not auth and is_admin:
            project = Project.get(id=pid, status__no=Project._status_del)
            user = User.get(id=uid, status=User._status_ok)
            if not user or not user.admin or not project:
                return None
            auth = cls.new(
                project_id=project.id,
                project_name=project.name,
                user_id=user.id,
                user_name=user.name,
                status=cls._status_allow
            )
        return auth

