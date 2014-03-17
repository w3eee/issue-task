# coding: utf8

import datetime


class Paginator(object):

    _per_page = 15
    _pi = 5

    def __init__(self, page, num, per_page=None):
        """ page: 当前页
            num: 数量
            per_page: 每一页数量
        """
        page = int(page)
        self.per_page = per_page or self._per_page
        num = (num * 1.0) / per_page
        if num > int(num):
            num += 1
        num = int(num)
        self.num = num
        self.page = page

    @property
    def pages(self):
        prange = self._pi / 2
        first = self.page - prange
        last = self.page + prange
        if first < 1:
            last += 1 - first
            first = 1
        if last > self.num:
            first -= last - self.num
            last = self.num
        if first < 1:
            first = 1
        return [i for i in range(first, last+1)]

    @property
    def prev(self):
        prev = self.page - 1
        return prev if prev > 0 else None

    @property
    def next(self):
        next = self.page + 1
        return None if next > self.num else next


def date_to_str(d, format='%Y-%m-%d %H:%M:%S'):
    if not d or not isinstance(d, datetime.datetime):
        return d
    return d.strftime(format)