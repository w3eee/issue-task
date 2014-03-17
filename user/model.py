# coding: utf8

import logging

from util.Hqorm import HqOrm, or_, and_

# Form
from wtforms_tornado import Form
from wtforms.fields import IntegerField, StringField, PasswordField
from wtforms.validators import Email, DataRequired, required, length
from wtforms import ValidationError


class User(HqOrm):

    _table_name = 'user'
    _rows = ['id', 'email', 'pwd', 'name', 'admin', 'avatar', 'created', 'status']

    _default_avatar = 'default'

    _status_ok = 1
    _status_del = 0

    @classmethod
    def register(cls, email, pwd, name, admin=0):
        try:
            return cls.new(
                email=email,
                pwd=pwd,
                name=name,
                admin=admin,
                avatar=cls._default_avatar,
                status=cls._status_ok,
            )
        except Exception as ex:
            logging.error('[User Register]: Error > ' + str(ex))
            return None

    @classmethod
    def check(cls, account, pwd):
        users = cls.find(and_(or_(email=account, name=account), pwd=pwd, status=cls._status_ok))
        return users[0] if users else None


class RegisterForm(Form):

    email = StringField(u'邮箱', [required(u'必须提供邮箱'), Email(u'不是合法的邮箱地址')])
    name = StringField(u'昵称', [required(u'请填写真实姓名')])
    pwd = PasswordField(u'密码', [length(max=32, min=6, message=u'密码至少六位')])

    def validate_email(form, field):
        if User.get(email=field.data, status=User._status_ok):
            raise ValidationError(u'该邮箱已经注册, 请换个邮箱')

    def validate_name(form, field):
        if User.get(name=field.data, status=User._status_ok):
            raise ValidationError(u'该昵称已经被使用, 请更换昵称')


class LoginForm(Form):
    account = StringField(u'账户(邮箱或者昵称)', [required(u'没帐号登录啥')])
    pwd = PasswordField(u'密码', [length(max=32, min=6, message=u'密码至少六位')])


class UserForm(Form):

    email = StringField(u'邮箱', [required(u'必须提供邮箱'), Email(u'不是合法的邮箱地址')])
    name = StringField(u'姓名', [required(u'请填写真实姓名')])
    old_pwd = PasswordField(u'密码', [length(max=32, min=6, message=u'密码至少六位')])
    new_pwd = PasswordField(u'新的密码')
    avatar = StringField(u'头像')