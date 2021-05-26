#!/bin/env python
"""
A simple example of using Python sockets for a client HTTPS connection.
"""

import ssl
import socket
from urllib.parse import urlparse

url = 'http://www.baidu.com'

url = urlparse(url)
host = url.netloc
path = url.path
if path == "":
    path = "/"
print([host, path])

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host, 80))
s.sendall("GET {} HTTP/1.1\r\nHost:{}\r\nConnection:close\r\n\r\n".format(path, host).encode("utf-8"))
# s.sendall(b"GET / HTTP/1.1\r\nHost:www.baidu.com\r\nConnection:keep-alive\r\n\r\n")

while True:

    new = s.recv(4096)
    if not new:
      s.close()
      break
    print('get response')
    print(new)