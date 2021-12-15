import asyncio
import msgpack
import logging

from msgpackio.rpc import REQUEST, NOTIFY, RESPONSE
from msgpackio.exceptions import RemoteException, NoMethod

log = logging.getLogger(__name__)


class Bindings:
    def __init__(self, obj, kwargs):
        self.obj = obj
        self.dict = kwargs

    def get(self, item, default=None):
        if isinstance(item, bytes):
            item = item.decode("utf-8")

        if hasattr(self.obj, item):
            return getattr(self.obj, item)

        return self.dict.get(item, default)

    def __setitem__(self, item, value):
        self.dict[item] = value


class RPCServer(asyncio.Protocol):
    def __init__(self, bindings=None, **kwargs):
        self.unpacker = msgpack.Unpacker()
        self.packer = msgpack.Packer(default=lambda x: x.to_msgpack())
        self.count = 0
        self.message_kinds = {
            REQUEST: self.on_request,
            NOTIFY: self.on_notify,
        }
        self.bindings = Bindings(bindings, kwargs)

    def add_bindings(self, name, function):
        self.bindings[name] = function

    def connection_made(self, transport):
        log.debug("Server: A connection was made")
        self.transport = transport

    def data_received(self, data):
        log.debug(f"Server: Receiving data {data}")

        self.unpacker.feed(data)
        for message in self.unpacker:
            self.on_message(message)

    def connection_lost(self, exc):
        log.debug("Server: The connection was lost")

    def on_message(self, msg):
        n = len(msg)
        if n != 3 and n != 4:
            log.error(f"Wrong RPC format {msg}")
            return

        handler = self.message_kinds.get(msg[0], None)

        if handler is None:
            log.error(f"{msg[0]} is not supported for server")
            return

        return handler(*msg[1:])

    def on_request(self, msgid, method, params):
        function = self.bindings.get(method, None)
        result = None
        error = None

        if function is None:
            error = NoMethod(f"`{method}` is not available")
        else:
            result = function(*params)

        self.transport.write(self.packer.pack([RESPONSE, msgid, error, result]))

    def on_notify(self, method, params):
        method = self.bindings.get(method)

        if method is None:
            log.error(f"{method} is not a method")
            return

        method(*params)
