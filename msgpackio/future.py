import time

from msgpackio.exceptions import RemoteException


class _Nothing:
    """A RPC could return None"""

    pass


class Future:
    def __init__(self, client):
        self.client = client
        self.result = _Nothing
        self.error: Exception = None

    def get(self, timeout=None):
        if not self.ready():
            self.client._fetch_future(timeout, step=0.001)

        if self.error is not None:
            raise RemoteException.from_msgpack(self.error)

        return self.result

    def wait(self, timeout):
        if self.ready():
            return

        try:
            self.client._fetch_future(timeout, step=0.001)
        except TimeoutError:
            pass

    def ready(self):
        return not (self.result is _Nothing and self.error is None)

    def successful(self):
        if not self.ready():
            raise ValueError()

        return self.error is None
