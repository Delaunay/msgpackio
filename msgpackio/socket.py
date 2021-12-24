# Copyright Epic Games, Inc. All Rights Reserved.

import threading
import time
import socket
import logging

import msgpack
import numpy as np

DEFAULT_PORT = 15151
LOCALHOST = 'localhost'
REQUEST = 0
RESPONSE = 1
NOTIFY = 2


logger = logging.getLogger(__name__)


class RemoteException(Exception):
    pass


class SocketClient:
    """Simple client that does not rely on the outdated msgpackrpc lib

    Notes
    -----
    It also looks to be more reliable.
    It has a lot less moving parts.

    """

    FUNCNAME_LIST_FUNCTIONS = "list_functions"
    FUNCNAME_PING = "ping"

    def __init__(
        self,
        server_address=LOCALHOST,
        server_port=DEFAULT_PORT,
        timeout=20,
        reconnect_limit=1024,
        **kwargs,
    ):
        self.host = server_address
        self.port = server_port
        self.packer = msgpack.Packer()
        self.unpacker = msgpack.Unpacker()
        self.buffer = np.empty(8192, dtype="<u1")
        self.uid = 0
        self.timeout = timeout
        self.retries = reconnect_limit

    def connect(self, retries=None, timeout=None, sleep_step=1):
        if timeout is None:
            timeout = self.timeout

        if retries is None:
            retries = self.retries

        start = time.time()

        for i in range(retries):
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            try:
                self.sock.connect((self.host, self.port))
                logger.info(
                    f"Connected after %5.2f s  and %d retries", time.time() - start, i
                )
                return
            except ConnectionRefusedError:
                pass

            time.sleep(sleep_step)

            if timeout and time.time() - start > timeout:
                raise TimeoutError()
        else:
            raise ConnectionRefusedError()

    def ensure_connection(self):
        self.call(SocketClient.FUNCNAME_PING)

    def call(self, method, *args):
        """Call a RPC, re-connect once if the connection drops"""

        for i in range(2):
            try:
                return self._call(method, *args)
            except ConnectionResetError:
                if i == 0:
                    self.connect()
                else:
                    raise

    def _call(self, method, *args):
        msgid1 = self.send_message(method, args)
        kind, msgid2, error, result = self.receive_message()

        assert kind == RESPONSE
        assert msgid1 == msgid2

        if error is None:
            return result

        raise RemoteException(error)

    def send_message(self, method, args):
        uid = self.uid
        payload = msgpack.packb([REQUEST, uid, method, args])
        self.sock.sendall(payload)
        self.uid += 1
        return uid

    def receive_message(self):
        while True:
            size = self.sock.recv_into(self.buffer)
            self.unpacker.feed(memoryview(self.buffer[:size]))

            for msg in self.unpacker:
                return msg

    def _add_function(self, function_name):
        self.__dict__[function_name] = lambda *args: self.call(function_name, *args)

    def add_functions(self):
        self.ensure_connection()

        function_list = self.call(SocketClient.FUNCNAME_LIST_FUNCTIONS)

        for fname in map(lambda x: x.decode("utf-8"), function_list):
            self._add_function(fname)

        logger.debug("Functions bound: {}".format(function_list))

    @property
    def connected(self):
        try:
            self.ensure_connection()
            return True
        except:
            return False
