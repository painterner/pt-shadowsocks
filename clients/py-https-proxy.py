import socket
import struct
import json
from typing import Any
import asyncio
import traceback
import ssl

proxy = {
    "url": ('127.0.0.1', 1081)
}

def str2bytes(string: str):
    return bytes(string, "utf8")

def obj2bytes(obj : Any):
    s = json.dumps(obj)
    return str2bytes(s)

# bytes("\uxxx", "unicode")
# SyntaxError: (unicode error) 'unicodeescape' codec can't decode bytes in position 0-1: truncated \uXXXX escape
    

def connectToProxy(address: tuple, options: dict = {}):
    sock = socket.socket()
    des = proxy['url']
    sock.connect(des)
    print("connected", des)

    # 1. init stage
    sock.send(b'\x00\x00\x05\x00')
    result = sock.recv(10)
    print("init stage received", result)

    # 1. addr stage
    data = obj2bytes(address)
    # data = data + b'\n'
    sock.send(data)
    result = sock.recv(1024)
    # why result = sock.recv(1024) will throw error ?
    print("addr stage received", result)
    return sock

import socket
import threading

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

sAddr = ('127.0.0.1', 8100)

s.bind(sAddr)

s.listen(1024)

print("listen at", sAddr)



class Th(threading.Thread):
    def __init__(self, rSock, type):
        threading.Thread.__init__(self)
        self.rSock = rSock
        self.type=type
        assert type=="forward" or type=="backward" or type=="cs" or type=="coroutine"

    def run_backward(self):
        rSock = self.rSock
        while True:
            try:
                result = rSock.recv(64*1024)
                print("received", result)
                if(not result):
                    break
            except:
                print("closed")
                break

    def run(self):
        if(self.type=='backward'):
            self.run_backward()


def DoubleServer():
    rSock = connectToProxy(('www.baidu.com', 443))
    # rSock = connectToProxy(('www.baidu.com', 443)) # 使用baidu.com会302，重定向(location) www.baidu.com
    # 所以猜测baidu.com 和 www.baidu.com不是一个地址
    
    # 需不需要wrap一个TLS是根据库的特性来定的，如果库可以根据https来分析出需要安全接近，那么就不需要自己传入ssl=true参数.
    rSock = ssl.wrap_socket(rSock, keyfile=None, certfile=None, server_side=False, cert_reqs=ssl.CERT_NONE, ssl_version=ssl.PROTOCOL_SSLv23)
    # rSock = connectToProxy(('localhost', 8001))
    # rSock = connectToProxy(('message.painterner.site', 80))

    data = b"GET / HTTP/1.1\r\nHost: www.baidu.com\r\nConnection: close\r\n\r\n"
    # data = b"GET / HTTP/1.1\r\nHost: www.baidu.com\r\nAccept: */*\r\n\r\n"
    # 测试似乎如果不指定Connection: close，说明是keep-alive, 所以server socket不会发出close socket命令
    rSock.send(data)

    th2 = Th(rSock, 'backward')
    th2.start()


DoubleServer()

