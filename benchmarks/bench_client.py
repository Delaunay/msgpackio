import msgpackrpc
from msgpackio.compat import Client
import time

Num = 10000


def run_call(cls):
    client = cls()
    before = time.time()

    for x in range(Num):
        assert client.call("sum", 1, 2) == 3

    after = time.time()
    diff = after - before

    print(f"{cls} call: {Num / diff:.4f} qps")


def run_call_async(cls):
    client = cls()
    before = time.time()
    for x in range(Num):
        # TODO: replace with more heavy sample
        future = client.call_async("sum", 1, 2)

        assert future.get() == 3

    after = time.time()
    diff = after - before

    print(f"{cls} async: {Num / diff:.4f} qps")


def run_notify(cls):
    client = cls()
    before = time.time()
    for x in range(Num):
        client.notify("sum", 1, 2)
    after = time.time()
    diff = after - before

    print(f"{cls} notify: {Num / diff:.4f} qps")


def legacy():
    return msgpackrpc.Client(msgpackrpc.Address("localhost", 18800))


def new():
    return Client("localhost", 18800)


backends = [new, legacy]

for b in backends:
    run_call(b)
    run_call_async(b)
    run_notify(b)
