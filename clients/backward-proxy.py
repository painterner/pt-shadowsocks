import socket
import struct
import json
from typing import Any
import asyncio
import traceback

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
    

def requestDirect(address: tuple, options: dict = {}):
    sock = socket.socket()
    # des = proxy['url']
    des = address
    sock.connect(des)
    print("connected", des)

    data = b'aaa'
    pData = obj2bytes(address) + data
    sock.send(pData)
    print("sent", pData)
    result = sock.recv(1024)
    print("received", result)

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
    def __init__(self, connect, rSock, type):
        threading.Thread.__init__(self)
        self.connect = connect
        self.rSock = rSock
        self.type=type
        assert type=="forward" or type=="backward" or type=="cs" or type=="coroutine"

    def run_forward(self):
        connect = self.connect
        rSock = self.rSock
        print("building conenct", connect[1])
        while True:
            try:
                data = connect[0].recv(64*1024)
                if(not data):
                    connect[0].close()
                    break
                rSock.send(data)
                print("sent", data)
            except:
                print("closed", connect[1])
                connect[0].close()
                break

    def run_backward(self):
        connect = self.connect
        rSock = self.rSock
        print("building conenct", connect[1])
        while True:
            try:
                result = rSock.recv(64*1024)
                print("received", result)
                connect[0].send(result)
            except:
                print("closed", connect[1])
                connect[0].close()
                break

    def run_by_coroutine():
        connect = self.connect
        rSock = self.rSock
        # 用协程失败的原因猜测是协程需要用asyncio.sleep(xx)协调，否则会阻塞其他协程运行。
        async def forward():
            while True:
                try:
                    data = connect[0].recv(64*1024)
                    if(not data):
                        connect[0].close()
                        break
                    rSock.send(data)
                    print("sent", data)
                except:
                    print("closed", connect[1])
                    connect[0].close()
                    break

        async def backward():
            while True:
                try:
                    result = rSock.recv(64*1024)
                    print("received", result)
                    connect[0].send(result)
                except:
                    print("closed", connect[1])
                    connect[0].close()
                    break

        async def gather():
            await asyncio.gather(forward(), backward())

        try:
            asyncio.run(gather())
        except:
            traceback.print_exc()

    def run(self):
        if(self.type=='forward'):
            self.run_forward()
        if(self.type=='backward'):
            self.run_backward()

        # connect = self.connect
        # print("building conenct", connect[1])
        # rSock = connectToProxy(('www.baidu.com', 443))

        # while True:
        #     try:
        #         data = connect[0].recv(64*1024)
        #         if(not data):
        #             connect[0].close()
        #             break
        #         rSock.send(data)
        #         print("sent", data)
        #         result = rSock.recv(64*1024)
        #         print("received", result)
        #         connect[0].send(result)
        #     except:
        #         print("closed", connect[1])
        #         connect[0].close()
        #         break

def DoubleServer():
    rSock = connectToProxy(('www.baidu.com', 443))
    # rSock = connectToProxy(('localhost', 8001))
    # rSock = connectToProxy(('message.painterner.site', 80))
    while True:
        connect = s.accept()
        print("accepted", connect[1])

        th1 = Th(connect, rSock, 'forward')
        th2 = Th(connect, rSock, 'backward')
        th1.start()
        th2.start()

def SingleServer():
    # rSock = connectToProxy(('www.baidu.com', 443))
    # rSock = connectToProxy(('localhost', 8001))
    rSock = connectToProxy(('message.painterner.site', 80))
    while True:
        connect = s.accept()
        print("accepted", connect[1])

        th = Th(connect, rSock, "cs" )
        th.start()


DoubleServer()

