from msgpackio.compat import Server


class SumServer(object):
    def sum(self, x, y):
        return x + y


server = Server(SumServer())
server.listen("localhost", 18800)
server.start()
