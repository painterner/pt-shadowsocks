import socket
import struct
import json
from typing import Any
import asyncio
import traceback
import ssl
import time
from ptshadowsocks.libs.asyncSocket import AsyncSocket
from ptshadowsocks.eventloop import EventLoop, POLL_IN, POLL_ERR

loop = EventLoop()

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



class Th():
    def __init__(self, rSock, cSock):
        self.rSock = rSock
        self.cSock = cSock
    def run_backward(self, sock, fd, event):
        rSock = self.rSock
        try:
            result = rSock.recv(64*1024)
            print("received length", len(result))
            if(not result):
                print("received length is 0, so close it")
                rSock.close()
                self.cSock.close()
                return
            self.cSock.send(result)
            print("sent", self.cSock)
            # self.cSock.close()  # todo: 根据event来检测然后自动关闭?
        except:
            print("exception run_backward")
            # self.cSock.close()
            # self.rSock.close()
        finally:
            return


def RemoteServer(cSock, host,port):
    rSock = connectToProxy((host, port))

    th2 = Th(rSock, cSock)
    AsyncSocket(rSock, th2.run_backward, loop)
    return rSock

class Server():
    def __init__(self, sock: socket.socket):
        super().__init__()
        self.sock = sock
        loop.add(self.sock, POLL_IN, self)

    def handle_event(self, sock, fd, event):
        if event & POLL_ERR:
            raise Exception('server_socket error')
        try:
            connect = self.sock.accept()
            SO_ORIGINAL_DST = 80 # missing definition in python, so I shiped from c++
            s_in = connect[0].getsockopt(socket.SOL_IP, SO_ORIGINAL_DST, 16)
            (proto, port, a, b, c, d) = struct.unpack('!HHBBBB', s_in[:8])
            o_addr = "%d.%d.%d.%d" % (a, b, c,d)
            print("original destionation was %d.%d.%d.%d:%d" % (a, b, c,d, port))
            print("accepted",connect[0], connect[1])

            rSock = RemoteServer(connect[0], o_addr, port)

            # rSock = connectToProxy((o_addr, port))
            try:
                data = connect[0].recv(1024)
                print("data", data)
                rSock.send(data)

                # result = rSock.recv(64*1024)

                # connect[0].send(result)
                print("done")
            except:
                print("closed", connect[1])

        except (OSError, IOError) as e:
            print("error", e)



s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sAddr = ('0.0.0.0', 1082)
s.bind(sAddr)
s.listen(1024)
print("listen at", sAddr)

Server(s)

loop.run()
