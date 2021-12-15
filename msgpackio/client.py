import logging
import select
import socket
import time
import queue
import multiprocessing as mp
import traceback
import msgpack

log = logging.getLogger(__name__)

try:
    # numpy buffers are faster
    import numpy as np

    def byte_buffer(size):
        return np.empty(size, dtype="<u1")

except ImportError:

    def byte_buffer(size):
        return bytearray(size)


class Client:
    """Connect to a server, send & receive message encoded using msgpack"""

    def __init__(self, host, port, wqueue=None, rqueue=None, state=None):
        self.host = host
        self.port = port

        self.sock = None
        self.buffer = byte_buffer(8192)

        self.packer = msgpack.Packer(default=lambda x: x.to_msgpack())
        self.unpacker = msgpack.Unpacker()
        self.pending = []

        # For Async
        self.state = state
        self.wqueue = wqueue
        self.rqueue = rqueue

    def close(self):
        if self.sock:
            self.sock.close()

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        self.close()
        return

    @property
    def running(self):
        if self.state is None:
            return self.sock is not None

        return self.state["running"]

    def connect(self, retries=20, sleep_time=0.01):
        if self.sock is None:
            self.sock = self._connect(retries, sleep_time)

    def _connect(self, retries, sleep_time):
        pending = None
        s = None

        for i in range(retries):
            if s is not None:
                s.close()

            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setblocking(True)
                s.connect((self.host, self.port))
                log.debug(f"Connection established after {i} retries")

                for p in self.pending:
                    s.sendall(p)

                self.pending = []
                return s

            except ConnectionRefusedError as err:
                pending = err
                time.sleep(sleep_time)
        else:
            log.debug("Could not establish connection")

            if pending is not None:
                raise pending

        return None

    def recv(self, timeout=None):
        """Receive a message from the server"""
        start = time.time()
        size = 0

        while True:
            size = self.sock.recv_into(self.buffer)

            if size > 0:
                break

            if timeout is not None and time.time() - start > timeout:
                return None

        self.unpacker.feed(memoryview(self.buffer[:size]))

        try:
            return next(self.unpacker)
        except StopIteration:
            return None

    def send(self, msg):
        """Send a message to the server"""
        msg = self.packer.pack(msg)

        if self.sock is None:
            self.pending.append(msg)
            return 0

        self.sock.sendall(msg)
        return
