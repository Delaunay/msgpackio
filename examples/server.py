from msgpackio.compat import Client

client = Client("localhost", 18800)
result = client.call("sum", 1, 2)  # = > 3

future = client.call_async("sum", 1, 2)
result = future.get()  # = > 3
