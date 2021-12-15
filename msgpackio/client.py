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

    # Async version when the client is instantiated
    # inside a subprocess

    def _async_send(self):
        """Send request from the AsyncClient"""
        try:
            item = self.wqueue.get(block=False)
            self.send(item)

        except queue.Empty:
            pass

    def _async_recv(self):
        """Send replies back to the AsyncClient"""
        size = self.sock.recv_into(self.buffer)
        self.unpacker.feed(memoryview(self.buffer[:size]))

        for msg in self.unpacker:
            self.rqueue.put(msg)

    def _loop(self):
        """Work loop when executed inside a separate process"""
        if not self.running:
            return

        readable, _, error = select.select([self.sock], [], [self.sock], 0.01)

        self._async_send()

        for _ in readable:
            self._async_recv()

        for err in error:
            err.close()
            log.debug(f"socket error")
            self.state["running"] = False

    def _run(self):
        """Top level work loop when executed inside a separate process"""
        self.connect(sleep_time=1)

        if self.sock is None:
            self.state["running"] = False
            raise RuntimeError("Impossible to connect to the game")

        self.state["running"] = True
        while self.running:
            try:
                self._loop()

            except KeyboardInterrupt:
                log.debug("user interrupt")
                self.state["running"] = False
                break

            except Exception:
                self.state["running"] = False
                log.error(traceback.format_exc())

        self.close()
        log.debug("Server is shutting down")


def _sync_client(host, port, wqueue, rqueue, state, level):
    try:
        import coverage

        coverage.process_startup()
    except ImportError:
        pass

    logging.basicConfig(level=level)
    wl = Client(host, port, wqueue, rqueue, state)
    wl._run()


def _seq():
    value = 0
    while True:

        yield value
        value += 1
        if value > (1 << 30):
            value = 0


class AsyncClient:
    """Create a client inside a subprocess"""

    def __init__(self, host, port):
        self.manager = mp.Manager()
        self.state = self.manager.dict()
        self.rqueue = self.manager.Queue()
        self.wqueue = self.manager.Queue()
        self.generator = _seq()

        self.client = mp.Process(
            name=f"Client",
            target=_sync_client,
            args=(host, port, self.wqueue, self.rqueue, self.state, logging.DEBUG),
        )
        self.client.start()

    @property
    def running(self):
        return self.state.get("running", False)

    def connect(self, *args, **kwargs):
        pass

    def close(self):
        self.state["running"] = False
        self.client.terminate()

    def __enter__(self):
        self.manager.__enter__()
        return self

    def __exit__(self, a, b, c):
        self.close()
        return self.manager.__exit__(a, b, c)

    def send(self, data):
        self.wqueue.put(data)

    def recv(self, timeout=None):
        try:
            return self.rqueue.get(block=timeout is not None, timeout=timeout)
        except queue.Empty:
            return None
