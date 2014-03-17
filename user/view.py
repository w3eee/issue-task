# coding: utf8
# 用户系统: 注册, 登录, 注销, 用户消息, 用户关注

from hashlib import md5

from util.base import BaseHandler, login_required
from util import Paginator
from model import User, RegisterForm, LoginForm, UserForm
from message.model import Message
from task.model import TaskFocus, Task
from project.model import Auth


def url_spec(**kwargs):
    return [
        (r'/register/?', UserRegisterHandler, kwargs),
        (r'/login/?', UserLoginHandler, kwargs),
        (r'/logout/?', UserLogoutHandler, kwargs),
        (r'/message/?', UserMessageHandler, kwargs),
        (r'/focus/task/?', UserFocusHandler, kwargs),
        (r'/user_task/?', UserTaskHandler, kwargs),
        (r'/user/edit/?', UserEditHandler, kwargs),
    ]


#todo 更新用户, 更新缓存
class UserEditHandler(BaseHandler):
    """ 用户资料编辑
    """
    _mode = 'user_edit'

    @login_required
    def get(self, *args, **kwargs):
        return self.render('user.html', user=self.user.dictify(), errors={})

    @login_required
    def post(self, *args, **kwargs):
        re_login = False
        form = UserForm(self.request.arguments)
        if form.validate():
            # 验证用户密码
            data = form.data
            if not data['new_pwd']:
                data['new_pwd'] = data['old_pwd']
            if len(data['new_pwd']) < 6:
                form.new_pwd.errors.append(u'新密码长度至少六位')
            old_pwd = md5(data['old_pwd']).hexdigest()
            new_pwd = md5(data['new_pwd']).hexdigest()
            if old_pwd != self.user.pwd:
                form.old_pwd.errors.append(u'旧密码验证失败, 请重试')
            if data['email'] != self.user.email or data['name'] != self.user.name or new_pwd != self.user.pwd:
                re_login = True
            data['pwd'] = new_pwd
            del data['old_pwd']
            del data['new_pwd']
            self.user.update(**data)
            #if re_login:
            self.add_message(u'您修改了信息, 请重新登录')
            self.logout()
            return self.redirect('/login')
            #self.add_message(u'信息修改成功!')
            #return self.redirect(self.request.uri)  # 刷新当前页面
        return self.render('user.html', user=form.data, errors=form.errors)


class UserTaskHandler(BaseHandler):
    """ 指派给用户的任务 快捷入口
    """
    _mode = 'user_task'

    @login_required
    def get(self, *args, **kwargs):
        self.set_cookie('index-mode', self._mode)
        tasks = Task.assigned_tasks(user_id=self.user.id)
        # num = Task.number(assigned_id=self.user.id, status__le=Task._status_assigned)
        # paginator = Paginator(page, num, Task._per_page)
        auths = Auth.find_user_projects(self.user.id)
        return self.render('index.html', datas=tasks, auths=auths, paginator=None, page=0)


class UserMessageHandler(BaseHandler):
    """ 用户消息
    """

    _mode = 'message'

    @login_required
    def get(self, *args, **kwargs):
        self.set_cookie('index-mode', self._mode)
        page = self.get_args('p', 1, int)
        messages = Message.user_msgs(user_id=self.user.id, page=page)
        Message.mark_read(user_id=self.user.id)
        # for m in messages:
        #     if m.status == m._status_unread:
        #         self.add_message(u'你有新的消息')
        #         break
        num = Message.number(user_id=self.user.id)
        paginator = Paginator(page, num, Message._per_page)
        # auth
        auths = Auth.find_user_projects(self.user.id)
        return self.render('index.html', datas=messages, auths=auths, paginator=paginator, page=page)


class UserFocusHandler(BaseHandler):
    """ 用户关注(任务)
    """

    _mode = 'focus'

    @login_required
    def get(self, *args, **kwargs):
        self.set_cookie('index-mode', self._mode)
        page = self.get_args('p', 1, int)
        focuses = TaskFocus.user_focs(user_id=self.user.id, page=page)
        for f in focuses:
            f.task = Task.get(id=f.task_id)
        num = TaskFocus.number(user_id=self.user.id)
        paginator = Paginator(page, num, TaskFocus._per_page)
        #auths
        auths = Auth.find_user_projects(self.user.id)
        return self.render('index.html', datas=focuses, auths=auths, paginator=paginator, page=page)


class UserRegisterHandler(BaseHandler):

    def get(self, *args, **kwargs):
        return self.render('auth.html', mode='register', errors=[])

    def post(self, *args, **kwargs):
        form = RegisterForm(self.request.arguments)
        if form.validate():
            data = form.data
            pwd = md5(data['pwd']).hexdigest()
            user = User.register(email=data['email'], name=data['name'], pwd=pwd)
            if user:
                self.login(user)
                # add default auth
                Auth.add_default(user=user)
                return self.redirect('/')
            else:
                form.errors.update({'server': [u'创建用户失败, 请重试!', ]})
        return self.render('auth.html', mode='register', errors=form.errors)


class UserLoginHandler(BaseHandler):

    def get(self, *args, **kwargs):
        return self.render('auth.html', mode='login', errors=[])

    def post(self, *args, **kwargs):
        form = LoginForm(self.request.arguments)
        if form.validate():
            data = form.data
            pwd = md5(data['pwd']).hexdigest()
            user = User.check(account=data['account'], pwd=pwd)
            if user:
                self.login(user)
                n = self.get_args('next', '/')
                return self.redirect(n)
            else:
                form.errors.update({'server': [u'账户和密码不匹配, 请检查']})
        return self.render('auth.html', mode='login', errors=form.errors)


class UserLogoutHandler(BaseHandler):

    @login_required
    def get(self, *args, **kwargs):
        self.logout()
        return self.redirect('/login')