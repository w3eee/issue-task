# coding: utf8

from util.Hqorm import HqOrm

# form
from wtforms_tornado import Form
from wtforms.fields import IntegerField, StringField
from wtforms.validators import required


class Comment(HqOrm):

    _table_name = 'comment'
    _rows = [
        'id', 'from_user_id', 'from_user_name', 'to_user_id', 'to_user_name',
        'task_id', 'task_title', 'content', 'type', 'parent', 'created',
    ]
    _type_at = 1
    _type_reply = 2

    @property
    def type_icon(self):
        return {
            self._type_at: 'fa-comments-o',
            self._type_reply: 'fa-comment-o',
        }.get(self.type)


class CommentForm(Form):

    from_user_id = IntegerField(validators=[required(), ])
    from_user_name = StringField(validators=[required(), ])
    to_user_id = IntegerField(validators=[required(), ])
    to_user_name = StringField(validators=[required(), ])
    task_id = IntegerField(validators=[required(), ])
    task_title = StringField(validators=[required(), ])
    type = IntegerField(validators=[required(), ])
    content = StringField(validators=[required(u'评论内容不可为空'), ])