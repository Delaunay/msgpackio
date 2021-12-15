import asyncio
import threading
import logging
import multiprocessing as mp

import pytest
import msgpack

from msgpackio.client import Client
from msgpackio.rpc import RPCClient
from msgpackio.server import RPCServer
from msgpackio.exceptions import RemoteException


log = logging.getLogger(__name__)


def add(a, b):
    return a + b


def server(**bindings):
    import asyncio

    async def main():
        loop = asyncio.get_running_loop()

        server = await loop.create_server(
            lambda: RPCServer(**bindings), "127.0.0.1", 8888
        )

        async with server:
            await server.serve_forever()

    asyncio.run(main())


clients = [Client]


@pytest.mark.parametrize("cls", clients)
def test_rpc_client_async(cls):
    import multiprocessing as mp
    import time

    s = mp.Process(target=server, kwargs=dict(add=add))
    s.start()

    try:
        with RPCClient(cls("127.0.0.1", 8888)) as client:
            future = client.call_async("add", 1, 2)

            assert future.ready() == False
            future.wait(1)
            assert future.ready() == True
            assert future.get() == 3

    finally:
        s.terminate()


@pytest.mark.parametrize("cls", clients)
def test_rpc_client_async_missing_key(cls):
    import multiprocessing as mp
    import time

    s = mp.Process(target=server)
    s.start()

    try:
        with RPCClient(cls("127.0.0.1", 8888)) as client:
            future = client.call_async("add", 1, 2)

            assert future.ready() == False
            future.wait(1)
            assert future.ready() == True

            with pytest.raises(RemoteException):
                print(future.get())

    finally:
        s.terminate()
