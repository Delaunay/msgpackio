msgpackio
=========

Design to replace `msgpack-rpc-python <https://github.com/msgpack-rpc/msgpack-rpc-python>`_ that has become badly out of date.


* Deprecate tornado completly
* Use Asyncio for the server
* Use standard sockets for the client


.. code-block:: bash

   pip install msgpackio


Bemchmark
=========




Compatibility
=============

Server
~~~~~~

.. code-block:: python

   from msgpackio.compat import Server

   class SumServer(object):
      def sum(self, x, y):
         return x + y

   server = Server(SumServer())
   server.listen("localhost", 18800)
   server.start()


Client
~~~~~~

.. code-block:: python

   from msgpackio.compat import Client

   client = Client("localhost", 18800)
   result = client.call('sum', 1, 2)         # = > 3

   future = client.call_async('sum', 1, 2)  
   result = future.get()                     # = > 3
