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

import threading



class Th(threading.Thread):
    def __init__(self, rSock,cSock, type):
        threading.Thread.__init__(self)
        self.rSock = rSock
        self.cSock = cSock
        self.type=type
        assert type=="forward" or type=="backward" or type=="cs" or type=="coroutine"

    def run_backward(self):
        rSock = self.rSock
        while True:
            try:
                result = rSock.recv(64*1024)
                print("received length", len(result))
                if(not result):
                    break
                self.cSock.send(result)
            except:
                print("closed")
                break

    def run(self):
        if(self.type=='backward'):
            self.run_backward()


def DoubleServer(cSock, host,port):
    rSock = connectToProxy((host, port))

    th2 = Th(rSock, cSock, 'backward')
    th2.start()
    return rSock


# DoubleServer('www.baidu.com', 443, b"GET / HTTP/1.1\r\nHost: www.baidu.com\r\nConnection: close\r\n\r\n")


import socket
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sAddr = ('0.0.0.0', 1082)
s.bind(sAddr)
s.listen(1024)
print("listen at", sAddr)
while True:
    connect = s.accept()
    SO_ORIGINAL_DST = 80 # missing definition in python, so I shiped from c++
    s_in = connect[0].getsockopt(socket.SOL_IP, SO_ORIGINAL_DST, 16)
    (proto, port, a, b, c, d) = struct.unpack('!HHBBBB', s_in[:8])
    o_addr = "%d.%d.%d.%d" % (a, b, c,d)
    print("original destionation was %d.%d.%d.%d:%d" % (a, b, c,d, port))
    print("accepted",connect[0], connect[1])

    rSock = DoubleServer(connect[0], o_addr, port)
    try:
        data = connect[0].recv(1024)
        rSock.send(data)

        # connect[0].send(b'ok')
    except:
        print("closed", connect[1])
        break
