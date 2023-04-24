from time import sleep

import requests
import threading


def make_request(url, delay=0):
    def target():
        sleep(delay)
        requests.get(url)
    threading.Thread(target=target, args=()).start()


def call_func_with_delay(func, delay, args=None, kwargs=None):
    args = args or []
    kwargs = kwargs or {}

    def target():
        sleep(delay)
        func(*args, **kwargs)
    threading.Thread(target=target, args=()).start()
