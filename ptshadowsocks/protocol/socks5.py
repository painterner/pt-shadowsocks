import json
import logging as gLogging
from ptshadowsocks.eventloop import EventLoop, POLL_IN, POLL_OUT, POLL_HUP, POLL_ERR, POLL_NVAL
from ptshadowsocks.dnsresolver import dnsresolver
import socket
from ptshadowsocks.crypto import Encryptor
import time
import errno
import logging
import traceback
import struct
from termcolor import colored

import ptshadowsocks.eventloop as eventloop
import ptshadowsocks.globalvar as globalvar

STAGE_INIT = 0
STAGE_ADDR = 1
STAGE_CONNECT = 2
STAGE_STREAM = 3
STAGE_DESTORY = 4

LENGTH_LENGTH = 2

SOCK_EMPTY_DATA_TRY = {}

def socks5_handle(self, sock, fd, event):
    if self.is_client:
        if event & POLL_ERR:
            self.logging.error(colored("POLL_ERROR", "red"))
            self.close()
            return
        if(event &  POLL_HUP):
            self.logging.error("POLL_HUP")
            return
            
        if(event &  POLL_IN):
            self.logging.debug(colored("has POLL_IN FLAG", "yellow"))
        # if(event &  POLL_OUT):
        #     self.logging.debug(colored("has POLL_OUT FLAG", "yellow"))
        # if(event &  POLL_ERR):
        #     self.logging.debug(colored("has POLL_ERR FLAG", "yellow"))
        # if(event &  POLL_HUP):
        #     self.logging.debug(colored("has POLL_HUP FLAG", "yellow"))
        # if(event &  POLL_NVAL):
        #     self.logging.debug(colored("has POLL_NVAL FLAG", "yellow"))

        if self.is_local and self.stage == STAGE_INIT:
            data = sock.recv(10)
            # received: b'\x05\x02\x00\x01'
            self.logging.debug(colored("init stage {}".format(data), 'blue'))
            self.stage = STAGE_ADDR
            sock.send(b'\x05\x00')
            return
        if self.is_local and self.stage == STAGE_ADDR:
            self.logging.debug(colored("addr stage", 'blue'))
            self.data_to_send = b''
            # received: b"\x05\x01\x00\x01'\x9cB\x0e\x00P"
            data = sock.recv(100)
            self.logging.debug(colored("received: {}".format(data), 'blue'))
            ## when use format of string
            tmp = json.loads(data.decode())
            addr = tmp[0];
            self.dest['port'] = tmp[1]

            ## when use format of binary
            # port = data[-2:]
            # addr = data[4:-2]
            # self.dest['port'] = struct.unpack('>H', port)[0]
            # addrTuple = [str(s) for s in struct.unpack('BBBB', addr)]
            # addr = '.'.join(addrTuple)

            self.logging.debug(colored("socks5 data addr {} port {}".format(addr, self.dest['port']), 'blue'))
            
            dnsresolver.resolve(addr, self.dnsresolver_callback) 
            return       
        if self.is_local and self.stage == STAGE_CONNECT:
            self.logging.error(colored('connecting, but get unexpected data, ignore ?', "red"))
            return
        if self.is_local and self.stage == STAGE_STREAM:
            self.logging.debug(colored("stream stage", 'blue'))
            data = sock.recv(1024*64)
            if(SOCK_EMPTY_DATA_TRY.get(sock) is None):
                SOCK_EMPTY_DATA_TRY[sock] = 0
            if not data:
                # todo, if not data, try 3 times, if still empty, close connection
                SOCK_EMPTY_DATA_TRY[sock] += 1
                if(SOCK_EMPTY_DATA_TRY[sock] > 0):
                    SOCK_EMPTY_DATA_TRY[sock] = 0
                    self.close()
                return 

            self.data_to_send += data
            self.update_stream()
            return

        if self.is_remote:
            data = sock.recv(1024*64)
            self.logging.debug(colored("step backward 1, data: {}".format(data), 'blue'))
            self.data_to_back += data
            self.decryptoSendBack() # send to client user

    else: 
        if self.is_local and self.stage == STAGE_INIT:
            self.logging.debug(colored("init stage, event: {}".format(event), 'blue'))
            if event & POLL_ERR:
                self.logging.error(colored("POLL_ERROR", "red"))
                return

            # print('event', event)
            # while True:
            #     print(sock.recv(10))
            # self.stage = STAGE_ADDR
            self.stage = STAGE_STREAM
            # self.stage = STAGE_INIT
            # dnsresolver.resolve(sock, self.dnsresolver_callback)

            self.data_to_send = b''
            return 
        if self.is_local and self.stage == STAGE_STREAM:
            self.logging.debug(colored("stream stage, event: {}".format(event), 'blue'))
            # self.data_to_send += data
            # self.update_stream()
            self.stage = STAGE_STREAM

            if event & POLL_ERR:
                # logging.error(colored("POLL_ERROR", "red"))
                self.logging.error("POLL_ERROR")
                return

            if(event & (POLL_IN | POLL_HUP)):
                data = sock.recv(1024*64)
                print("received:", data)
                if not data:
                    # 如果single pipe, 只有可能是client 断开连接了? 所以需要关闭 ?
                    self.close()
                    return

                self.data_to_send += data
                self.update_stream()
                # todo, if POLL_HUP, it represent client is closed ?
                return

            return

        if self.is_remote:
            if event & POLL_ERR:
                # logging.error(colored("POLL_ERROR", "red"))
                self.logging.error("POLL_ERROR")
                return

            if(event & (POLL_HUP)):
                    # The reason for this event:
                # 1. create this socket, but not connected to server
                return

            if(event & (POLL_IN)):
                data = sock.recv(1024*64)
                if not data:
                    self.close()
                    return 
                self.logging.debug(colored("received from destination: {}".format(data), "green"))
                self.update_back_stream(data)
                return



            # logging.debug(colored("me: server, send to client, data: {}".format(self.data), 'blue'))
            # data = crypto.encrypt(data)
            # self.local_relay.sock.send(data) # to do, 能否把sock.send用local_relay.send代理 ?
            return