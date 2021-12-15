import asyncio
import threading
import logging
import multiprocessing as mp

import pytest
import msgpack

from msgpackio.client import Client


log = logging.getLogger(__name__)


def server():
    import asyncio

    class ServerProto(asyncio.Protocol):
        def __init__(self):
            self.unpacker = msgpack.Unpacker()
            self.packer = msgpack.Packer(default=lambda x: x.to_msgpack())
            self.count = 0

        def connection_made(self, transport):
            log.debug("Server: A connection was made")
            self.transport = transport

        def data_received(self, data):
            self.unpacker.feed(data)
            for message in self.unpacker:
                self.count += 1

            self.transport.write(self.packer.pack(self.count))

        def connection_lost(self, exc):
            log.debug("Server: The connection was lost")

    async def main():
        loop = asyncio.get_running_loop()

        server = await loop.create_server(lambda: ServerProto(), "127.0.0.1", 8888)

        async with server:
            await server.serve_forever()

    asyncio.run(main())


clients = [Client]


@pytest.mark.parametrize("cls", clients)
def test_client(cls):
    import multiprocessing as mp
    import time

    s = mp.Process(target=server)
    s.start()

    try:
        with cls("127.0.0.1", 8888) as client:
            client.connect()

            client.send(b"1234")
            assert client.recv(timeout=1) == 1

            client.send(b"1234")
            assert client.recv(timeout=1) == 2
    finally:
        s.terminate()
