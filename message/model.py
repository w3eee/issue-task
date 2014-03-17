# coding: utf8
# 消息设置场景: 1. 被分派任务, 2. 创建任务被评论, 3. 评论被评论 4. 私信(@)

from util.Hqorm import HqOrm, set_


class Message(HqOrm):

    _table_name = 'message'
    _rows = [
        'id', 'user_id', 'type', 'from_user_id', 'from_user_name', 'project_id', 'project_name',
        'content', 'task_id', 'task_title', 'status', 'created'
    ]
    _per_page = 10

    _type_assigned = 1
    _type_apply = 2
    _type_sys = 3
    _type_user = 4
    _type_edit = 5
    _types = {
        'assigned': _type_assigned,
        'apply': _type_apply,
        '@': _type_user,
        'edit': _type_edit,
        'sys': _type_sys,
    }
    _type_icon = {
        _type_assigned: 'fa-sign-in',
        _type_apply: 'fa-comment',
        _type_sys: 'fa-laptop',
        _type_user: 'fa-user',
        _type_edit: 'fa-edit',
    }

    _status_unread = 1
    _status_read = 0
    _status_del = 2

    @classmethod
    def user_msgs(cls, user_id, page=1):
        """ 不获取删除的消息
        """
        return cls.page(page=page, user_id=user_id, status__le=cls._status_unread, order_by='created desc')

    @classmethod
    def number(cls, args=None, **kwargs):
        return super(Message, cls).number(args=args, status__no=cls._status_del, **kwargs)

    @classmethod
    def unread_num(cls, user_id):
        return super(Message, cls).number(user_id=user_id, status=cls._status_unread)

    @classmethod
    def mark_read(cls, user_id):
        return cls.cls_update(set_(status=cls._status_read), user_id=user_id, status=cls._status_unread)

    @classmethod
    def set(cls, user_id, from_user, task, pid, pname, type, content=''):
        """ 避免重复的设定消息
        """
        type = cls._types.get(type)
        if not type:
            return None
        if type == cls._type_assigned:
            # 指派消息显示一条即可
            msg = Message.find(user_id=user_id, type=type, task_id=task.id)
            if msg:
                return msg[0]
        return Message.new(
            user_id=user_id,
            from_user_id=from_user.id,
            from_user_name=from_user.name,
            task_id=task.id,
            task_title=task.title,
            project_id=pid,
            project_name=pname,
            type=type,
            content=content,
        )

    @property
    def action(self):
        return self._types[self.type]

    @property
    def icon(self):
        return self._type_icon.get(self.type)