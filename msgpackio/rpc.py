from enum import Enum
import time
import logging

from msgpackio.client import Client
from msgpackio.future import Future


class LostFuture(Exception):
    pass


REQUEST = 0
RESPONSE = 1
NOTIFY = 2


def _seq():

    value = 0
    while True:

        yield value
        value += 1
        if value > (1 << 30):
            value = 0


log = logging.getLogger(__name__)


class RPCClient:
    def __init__(self, client: Client):
        self.client = client
        self.client.connect()

        self.generator = _seq()
        self._pending_results = dict()

    def call(self, method, *args):
        result = self.send_request(method, args).get()
        return result

    def call_async(self, method, *args):
        return self.send_request(method, args)

    def send_request(self, method, args):
        msgid = next(self.generator)
        future = Future(self)
        self._pending_results[msgid] = future
        self.client.send([REQUEST, msgid, method, args])
        return future

    def notify(self, method, *args):
        future = Future(self)
        self.client.send([NOTIFY, method, args])
        return future

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        self.close()
        return

    def _fetch_future(self, timeout, step=0.01):
        wait_time = 0
        start = time.time()

        while True:
            value = self.client.recv(timeout)

            if value is None:
                wait_time = time.time() - start

                if timeout is not None and wait_time > timeout:
                    raise TimeoutError()

                continue

            kind, msgid, error, result = value
            assert kind == RESPONSE
            future = self._pending_results.pop(msgid, None)

            if future is None:
                raise LostFuture(f"Server replied to an unknown future")

            future.error = error
            future.result = result
            return msgid
