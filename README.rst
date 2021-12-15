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

Overview
~~~~~~~~~

* New server with new client
* Legacy server with legacy client

+--------+----------------------+------------------+-----------+
|        | msgpackrpc (legacy)  | msgpackio (new)  | Speed up  |
+========+======================+==================+===========+
| call:  | 9300.36              | 15785.75         | 1.69      |
+--------+----------------------+------------------+-----------+
| async  | 8625.17              | 15894.88         | 1.84      |
+--------+----------------------+------------------+-----------+
| notify | 47751.91             | 208592.96        | 4.36      |
+--------+----------------------+------------------+-----------+


New Client vs Legacy Client
~~~~~~~~~~~~~~~~~~~~~~~~~~~

* use legacy server
* change client

+--------+----------------------+------------------+-----------+
|        | msgpackrpc (legacy)  | msgpackio (new)  | Speed up  |
+========+======================+==================+===========+
| call:  | 8913.07              | 18049.83         | 2.02      |
+--------+----------------------+------------------+-----------+
| async  | 9145.02              | 17972.45         | 1.96      |
+--------+----------------------+------------------+-----------+
| notify | 52621.65             | 230716.13        | 4.38      |
+--------+----------------------+------------------+-----------+


New Server vs Legacy Server
~~~~~~~~~~~~~~~~~~~~~~~~~~~

* use legacy client
* change server

+--------+----------------------+------------------+-----------+
|        | msgpackrpc (legacy)  | msgpackio (new)  | Speed up  |
+========+======================+==================+===========+
| call   | 8913.07              | 13632.59         | 1.52      |
+--------+----------------------+------------------+-----------+
| async  | 9145.02              | 13844.42         | 1.51      |
+--------+----------------------+------------------+-----------+
| notify | 52621.65             | 49555.3925       | 0.94      |
+--------+----------------------+------------------+-----------+


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
