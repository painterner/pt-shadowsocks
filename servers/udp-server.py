import ctypes
import json
import socket
import struct
from ptshadowsocks.eventloop import POLL_ERR, POLL_HUP, EventLoop
from ptshadowsocks.libs.asyncSocket import AsyncSocket
from ctypes import *
import threading


cyUdpServer = CDLL('./udp-server-c/udp-server.so')
# https://blog.csdn.net/qq_35636311/article/details/78255568


# def main():
#     def callback(sock, fd, event):
#         SO_ORIGINAL_DST = 80 # missing definition in python, so I shiped from c++
#         s_in = sock.getsockopt(socket.SOL_IP, SO_ORIGINAL_DST, 16)
#         (proto, port, a, b, c, d) = struct.unpack('!HHBBBB', s_in[:8])
#         o_addr = "%d.%d.%d.%d" % (a, b, c,d)
#         print("original destionation was %d.%d.%d.%d:%d" % (a, b, c,d, port))
#         print("accepted",sock)

#         print("callback", sock, fd, event)
        
#     eventloop = EventLoop()
#     sock = socket.socket(type=socket.SOCK_DGRAM)
#     sock.bind(('0.0.0.0', 1082))
#     # sock.setsockopt(socket.SOL_IP, socket.IP_RECVDSTADDR, 1)
#     # data, msg, *retu= sock.recvmsg(64*1024)
#     # print("data other", retu)
#     # print("data", data, msg)


#     def main_handle(sock, fd, event): 
#         data, addr = sock.recvfrom(64*1024)
#         data = json.loads(data)
#         des_host = data["address"].des_host
#         des_port = data["address"].des_port

#         rsock = socket.socket(type=socket.SOCK_DGRAM)
#         AsyncSocket(sock, )

#     AsyncSocket(sock, main_handle, eventloop)
    
    
    
# main()

eventloop = EventLoop()

cyContext = cyUdpServer.context
print(cyUdpServer.__dict__)

class Th(threading.Thread):
    def __init__(self, func):
        super(Th, self).__init__()
        self.func = func
        self.stop = False
    def run(self):
        while True:
            self.func()
            if(self.stop):
                break
    def join(self):
        self.stop = True


def main_handle():
    cyUdpServer.recv_main.restype = ctypes.c_char_p
    data = cyUdpServer.recv_main()
    data = json.loads(data)
    # data = cyContext.buf
    # data["payload"] = data["payload"][:-1] # 移除最后的\n符号(\n是因为nc -u host port命令是自动发送\n的)? 但是windows是否需要移除\r\n ?
    print("received", data)

    def callback_handle(sock, fd, event):
        if event & (POLL_ERR | POLL_HUP):
            eventloop.remove(sock)
            sock.close()
            return

        data, addr = sock.recvfrom(64*1024)
        print("callback received", data)
        if not data:
            eventloop.remove(sock)
            sock.close()
            return

        sock.bind(addr)  # 模拟iptables的伪装, 如果是tcp的话，应该怎么伪装?
        sock.sendto(data, (data["host"], data["port"]))
        print("sent back done")

    if(data['des_port'] == 1082):
        print("Error: the destination shouldn't be self")
        return

    rsock = socket.socket(type=socket.SOCK_DGRAM)
    AsyncSocket(rsock, callback_handle, eventloop)
    rsock.sendto(data["payload"].encode(), (data["des_host"], data["des_port"]))

th = Th(main_handle)
th.start()

# 多线程编程应该是可以接受的。因为可以设想系统中每一个serice都会占用一个线程，所以只要不是太多是无所谓的。

eventloop.run()