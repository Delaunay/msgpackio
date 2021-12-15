from enum import Enum
import time
import logging
import threading
import select


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

        self.sockets = [self.client.sock]
        self.keep_promises = True
        self.lock = threading.Lock()
        self.promise_keeper = threading.Thread(target=self._fetch_results)
        self.promise_keeper.daemon = True
        self.promise_keeper.start()

    def _fetch_results(self):
        while self.keep_promises:
            readable, _, _ = select.select(self.sockets, [], [], 0.01)

            for _ in readable:
                value = self.client.recv(0)
                self._set_future(value)

    def call(self, method, *args):
        result = self.send_request(method, args).get()
        return result

    def call_async(self, method, *args):
        return self.send_request(method, args)

    def send_request(self, method, args):
        msgid = next(self.generator)
        future = Future(self, msgid)

        with self.lock:
            self._pending_results[msgid] = future

        self.client.send([REQUEST, msgid, method, args])
        return future

    def notify(self, method, *args):
        self.client.send([NOTIFY, method, args])

    def close(self):
        self.keep_promises = False
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        self.close()
        return

    def _set_future(self, value):
        _, msgid, error, result = value

        with self.lock:
            future = self._pending_results.pop(msgid, None)

        if future is None:
            log.error(f"Server replied to an unknown future")

        future.error = error
        future.result = result
        return msgid

    def _wait_future(self, timeout, target):
        start = time.time()

        while not target.ready():
            time.sleep(0)

            if timeout:
                timeout -= time.time() - start

                if timeout < 0:
                    raise TimeoutError()
