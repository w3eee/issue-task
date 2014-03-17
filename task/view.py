# coding: utf8

from tornado.web import HTTPError
from functools import wraps
import json
import re
from datetime import datetime

from util.base import BaseHandler, login_required
from util import Paginator
from model import Task, TaskForm, TaskLog, TaskFocus
from project.model import Auth
from message.model import Message
from comment.model import Comment, CommentForm
from user.model import User

# just for backup
_url_regex = regex = re.compile(
    r'^(?:http|ftp)s?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)


def analyse_content(content):
    """ 内容分析, 获取@和链接
    """
    url_re = r'<a>.*?</a>'
    at_re = r'@.*?\s'
    users = []

    def sub_func(g):
        url = g.group()[3: -4]
        if not url.startswith('http://'):
            url = 'http://' + url
        return '<a href="%s" target="_blank">%s</a>' % (url, url)

    def at_sub(g):
        at = g.group()
        users.append(at[1:].strip())
        return '<b>%s</b>' % at

    content = content.strip()
    try:
        content = content.decode('utf8')
    except UnicodeEncodeError:
        content = content
    if not content:
        return content, []
    content = re.sub(url_re, sub_func, content)  # 替换url
    content = re.sub(at_re, at_sub, content)  # 替换@
    # content = content.replace('\n', '<br />')
    # content = content.replace('\r', '<br />')
    content = content.replace('\r\n', '<br />')
    return content, users


def url_spec(**kwargs):
    return [
        (r'/(?P<pid>\d+)/task/?', TaskHandler, kwargs),  # /1/task?s=unsolved&&p=1&&o=priority 任务列表, 各种排序类型等
        (r'/task/home/?', TaskHomeHandler, kwargs),  # 任务列表首页
        (r'/(?P<pid>\d+)/task/new/?', TaskNewHandler, kwargs),  # 创建任务
        (r'/(?P<pid>\d+)/task/(?P<tid>\d+)/?(?P<mode>(?:solve)|(?:edit)|(?:focus))?/?', TaskPageHandler, kwargs),  # 详情
        (r'/(?P<pid>\d+)/task/(?P<tid>\d+)/comment/?', TaskCommentHandler, kwargs),  # 评论 设置@消息
    ]


# 验证pid uid权限修饰器
def pro_auth(func):
    @wraps(func)
    def wrapper(handler, *args, **kwargs):
        pid = kwargs.get('pid')
        if not pid:
            raise HTTPError(404, 'not fount this page')
        auth = Auth.check_auth(uid=handler.user.id, pid=pid, is_admin=handler.user.admin)
        if not auth:
            handler.add_message(u'您没有访问该项目的权限, 请联系管理员')
            return handler.render('failed.html')
        handler.auth = auth
        handler.pid = pid
        return func(handler, *args, **kwargs)
    return wrapper


class TaskHomeHandler(BaseHandler):

    _mode = 'task'

    @login_required
    def get(self, *args, **kwargs):
        """ 任务home页
        """
        pros = Auth.find_user_projects(uid=self.user.id)
        if not pros:
            self.add_message(u'您目前还没有可用的项目哦!')
            return self.redirect('/')  # 首页展示用户消息
        cur_pro = pros[0]
        cur_auth_id = self.get_cookie('cur_auth', pros[0].id)
        for p in pros:
            if p.id == int(cur_auth_id):
                cur_pro = p
        status = self.get_cookie('status', 'unsolved')
        order = self.get_cookie('order', 'p')
        return self.redirect('/%s/task?s=%s&&o=%s' % (cur_pro.project_id, status, order))


class TaskHandler(BaseHandler):
    """ 任务列表展示
    """

    _status = [
        'unsolved', 'solved', 'wait', 'assigned', 'closed', 'create', 'all'
    ]
    _mode = 'task'
    _order = {
        'p': 'priority desc',
        'p_': 'priority asc',
        's': 'status desc',
        's_': 'status asc',
        't': 'type desc',
        't_': 'type asc',
        'c': 'created desc',
        'c_': 'created asc',
    }

    @login_required
    @pro_auth  # check and set auth and set pid
    def get(self, *args, **kwargs):
        """ order: p, s, t default desc p_, s_, t_ - asc
        """
        # get args
        status = self.get_args('s') or self.get_cookie('status', 'unsolved')
        order = self.get_args('o') or self.get_cookie('order', 'p')  # _o - desc, o_ - asc
        page = self.get_args('p', 1)
        # 记录状态
        self.set_cookie('status', status)
        self.set_cookie('order', order)
        self.set_cookie('cur_auth', str(self.auth.id))
        # set order_by
        if order not in self._order.keys():
            order = 'p'
        order_by = self._order.get(order)
        page = int(page)
        pros = Auth.find_user_projects(uid=self.user.id)
        where = dict(
            uid=self.user.id,
            pid=self.pid,
            status=status
        )
        if status != 'assigned':
            tasks, num = Task.find_project_tasks(
                page=page,
                order_by=order_by,
                get_num=True,
                **where)
            paginator = Paginator(page, num, Task._per_page)
        else:
            tasks = Task.assigned_tasks(
                user_id=self.user.id,
                order_by=order_by,
                pid=self.pid,
            )
            paginator = None
        unread_num = Message.unread_num(user_id=self.user.id)
        return self.render(
            'task-home.html',
            cur_pro=self.auth,
            pros=pros,
            tasks=tasks,
            status=status,
            order=order,
            page=page,
            paginator=paginator,
            unread_num=unread_num)


class TaskNewHandler(BaseHandler):
    """ 创建任务
    """

    _mode = 'task'

    def initialize(self):
        self.statuses = Task._status.items()
        self.types = Task._type.items()
        self.priorities = Task._priority.items()

    @login_required
    @pro_auth
    def get(self, *args, **kwargs):
        # todo 改善, 不要写多
        # todo 添加缓存
        p_users = Auth.find_project_users(pid=self.pid)
        p_users = [{'id': auth.user_id, 'name': auth.user_name} for auth in p_users]
        json_p_users = json.dumps(p_users)
        form = TaskForm()
        form.assigneds.data = json.dumps([])
        return self.render('task-new.html',
                           task=form.data,
                           auth=self.auth,
                           json_users=json_p_users,
                           statuses=self.statuses,
                           types=self.types,
                           priorities=self.priorities,
                           errors={},
                           update=False)

    @login_required
    @pro_auth
    def post(self, *args, **kwargs):
        # todo
        p_users = Auth.find_project_users(pid=self.pid)
        p_users = [{'id': auth.user_id, 'name': auth.user_name} for auth in p_users]
        json_p_users = json.dumps(p_users)
        self.p_users = p_users  # form填充需要使用
        form = TaskForm(self, self.request.arguments)
        is_continue = int(self.get_args('continue', 0))
        if form.validate():
            form.created.data = datetime.now()
            data = dict(form.data)
            if not data['expires']:
                data.pop('expires')
            # return
            task = Task.new(**data)
            # 指派用户, 记录消息
            for ud in task.assigned_users:
                Message.set(user_id=ud['id'],
                            from_user=self.user,
                            task=task,
                            pid=self.pid,
                            pname=self.auth.project_name,
                            type='assigned')
            if task and is_continue:
                self.add_message(u'发布任务成功')
                return self.redirect(self.request.uri)
            return self.redirect('/%s/task' % self.pid)
        else:

            return self.render(
                'task-new.html',
                task=form.data,  # 字典
                auth=self.auth,
                json_users=json_p_users,
                statuses=self.statuses,
                types=self.types,
                priorities=self.priorities,
                errors=form.errors,
                update=False)


class TaskPageHandler(BaseHandler):
    """ 任务详情页, 包含任务关注, 任务编辑功能
    """

    _mode = 'task'

    def initialize(self):
        self.statuses = Task._status.items()
        self.types = Task._type.items()
        self.priorities = Task._priority.items()

    @login_required
    @pro_auth
    def get(self, *args, **kwargs):
        tid = kwargs.get('tid')
        mode = kwargs.get('mode')
        if not tid:
            raise HTTPError(404)
        p_users = Auth.find_project_users(pid=self.pid)
        self.p_users = [{'id': auth.user_id, 'name': auth.user_name} for auth in p_users]
        self.json_p_users = json.dumps(self.p_users)
        task = Task.get(id=tid)
        if not mode:  # 任务详细信息
            # get comment
            task_comments = Comment.find(task_id=task.id, order_by='created')
            # get change log
            task_logs = TaskLog.find(task_id=task.id, order_by='created desc')
            # focus
            focus = TaskFocus.check_focus(task_id=task.id, user_id=self.user.id)
            return self.render('task.html',
                               task=task,
                               auth=self.auth,
                               logs=task_logs,
                               comments=task_comments,
                               focus=focus)
        if mode == 'solve':  # 标记解决任务
            if not task.is_done:
                task.status = Task._status_solved
                task.save()
                TaskLog.new(
                    task_id=task.id,
                    desc=json.dumps([]),
                    note=u'标记为解决',
                    updater_id=self.user.id,
                    updater_name=self.user.name,
                )
            return self.redirect('/%s/%s/%s' % (self.pid, 'task', task.id))
        if mode == 'edit':  # 编辑任务
            # 用户列表去除已经分配的用户
            users = [u for u in self.p_users if u['id'] not in task.assigned_ids]
            json_p_users = json.dumps(users)
            task_data = task.dictify()
            task_data['assigneds'] = json.dumps(task.assigned_users)
            return self.render(
                'task-new.html',
                task=task_data,
                auth=self.auth,
                json_users=json_p_users,
                statuses=self.statuses,
                types=self.types,
                priorities=self.priorities,
                errors={},
                update=True)
        if mode == 'focus':  # 关注任务
            TaskFocus.focus(
                task=task,
                user=self.user,
                pid=self.pid,
                pname=self.auth.project_name,
            )
            return self.redirect('/%s/%s/%s' % (self.pid, 'task', task.id))

    @login_required
    @pro_auth
    def post(self, *args, **kwargs):
        """ 编辑任务 并记录更新历史
        """
        tid = kwargs.get('tid')
        mode = kwargs.get('mode')
        if not tid or mode != 'edit':
            raise HTTPError(404)
        p_users = Auth.find_project_users(pid=self.pid)
        self.p_users = [{'id': auth.user_id, 'name': auth.user_name} for auth in p_users]
        self.json_p_users = json.dumps(self.p_users)
        task = Task.get(id=tid)
        post_data = self.request.arguments
        # log note
        log_note = post_data['note'][0].decode('utf8')
        form = TaskForm(self, post_data)
        # redefine task message
        form.creator_id.data = task.creator_id
        form.creator_name.data = task.creator_name
        form.project_id.data = self.pid
        form.created.data = task.created
        # 旧的指派者
        assigned_users = task.assigned_users
        if form.validate():
            task = task.update_and_log(
                data=form.data,
                actor_id=self.user.id,
                actor_name=self.user.name,
                note=log_note)
            if task:
                # 指派用户, 记录消息
                for ud in task.assigned_users:
                    Message.set(user_id=ud['id'],
                                from_user=self.user,
                                task=task,
                                pid=self.pid,
                                pname=self.auth.project_name,
                                type='assigned')
                # 删除更新 未指派用户的消息 为获取用户消息提供服务 物理删除记录
                del_msg_user_ids = [u['id'] for u in assigned_users if u['id'] not in task.assigned_ids]
                for duid in del_msg_user_ids:
                    Message.delete(
                        user_id=duid,
                        type=Message._type_assigned,
                        task_id=task.id,
                        project_id=self.pid
                    )
                # 任务更新消息
                if task.creator_id != self.user.id:
                    Message.set(
                        user_id=task.creator_id,
                        from_user=self.user,
                        task=task,
                        pid=self.pid,
                        pname=self.auth.project_name,
                        type='edit'
                    )
                return self.redirect('/%s/task/%s' % (self.pid, task.id))
            self.add_message(u'更新任务失败, 请重试')
            return self.render('failed.html')
        else:
            # 去除已经填写的用户
            assigneds = json.loads(form.assigneds.data)
            aids = set([ud['id'] for ud in assigneds])
            json_users = json.dumps([ud for ud in self.p_users if ud['id'] not in aids])
            return self.render(
                'task-new.html',
                task=form.data,
                auth=self.auth,
                json_users=json_users,
                statuses=self.statuses,
                types=self.types,
                priorities=self.priorities,
                errors=form.errors,
                update=True)


class TaskCommentHandler(BaseHandler):

    @login_required
    @pro_auth
    def get(self, *args, **kwargs):
        tid = kwargs.get('tid')
        task = Task.get(id=tid)
        return self.render('comment.html', errors={}, auth=self.auth, task=task)

    @login_required
    @pro_auth
    def post(self, *args, **kwargs):
        tid = kwargs.get('tid')
        if not tid:
            raise HTTPError(404)
        task = Task.get(id=tid)
        form = CommentForm(self.request.arguments)
        # set form data
        form.from_user_id.data = self.user.id
        form.from_user_name.data = self.user.name
        form.to_user_id.data = task.creator_id
        form.to_user_name.data = task.creator_name
        form.task_id.data = task.id
        form.task_title.data = task.title
        # 分析content 识别链接, 识别@
        # 链接 <a>url</a>
        content, at_users = analyse_content(form.content.data)
        print '****************content: ', repr(content)
        form.type.data = Comment._type_at if at_users else Comment._type_reply
        form.content.data = content
        if form.validate():
            comment = Comment.new(**form.data)
            # 评论消息 自己回复自己或者自己@自己不发消息
            if int(self.user.id) != int(task.creator_id):
                Message.set(
                    user_id=task.creator_id,
                    from_user=self.user,
                    task=task,
                    pid=self.pid,
                    pname=self.auth.project_name,
                    type='apply',
                    content=content,
                )
            # @消息
            for name in at_users:
                user = User.get(name=name, status=User._status_ok)
                if user and user.id != int(self.user.id):
                    Message.set(
                        user_id=user.id,
                        from_user=self.user,
                        task=task,
                        pid=self.pid,
                        pname=self.auth.project_name,
                        type='@',
                        content=content,
                    )
            return self.redirect('/%s/task/%s' % (self.pid, task.id))
        else:
            return self.render('comment.html', errors=form.errors, auth=self.auth, task=task)