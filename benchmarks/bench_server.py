import msgpackrpc
from msgpackio.compat import Server


class SumServer(object):
    def sum(self, x, y):
        return x + y


def legacy():
    server = msgpackrpc.Server(SumServer())
    server.listen(msgpackrpc.Address("localhost", 18800))
    server.start()


def new():
    server = Server(SumServer())
    server.listen("localhost", 18800)
    server.start()


new()
# legacy()
