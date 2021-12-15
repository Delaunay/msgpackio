class RemoteException(Exception):
    CODE = ".RemoteException"

    def __init__(self, message):
        Exception.__init__(self, message)
        self.message = message

    @property
    def code(self):
        return self.__class__.CODE

    def to_msgpack(self):
        return [self.code, self.message]

    @staticmethod
    def from_msgpack(message):
        return RemoteException(f"{message[0]}: {message[1]}")


class NoMethod(RemoteException):
    CODE = ".NoMethod"
    pass
