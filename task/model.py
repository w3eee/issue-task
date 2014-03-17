# coding: utf8
# model, form

import json
from datetime import datetime

from util.Hqorm import HqOrm, join_
from util import date_to_str

#form
from wtforms_tornado import Form
from wtforms.fields import IntegerField, StringField, TextField, SelectField, DateTimeField
from wtforms.validators import required

from message.model import Message


class TaskFocus(HqOrm):

    _table_name = 'task_focus'
    _per_page = 10
    _status_ok = 1
    _status_del = 0

    _rows = [
        'id', 'task_id', 'task_title', 'user_id', 'user_name', 'status', 'created', 'project_id', 'project_name'
    ]

    @classmethod
    def check_focus(cls, user_id, task_id):
        return cls.get(user_id=user_id, task_id=task_id, status=cls._status_ok)

    @classmethod
    def user_focs(cls, user_id, page=1):
        return cls.page(user_id=user_id, status=cls._status_ok, page=page)

    @classmethod
    def number(cls, args=None, **kwargs):
        return super(TaskFocus, cls).number(args=args, status=cls._status_ok, **kwargs)

    @classmethod
    def focus(cls, user, task, pid, pname):
        f = cls.get(user_id=user.id, task_id=task.id)
        if not f:
            f = cls.new(
                task_id=task.id,
                task_title=task.title,
                user_id=user.id,
                user_name=user.name,
                project_id=pid,
                project_name=pname,
                status=cls._status_ok
            )
        else:
            f.status = not f.status
            f.save()
        return f


class TaskLog(HqOrm):

    _table_name = 'task_log'
    _per_page = 15

    _rows = [
        'id', 'task_id', 'created', 'desc', 'note', 'updater_id', 'updater_name'
    ]

    @property
    def desc_(self):
        if not self.desc:
            return self.desc
        return json.loads(self.desc)


class Task(HqOrm):

    _table_name = 'task'
    _per_page = 10

    _rows = [
        'id', 'project_id', 'title', 'type', 'status', 'priority', 'desc', 'created', 'updated',
        'expires', 'creator_id', 'creator_name', 'assigned_id', 'assigned_name', 'assigneds'
    ]

    _checks = {
        'title': u'标题',
        'assigneds': u'指派用户',
        'priority': u'优先级',
        'type': u'类型',
        'status': u'状态',
        'expires': u'期望时间',
        'desc': u'描述',
    }

    _type = {1: u'bug', 2: u'功能', 3: u'支持', 4: u'事务'}
    _type_icon = {1: 'fa-bug', 2: 'fa-gift', 3: 'fa-gavel', 4: 'fa-shield'}
    _type_bug = 1
    _type_func = 2
    _type_support = 3
    _type_work = 4

    _priority_low = 1
    _priority_normal = 2
    _priority_high = 3
    _priority_crash = 4
    _priority = {1: u'低', 2: u'普通', 3: u'高', 4: u'紧急'}

    _status_new = 1
    _status_assigned = 2
    _status_wait = 3
    _status_solved = 4
    _status_closed = 5
    _status = {1: u'新建', 2: u'已指派', 3: u'等待反馈', 4: u'已解决', 5: u'已关闭'}

    _web_status = ['unsolved', 'solved', 'all', 'assigned', 'closed', 'wait', 'create']

    @classmethod
    def find_project_tasks(cls, uid, pid, status, page=0, order_by='created desc', get_num=False):
        assert status in cls._web_status
        page = int(page)
        params = dict(
            project_id=pid,
        )
        if status == 'unsolved':  # todo 临时的解决方案
            params['status__le'] = cls._status_wait
        if status == 'solved':
            params['status'] = cls._status_solved
        if status == 'assigned':
            params['assigned_id'] = uid
        if status == 'closed':
            params['status'] = cls._status_closed
        if status == 'wait':
            params['status'] = cls._status_wait
        if status == 'create':
            params['creator_id'] = uid
        if get_num:
            num = int(cls.number(**params))
        params['page'] = page
        params['order_by'] = order_by
        tasks = cls.page(**params)
        if get_num:
            return tasks, num
        return tasks

    @classmethod
    def assigned_tasks(cls, user_id, pid=None, order_by='priority desc'):
        # 连表, 从消息表中获取用户的指派用户
        pid_d = {'project_id': pid} if pid else {}
        return cls.find(
            join=join_(table='message', on_str='message.task_id=task.id',
                       type=Message._type_assigned, user_id=user_id),
            status__le=cls._status_wait,
            order_by=order_by,
            **pid_d
        )
        # assigned_ids = [m.task_id for m in Message.find(user_id=user_id, type=Message._type_assigned)]
        # return cls.page(assigned_id=user_id, status__le=cls._status_wait, page=page, order_by='priority desc')

    @property
    def type_name(self):
        return self._type.get(self.type)

    @property
    def priority_name(self):
        return self._priority.get(self.priority)

    @property
    def status_name(self):
        return self._status.get(self.status)

    @property
    def is_done(self):
        return self.status == self._status_closed or self.status == self._status_solved

    @property
    def type_icon(self):
        return self._type_icon.get(self.type)

    @property
    def assigned_users(self):
        try:
            na = json.loads(self.assigneds)
            ids = set([ud['id'] for ud in na])
            if self.assigned_id and self.assigned_name and self.assigned_id not in ids:
                na.append({'id': self.assigned_id, 'name': self.assigned_name})
            return na
        except (ValueError, TypeError):
            return []

    @property
    def assigned_names(self):
        return set([u['name'] for u in self.assigned_users])

    @property
    def assigned_ids(self):
        return set([u['id'] for u in self.assigned_users])

    def get_diff(self, data):
        """ 设置更新日志
        """
        diffs = []
        for field, name in self._checks.items():
            old = getattr(self, field)
            new = data.get(field)
            if field == 'status':
                old = self._status.get(int(old))
                new = self._status.get(int(new))
            elif field == 'priority':
                old = self._priority.get(int(old))
                new = self._priority.get(int(new))
            elif field == 'type':
                old = self._type.get(int(old))
                new = self._type.get(int(new))
            elif field == 'assigneds':  # 指派用户对比, 取名字即可
                old = self.assigned_names
                new = set([ud['name'] for ud in json.loads(new)])
                old = ','.join(sorted(old))
                new = ','.join(sorted(new))
            elif field == 'expires':
                old = date_to_str(old) if old else None
                new = date_to_str(new) if new else None
                if new:
                    new = new[: 10]
                if old:
                    old = old[: 10]
            new = new or ''
            old = old or ''
            old = old.strip()
            new = new.strip()
            if old != new:
                if not old:
                    t = 'set'
                elif not new:
                    t = 'del'
                else:
                    t = 'update'
                if field == 'desc':  # 描述只记录前20个字符
                    old = old[: 20]
                    new = new[: 20]
                diffs.append((name, old, new, t))
        return json.dumps(diffs)

    def update_and_log(self, data, actor_id, actor_name, note):
        """ 更新任务以及记录日志
        """
        try:
            diffs = self.get_diff(data)
            if not data['expires']:
                # data.pop('expires')
                data['expires'] = None
            # 删除旧版数据
            data['assigned_id'] = 0
            data['assigned_name'] = ''
            error = self.update(**data)
            note = note.strip()
            if len(diffs) > 2 or note:
                TaskLog.new(
                    task_id=self.id,
                    desc=diffs,
                    note=note,
                    updater_id=actor_id,
                    updater_name=actor_name,
                )
            if not error:
                return Task.get(id=self.id)
            return None
        except Exception as ex:
            print str(ex)
            return None


class TaskForm(Form):
    """ 任务创建表单
    """
    title = StringField(u'标题', validators=[required(u'请填写任务标题')])
    status = SelectField(u'状态', choices=Task._status.items(), coerce=int)
    priority = SelectField(u'优先级', choices=Task._priority.items(), coerce=int)
    type = SelectField(u'类型', choices=Task._type.items(), coerce=int)
    desc = TextField(u'描述')
    expires = StringField(u'期待时间')  # 默认为空
    # view to fill and validate
    project_id = IntegerField()
    creator_id = IntegerField()
    creator_name = StringField()
    # assigned_id = IntegerField()
    # assigned_name = StringField()
    assigneds = StringField()  # 指派用户构成, json
    created = DateTimeField()

    def __init__(self, handler=None, formdata=None, obj=None, prefix='', data=None, meta=None, **kwargs):
        if formdata and handler:
            # 获取指派用户
            assigned_ids = [int(sid) for sid in formdata['assigneds'][0].split(',')] if formdata['assigneds'][0] else []
            assigned_ids = set(assigned_ids)
            assigneds = [ud for ud in handler.p_users if ud['id'] in assigned_ids]
            formdata['assigneds'] = [json.dumps(assigneds), ]
            # 填充剩余表单数据
            formdata['creator_id'] = [str(handler.user.id), ]
            formdata['creator_name'] = [handler.user.name, ]
            formdata['project_id'] = [handler.pid, ]
            formdata['created'] = [date_to_str(datetime.now()), ]
        super(TaskForm, self).__init__(formdata, obj, prefix, **kwargs)

    def __getattr__(self, key):
        return self.data.get(key)