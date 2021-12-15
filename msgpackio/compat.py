import asyncio
import multiprocessing as mp

from msgpackio.server import RPCServer
from msgpackio.rpc import RPCClient
from msgpackio.client import Client as SyncClient


class Server:
    """Provides the same API as ``msgpackrpc.Server`` for compatibility"""

    def __init__(self, bindings):
        self.bindings = bindings
        self.host = None
        self.port = None
        self.process = None

    def listen(self, host, port):
        self.host = host
        self.port = port

    def start(self):
        self.process = mp.Process(target=self._start)
        self.process.start()

    def stop(self):
        self.process.terminate()
        self.process.join()

    def close(self):
        self.stop()

    def _start(self):
        async def main():
            loop = asyncio.get_running_loop()

            server = await loop.create_server(
                lambda: RPCServer(self.bindings), self.host, self.port
            )

            async with server:
                await server.serve_forever()

        asyncio.run(main())


class Client:
    """Provides the same API as ``msgpackrpc.Client`` for compatibility"""

    def __init__(self, host, port):
        self.port = port
        self.host = host
        self.client = RPCClient(SyncClient(self.host, self.port))

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        self.client.close()
        return

    def close(self):
        self.client.close()

    def notify(self, method, *args):
        return self.client.notify(method, *args)

    def call(self, method, *args):
        return self.client.call(method, *args)

    def call_async(self, method, *args):
        return self.client.call_async(method, *args)
