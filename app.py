#!/usr/bin/env python

import os.path
import sys

sys.path.append(os.path.dirname(__file__))

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from config import configs
from util import db


class Application(tornado.web.Application):
    def __init__(self):
        init_db = db.get_conn('hqerp')
        handlers = []
        handler_mods = [
            'task',
            'user',
            'message',
        ]
        for i in handler_mods:
            m = __import__(i+'.view', fromlist=['url_spec'])
            handlers.extend(m.url_spec())
        handler_mods = [
            'index',
        ]
        for i in handler_mods:
            m = __import__(i, fromlist=['url_spec'])
            handlers.extend(m.url_spec())

        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), 'templates'),
            static_path=os.path.join(os.path.dirname(__file__), 'static'),
            cookie_secret=configs['cookie_secret'],
            debug=configs['debug'],
            xsrf_cookies=True,
            gzip=True
        )
        tornado.web.Application.__init__(self, handlers, **settings)


def main():
    http_server = tornado.httpserver.HTTPServer(Application(), xheaders=True)
    http_server.listen(configs['port'])
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()

