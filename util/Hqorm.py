#!/usr/bin/env python
# coding: utf-8

#TODO 添加缓存功能
#DO 添加连表功能
#TODO 添加事务支持
#TODO 支持同一字段的逻辑运算

import db
from config import configs

import logging


#设置使用的数据库名称
_DATABASE_NAME = configs['db_name']


# 定义异常
class RowError(Exception):
    """ 不存在的更新列导致异常
    """
    pass


def date_to_str(d, format='%Y-%m-%d %H:%M:%S'):
    if not d:
        return ''
    return d.strftime(format)


# 比较运算 exam: age__gt = 34 //age 大于34
_COMS = {'gt': '>',  # 大于
         'lt': '<',  # 小于
         'ge': '>=',  # 大于等于
         'le': '<=',  # 小于等于
         'no': '<>',  # 不等于
         'like': ' like ', }


def _rebuild_argv(kwargs, args=None, rows=None, link=' and ', table=None):
    """ 重构字典参数,以及连接成sql语句需要的字符串
        args: (re_str, values)
        kwargs: key, value dict
        return where expr
    """
    keys = kwargs.keys()
    check_keys = [k.split('__')[0] for k in keys]
    # 检测更新列是否都在表列中
    if rows and not set(check_keys).issubset(set(rows)):
        return None, None
    re_str = []
    for k in keys:
        com = '='
        if '__' in k:
            k1, k2 = k.split('__')
            if k2 == 'like':
                kwargs[k] = '%' + kwargs[k] + '%'
            com = _COMS.get(k2, '=')
            if com != '=':
                k = k1
        k = '`' + k + '`'
        re_str.append(table + '.' + k + com + '%s' if table else k + com + '%s')
    values = kwargs.values()
    if args:
        re_str.append(args[0])
        values.extend(args[1])
    re_str = link.join(re_str)
    re_str = ' (' + re_str + ') ' if kwargs else re_str
    return re_str, values


def and_(args=None, **kwargs):
    """
        args: (keys_str, values)
        kwargs: key=value
        return: (keys_str, values) tuple
    """
    return _rebuild_argv(kwargs, link=' and ', args=args)


def or_(args=None, **kwargs):
    return _rebuild_argv(kwargs, link=' or ', args=args)


def where_(args=None, **kwargs):
    return _rebuild_argv(kwargs, link=' and ', args=args)


def set_(**kwargs):
    return _rebuild_argv(kwargs, link=' , ')


def _to_sql(sql):
    return sql.replace('\"', '\'').replace('\'', '`')


def list_to_sql(l, table=''):
    """ 列表列转换sql语句返回, 如果是字符串形式的sql, 直接返回
    """
    if isinstance(l, (str, unicode)):
        return l
    if table:
        table += '.'
    return ','.join([table+'`'+str(i)+'`' for i in l])


def join_(table, on_str, **kwargs):
    """
        join_(table='items', on_str='items.id=topic_item.item_id', status=1)
    """
    join_str = ' JOIN `' + table + '` on ' + on_str
    re_str, values = _rebuild_argv(kwargs, table=table)
    return join_str, re_str, values


def _execute_sql(sql, values, mode='execute'):
    """ 连接到数据库执行sql语句, mode: execute/get/query
    """
    if mode not in ['execute', 'get', 'query']:
        return None
    if configs['debug']:
        logging.info('[HqOrm Gen-SQL]:' + sql % tuple(values))
    dbc = db.get_conn(_DATABASE_NAME)
    return getattr(dbc, mode)(sql, *values)


class HqOrm(object):

    # 必须在子类中重置的属性
    _table_name = None  # 数据库表名
    _rows = None  # 表列名

    # 可选提供属性
    _per_page = 10

    # 内置属性, 外部不使用
    __dirty_data = {}

    def __init__(self, data):
        """ data must be a dict
        """
        #self._table_name = '_'.join(i.lower() for i in re.findall(r'[A-Z][a-z]+', self.__class__.__name__))
        #设置数据属性
        for k in data:
            self.__setattr__(k, data[k])
        self.__dirty_data = {}

    def __setattr__(self, key, value):
        """ 设置属性
        """
        object.__setattr__(self, key, value)
        if key in self._rows:
            self.__dirty_data[key] = value

    # 定义类级别的操作方法
    @classmethod
    def new(cls, **kwargs):
        """ 新建一条记录并保存到数据库, 返回对象
        """
        if not kwargs:
            return None

        keys = kwargs.keys()
        values = kwargs.values()

        row_names = _to_sql(str(keys)[1:-1])
        row_values = ','.join(['%s'] * len(values))

        if not row_names or not row_values:
            raise Exception('New object error', 'empty data')
        assert dict(zip(keys, values)) == kwargs
        # 构建sql插入语句
        sql = "INSERT INTO `" + cls._table_name + "` ( " + row_names + " ) VALUES ( " + row_values + " ) "
        max_try = 3
        for i in range(max_try):
            try:
                #sql = 'BEGIN; ' + sql + '; COMMIT;'
                nid = _execute_sql(sql, values, mode='execute')
                #nid = _execute_sql('SELECT LAST_INSERT_ID();', [], 'execute')
            except Exception as ex:
                #_execute_sql('ROLLBACK;', [], mode='execute')
                if ex[0] == 1062:
                    continue
                else:
                    raise ex
            break
        else:
            #_execute_sql('ROLLBACK;', [], mode='execute')
            raise Exception(cls.__name__ + ' error', ex[1])
        add = cls.get(id=nid)
        add.__dirty_data = {}
        # 清理脏数据
        return add  # 返回对象

    @classmethod
    def new_mul(cls, *items):
        """ 新建多个记录到数据库, 返回新建对象列表, 参数items为字典列表
        sql_rows = _to_sql(str(items[0].keys())[1:-1])
        values = []
        data_len = len(items[0])
        for data in items:
            values.extend(data.values())
        row_values = ('(' + ','.join(['%s']) * data_len + ')') * len(items)
        sql = 'INSERT INTO `' + cls._table_name + '` (' + sql_rows + ') VALUES ' + row_values
        """
        news = []
        if not items:
            return []
        for data in items:
            news.append(cls.new(**data))
        return news

    @classmethod
    def get(cls, fields=None, **kwargs):
        """ 获取单个对象, 根据id获取, 取得多个对象将导致异常
        """
        is_o = False
        if not fields:
            is_o = True
            fields = cls._rows
        assert set(fields).issubset(set(cls._rows))
        re_str, values = _rebuild_argv(kwargs, rows=cls._rows)  # if id is None else ('id=%s', [id])
        sql = 'SELECT %s FROM `%s`  WHERE %s LIMIT 1' % (list_to_sql(fields), cls._table_name, re_str)
        #sql = 'SELECT ' + _to_sql(str(cls._rows)[1:-1]) + ' FROM `' + cls._table_name + '` WHERE ' + re_str + ' LIMIT 1'
        o = _execute_sql(sql, values, mode="get")
        if is_o and o:
            return cls(o)
        return o

    @classmethod
    def find(cls, args=None, join=None, fields=None, **kwargs):
        """ 根据条件获取多个对象, 返回对象列表, 支持单张连表
            exam: find(id=id, name=name) -- and
        """
        is_o = False
        if not kwargs and not args:  # 没有条件, 直接返回空
            return []
        if not fields:
            is_o = True
            fields = cls._rows
        order_by = kwargs.get('order_by', '')
        limit = kwargs.get('limit', '')
        if order_by:
            order_by = ' ORDER BY ' + order_by
            del kwargs['order_by']
        if limit != '':  # 避免limit=0的bug
            limit = ' LIMIT ' + str(limit)
            del kwargs['limit']
        table = cls._table_name if join else ''
        re_str, values = _rebuild_argv(kwargs, args=args, rows=cls._rows, table=table)
        if not re_str or not values:
            return []
        join_sql = ''
        if join:
            # is_o = False
            re_str = re_str + ' AND ' + join[1]
            values.extend(join[2])
            join_sql = join[0]
        sql = 'SELECT %s FROM `%s` %s WHERE %s %s %s' % (list_to_sql(fields, table=table), cls._table_name,
                                                         join_sql, re_str, order_by, limit)
        #sql = 'SELECT ' + list_to_sql(fields) + ' FROM `' + cls._table_name + '`' + join_sql + ' WHERE '\
        #      + re_str + order_by + limit
        datas = _execute_sql(sql, values, mode='query')
        if not is_o:
            return datas
        return [cls(o) for o in datas] if datas else []

    @classmethod
    def all(cls):
        sql = 'select %s from %s ' % (list_to_sql(cls._rows), cls._table_name)
        return _execute_sql(sql, [], mode='query')

    @classmethod
    def page(cls, page, args=None, join=None, fields=None, **kwargs):
        """ 页数从第1页开始, 支持单张连表
            page: 页数
            args: and, or支持
            join: join exp [table, join_col, table.col]
            fields: 连表获取的列字符串 exam: 'items.*'
            kwargs: 限制条件
        """
        #assert 'limit' not in kwargs
        is_o = False
        page = int(page)
        if page:
            page -= 1
        if not fields:
            is_o = True
            fields = cls._rows
        beg = page * cls._per_page
        order_by = kwargs.get('order_by', '')
        if order_by:
            order_by = ' ORDER BY ' + order_by
            del kwargs['order_by']
        table = cls._table_name if join else ''
        re_str, values = _rebuild_argv(kwargs, args=args, rows=cls._rows, table=table)
        if not re_str or not values:
            return []
        join_sql = ''
        if join:
            re_str = re_str + ' AND ' + join[1]
            values.extend(join[2])
            join_sql = join[0]
        page_limit = ' LIMIT %s OFFSET %s' % (cls._per_page, beg)
        sql = 'SELECT %s FROM `%s` %s WHERE %s %s %s ' % (list_to_sql(fields, table=table), cls._table_name,
                                                          join_sql, re_str, order_by, page_limit)
        #sql = 'SELECT ' + list_to_sql(fields) + ' FROM `' +\
        #      cls._table_name + '`' + join_sql + ' WHERE ' + re_str + order_by + page_limit
        datas = _execute_sql(sql, values, mode='query')
        if not is_o:
            return datas
        return [cls(o) for o in datas] if datas else []

    @classmethod
    def delete(cls, args=None, **kwargs):
        """ 删除相关对象, 直接生效, 谨慎操作
        """
        re_str, values = _rebuild_argv(kwargs, args=args, rows=cls._rows)
        if not re_str or not values:
            return False
        sql = 'DELETE FROM `%s` WHERE %s' % (cls._table_name, re_str)
        return _execute_sql(sql, values, mode='execute')

    @classmethod
    def number(cls, args=None, **kwargs):
        """ 计数
        """
        re_str, values = _rebuild_argv(kwargs, args=args, rows=cls._rows)
        sql = 'SELECT COUNT(*) FROM `%s` WHERE %s' % (cls._table_name, re_str)
        result = _execute_sql(sql, values, mode='query')
        return int(result[0].get('COUNT(*)', 0)) if result else 0

    @classmethod
    def cls_update(cls, sets=None, args=None, **kwargs):
        """
            类级别的更新方法
            usage: Cls.cls_update(set_(a=32, b=34), and_(id=3, status=0))
        """
        if sets is None:
            return 0
        set_keys, set_values = sets
        set_keys = set_keys.replace('(', '').replace(')', '')
        re_str, values = _rebuild_argv(kwargs, args=args, rows=cls._rows)
        #set_values.extend(values)
        sql = 'UPDATE `%s` SET %s WHERE %s' % (cls._table_name, set_keys, re_str)
        set_values.extend(values)
        return _execute_sql(sql, set_values, mode='execute')

    # 对象级别方法
    def update(self, **kwargs):
        """ 更新对象多个值, 单个值直接设置并调用save方法即可
        """
        re_str, values = _rebuild_argv(kwargs, args=None, rows=self._rows, link=' , ')
        if not re_str or not values:
            return None
        re_str = re_str.replace('(', '').replace(')', '')  # update 语句不可包含括号
        sql = 'UPDATE `%s` SET %s WHERE `id` = "%s"' % (self._table_name, re_str, self.id)
        return _execute_sql(sql, values, mode='execute')

    def save(self):
        """ 保存更改到数据库
        """
        if not self.__dirty_data:
            return self
        self.update(**self.__dirty_data)
        self.__dirty_data = {}
        return self

    def be_clean(self):
        self.__dirty_data.clear()

    def dictify(self, fields=None, properties=None):
        """ 对象数据包装, 返回字典
        """
        if properties is None:
            properties = []
        data = {}
        for k, v in self.__dict__.items():
            if fields and k in fields:
                data[k] = v
            elif not k.startswith('_') and fields is None:
                data[k] = v
        for attr in properties:
            if hasattr(self, attr) and attr not in data:
                data[attr] = getattr(self, attr)
        if 'created' in data:
            data['created'] = date_to_str(data['created'])
        if 'updated' in data:
            data['updated'] = date_to_str(data['updated'])
        if 'expires' in data:
            data['expires'] = date_to_str(data['expires'])
        if 'ins_time' in data:
            data['ins_time'] = date_to_str(data['ins_time'])
        return data
