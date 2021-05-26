import json
import logging as gLogging
from ptshadowsocks.eventloop import EventLoop, POLL_IN, POLL_OUT, POLL_HUP, POLL_ERR
from ptshadowsocks.dnsresolver import dnsresolver
import socket
from ptshadowsocks.crypto import Encryptor
import time
import errno
import logging
import traceback
import struct
from termcolor import colored
import copy

import ptshadowsocks.eventloop as eventloop
import ptshadowsocks.globalvar as globalvar
from ptshadowsocks.globalvar import get_env
from ptshadowsocks.protocol.socks5 import socks5_handle

#  todo: 如何建立一个层级logging, 比如一个父logging控制所有子logging, 子logging可以有自己的级别， 
#  但是父logging可以控制总体级别的开关。
#  best practice: 每个模块使用不同的logging, logging.get(__name__)

# todo: 转化logging为get 函数，这样就可以获得env了，否则由于先倒入这个module，env并未设置
gLogging.getLogger(__name__).setLevel(level=gLogging.DEBUG)
# gLogging.getLogger().setLevel(level=gLogging.DEBUG)
logging = gLogging.getLogger(__name__)

# errno.EAGAIN, errno.EINPROGRESS, errno.EWOULDBLOCK

STAGE_INIT = 0
STAGE_ADDR = 1
STAGE_CONNECT = 2
STAGE_STREAM = 3
STAGE_DESTORY = 4

#  the size of encrytoed packet size
LENGTH_LENGTH = 4
META_LENGTH_LENGTH = 2

# class Context():
#     def __init__(self):
#         self.env = None
#         self.sock = None
#         self.is_client = None
#         self.is_local = None
#         self.eventloop = None
#         self.loop = None # alias of eventloop

class FD_HANDLER():
    def __init__(self) -> None:
        self._fd_to_handlers = {}
        self._handlers_to_fd = {}

        self.handler = self._fd_to_handlers
        self.fd = self._handlers_to_fd

source_dest_map = {}
global inited_relay_remote
inited_relay_remote = False

def unpack_length(data):
    length = struct.unpack("<I", data[0:LENGTH_LENGTH])[0]
    lengthDest = struct.unpack("<H", data[LENGTH_LENGTH:LENGTH_LENGTH+META_LENGTH_LENGTH])[0]
    return length, lengthDest
    
def pack_length(length, lengthDest):
    lengthBinary = struct.pack("<I", length + LENGTH_LENGTH + META_LENGTH_LENGTH) # total length
    lengthBinaryDest = struct.pack("<H", lengthDest) # destination(ex. b'www.google.com') length
    return lengthBinary, lengthBinaryDest

# 理论： 类初始化不要传入过多的初始值， 那么关于类的位置移动到其他项目的问题如何解决？： 可以把这个类和全局变量池一块移动，
# 实践起来说不定会更方便?
class TCPRelayHandler ():
    def __init__(self, sock, is_client, is_local, fd_handler, local_relay=None , context=None, eventloop=None, address=None):
        """
        client: local machine
        server: vps

        local: local socket
        remote: remote socket
        """
        self.sock = sock
        self.address = address
        self.stage = STAGE_INIT
        self.is_client = is_client
        self.is_server = not is_client
        self.is_local = is_local
        self.is_remote = not is_local
        self.data_to_send = ''
        self.last_activity = 0
        self.env = context['env'] if context != None else {"timeout": 300}
        self.is_relay = False
        self.fd_handler = fd_handler
        self.eventloop : EventLoop = eventloop
        self.dest = {}
        self.meta = {}
        self.singlePipe = True
        self.data_to_back = b''
        self.remote_relay = None
        self.local_relay = None
        self.closed = False
        self.use_protocol_socks5 = True
        # self.crypto = Encryptor(globalvar.password, 'aes-256-cfb')
        self.crypto = globalvar.crypto

        
        self.logging_name = "hand_local" if self.is_local else "hand_remote"
        gLogging.getLogger(__name__).setLevel(level=gLogging.DEBUG)
        # if(get_env()['VERBOSE_LEVEL']):
        #     gLogging.getLogger(__name__).setLevel(level=gLogging.DEBUG)
        # else:
        #     gLogging.getLogger(__name__).setLevel(level=gLogging.INFO)
    
        print('creating a new tcprelayhandler',is_client, is_local, fd_handler)
        fd_handler.handler[sock] = self

        print("is_local", self.is_local)
        if(self.is_local):
            self.sock.setblocking(False)
            self.sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
            # self.eventloop.add(self.sock, POLL_IN | POLL_ERR, self)

            ## todo: change to add after dnsresolved
            if self.is_client:
                source = '{}:{}'.format(self.address[0], self.address[1])
                self.logging.debug(colored("add surce {}".format(source), "blue"))
                source_dest_map[source] = self

                self.remote_sock = globalvar.relay_sock
                global inited_relay_remote
                if( not inited_relay_remote):
                    self.remote_relay = TCPRelayHandler(self.remote_sock, self.is_client, False, self.fd_handler, local_relay=self, eventloop=self.eventloop)
                    inited_relay_remote = True
            else:
                self.remote_sock = socket.socket()
                # self.remote_sock.setblocking(False)
                # self.remote_sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)

            if not self.singlePipe:
                print("remote_sock", self.remote_sock)
                self.remote_relay = TCPRelayHandler(self.remote_sock, self.is_client, False, self.fd_handler, local_relay=self, eventloop=self.eventloop)
                self.eventloop = eventloop
                #  todo: 采用shadowsocks的方式，self.server, 以减少出错率。

            # self.eventloop.add(self.remote_sock, POLL_IN | POLL_ERR, self.remote_relay)
        else:
            assert local_relay is not None
            self.local_relay = local_relay

        self.eventloop.add(self.sock, POLL_IN | POLL_ERR | POLL_HUP, self)
            
        
    @property
    def logging(self):
        l = gLogging.getLogger(self.logging_name)
        if(get_env()['VERBOSE_LEVEL']):
            l.setLevel(level=gLogging.DEBUG)
        else:
            l.setLevel(level=gLogging.INFO)
        return l

    @logging.setter
    def logging(self,v):
        pass

    def dnsresolver_callback(self, *args):
        self.stage = STAGE_CONNECT
        self.logging.debug(colored("dns resolved args: {}".format(args), "yellow"))
        # Example:DEBUG:hand_local:dns resolved args: ((b'www.baidu.com', '180.101.49.12'), None)
        
        # result = args[0][0]
        result = args[0][-1]
        if(isinstance(result, str)):
            result = result.encode("utf-8")
        self.dest['addr'] = result.decode("utf-8")
        self.logging.debug(colored("dns resolved result: {}".format(result), "yellow"))
        try:
            
            port = self.dest['port']

            self.logging.debug(self.remote_sock)
            if(not self.is_client):
                self.remote_sock.connect((result, port))
            self.stage = STAGE_STREAM

            
            if self.use_protocol_socks5:
                bindServerAddr = (0,0,0,0)
                bindServerPort = 0
                bindServerAddr = struct.pack('BBBB', *bindServerAddr)
                bindServerPort = struct.pack('H', bindServerPort)
                self.sock.send(b'\x05\x00\x00\0x01'+bindServerAddr+bindServerPort)
            else:
                self.sock.send(b'random')
        except Exception as e:
            self.logging.info('connect to remote error: {}'.format(e))
            self.close()

    def encrypto(self):
        # self.logging.debug(colored('start encrypto', "blue"))
        meta = {
            "addr": self.dest['addr'],
            "port": self.dest['port'],
            "srcAddr": self.address[0],
            "srcPort": self.address[1]
        }
        metaJsonBytes = bytes(json.dumps(meta), "utf-8")
        self.meta["bytes"] = metaJsonBytes
        self.data_to_send = metaJsonBytes + self.data_to_send
        self.logging.debug("self.data_to_send", self.data_to_send)
        self.data_to_send = self.crypto.encrypt(self.data_to_send)
        self.logging.debug('encrtyto done, result:')

    def encryptoBack(self, data):
        metaJsonBytes=self.meta["bytes"]
        data = metaJsonBytes + data
        data = self.crypto.encrypt(data)
        # self.logging.debug(colored("entrypto for send back: {}".format(data), "blue"))
        return data

    def decryptoSendBack(self):
        length,lengthDest = unpack_length(self.data_to_back)
        self.logging.debug(colored(" length: content {}, meta {}".format(length, lengthDest), 'green'))
        if(len(self.data_to_back) < length):
            return
        data = self.data_to_back[LENGTH_LENGTH+META_LENGTH_LENGTH:length]
        self.logging.debug(colored('start decrypt', 'green'))
        data = self.crypto.decrypt(data)
        self.logging.debug(colored('end decrypt, result: {}'.format(data), 'green'))

        if data and self.is_client:
            metaBytes = data[0:lengthDest]
            content = data[lengthDest:]
            # self.logging.debug(colored("content:{}".format(content), "green"))
            self.meta["obj"] = json.loads(metaBytes)
            addr = self.meta["obj"]["addr"]
            port = self.meta["obj"]["port"]
            srcAddr = self.meta["obj"]["srcAddr"]
            srcPort = self.meta["obj"]["srcPort"]
            source = "{}:{}".format(srcAddr, srcPort)
            target = "{}:{}".format(addr, port)
            self.logging.debug(colored('send back, source: {}'.format(source), 'green'))

            handler = source_dest_map[source]
            handler.sock.send(content)

            if(len(self.data_to_send) == length):
                self.data_to_back = b''
            else:
                self.data_to_back = self.data_to_back[length:]

    def decryptoSend(self):
        length,lengthDest = unpack_length(self.data_to_send)
        self.logging.debug(colored(" length: content {}, meta {}".format(length, lengthDest), 'green'))
        if(len(self.data_to_send) < length):
            return
        data = self.data_to_send[LENGTH_LENGTH+META_LENGTH_LENGTH:length]
        self.logging.debug('start decrypt', data)
        data = self.crypto.decrypt(data)
        self.logging.debug('end decrypt')

        if data and not self.is_client:
            metaBytes = data[0:lengthDest]
            content = data[lengthDest:]
            self.logging.debug(colored("content:{}".format(content), "green"))
            self.meta["obj"] = json.loads(metaBytes)
            self.meta["bytes"] = metaBytes
            addr = self.meta["obj"]["addr"]
            port = self.meta["obj"]["port"]
            srcAddr = self.meta["obj"]["srcAddr"]
            srcPort = self.meta["obj"]["srcPort"]
            source = "{}:{}".format(srcAddr, srcPort)
            target = "{}:{}".format(addr, port)

            # 时间上并没有用到?
            key = source+'<-->'+target
            tmp_handler = source_dest_map.get(key)             
            if(tmp_handler):
                self.remote_sock = tmp_handler.sock
            else:
                # ... 如果所有数据到server的同一个端口，需要分别建立socket和Handler
                
                if self.singlePipe:
                    self.remote_sock = socket.socket() 
                    handler = TCPRelayHandler(self.remote_sock, self.is_client, False, self.fd_handler, local_relay=self, eventloop=self.eventloop)
                    source_dest_map[key] = handler
                    handler.meta = copy.deepcopy(self.meta)
                    
                # ...

                self.logging.debug(colored("starting connect to created server sock {}:{}".format(addr, port), "yellow"))
                self.remote_sock.connect((addr, port))
                self.logging.debug(colored("connected", "yellow"))

            self.logging.debug(colored("starting send to created server sock {}:{}".format(addr, port), "yellow"))
            self.remote_sock.send(content)
            self.logging.debug(colored("send done", "yellow"))

            if(len(self.data_to_send) == length):
                self.data_to_send = b''
            else:
                self.data_to_send = self.data_to_send[length:]

    def update_stream(self):
        if self.is_client:
            if self.is_local:
                self.encrypto()
                length = len(self.data_to_send)
                lengthDest = len(self.meta["bytes"])
                lengthBinary, lengthBinaryDest = pack_length(length, lengthDest)
                self.data_to_send = lengthBinary + lengthBinaryDest + self.data_to_send
                self.remote_sock.send(self.data_to_send)
                self.data_to_send = b''
        else: 
            if self.is_local:
                self.decryptoSend()
    def update_back_stream(self, data):
        if self.is_client:
            pass
        else:
            if self.is_local:
                pass
            else:
                data = self.encryptoBack(data)
                length = len(data)
                # 想象一下，如果不是singlePipe, 我们是不要要meta数据的(也就不需要source_dest_map)
                lengthDest = len(self.meta["bytes"])
                self.logging.debug("data length %d" % length)
                lengthBinary, lengthBinaryDest = pack_length(length, lengthDest)
                data = lengthBinary + lengthBinaryDest + data
                self.local_relay.sock.send(data)

    def handle_event(self, sock: socket.socket, fd, event):
        self.last_activity = time.time()

        self.logging.debug("sock status: event {}, stage {}, {}, {}, {}".format(event, self.stage, sock==self.sock, self.is_local, self.is_remote))

        if self.is_relay: 
            raise Exception('Unimplemented') 

        if self.use_protocol_socks5:
            socks5_handle(self, sock, fd, event)
            return           

        if self.is_client:

            if event & POLL_ERR:
                self.logging.error(colored("POLL_ERROR", "red"))
                self.close()
                return

            if(event &  POLL_HUP):
                self.logging.error("POLL_HUP")
                return

            if self.is_local and self.stage == STAGE_INIT:
                data = sock.recv(10)
                # received: b'\x05\x02\x00\x01'
                self.logging.debug(colored("init stage {}".format(data), 'blue'))
                self.stage = STAGE_ADDR
                # sock.send(b'\x00\x00\x05\x01')
                sock.send(b'\x05\x00')
                
                return
            if self.is_local and self.stage == STAGE_ADDR:
                self.logging.debug(colored("addr stage", 'blue'))
                self.data_to_send = b''
                data = sock.recv(100)
                self.logging.debug(colored("received: {}".format(data), 'blue'))
                addr  = json.loads(data.decode('utf-8'))
                self.dest['port'] = addr[1]
                self.logging.debug(colored("will resolve host {} ( port: {})".format(addr[0],addr[1]), 'blue'))
                
                dnsresolver.resolve(addr[0], self.dnsresolver_callback) 
                return       
            if self.is_local and self.stage == STAGE_CONNECT:
                print('connectiong, but get unexpected data, ignore ?')
                return
            if self.is_local and self.stage == STAGE_STREAM:
                self.logging.debug(colored("stream stage", 'blue'))
                data = sock.recv(1024*64)
                if not data:
                    # todo, if not data, close connection ?
                    self.logging.error("local recieved empty data, to close it")
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
                        self.logging.error("local recieved empty data, to close it")
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

                if(event & (POLL_IN)):
                    data = sock.recv(1024*64)
                    if not data:
                        self.logging.error("remote recieved empty data, to close it")
                        self.close()
                        return 
                    self.logging.debug(colored("received from destination: {}".format(data), "green"))
                    self.update_back_stream(data)
                    return

                if(event & (POLL_HUP)):
                    # The reason for this event:
                    # 1. create this socket, but not connected to server
                    return

                # logging.debug(colored("me: server, send to client, data: {}".format(self.data), 'blue'))
                # data = crypto.encrypt(data)
                # self.local_relay.sock.send(data) # to do, 能否把sock.send用local_relay.send代理 ?
                return

    def handle_periodic(self):
        now = time.time()
        if now - self.last_activity > env['timeout']:
            self.logging.info("handle periodic: to close sock")
            self.close()

            if self.is_remote:
                pair_relay = self.local_relay
                del self.local_relay
            else:
                pair_relay = self.remote_relay
                del self.remote_relay

            del self
            del self.handle_to_handle[self]
            del self.handle_to_handle[self.local_relay]

    def close(self):
        traceback.print_stack()

        self.eventloop.remove(self.sock)
        self.sock.close()
        self.closed = True
        # self.fd_handler.remove(self.sock)
        if self.remote_relay and not self.remote_relay.closed:
            if self.is_server:
                self.logging.error("close: close remote_relay")
                self.remote_relay.close()

        if self.is_server:
            if self.is_local:
                for key in source_dest_map:
                    self.logging.error("close: close source_dest_map")
                    handler = source_dest_map[key]
                    handler.close()

        if not self.is_remote:
            if self.local_relay and not self.local_relay.closed:
                self.logging.error("close: close local_relay")
                self.local_relay.close()

        self.logging.info(colored("closed handler {}".format(self), "red"))
        del self

class TCPRelay():
    def __init__(self, listen_socket, eventloop, env):
        self.eventloop = eventloop
        self.env = env
        self.is_client = self.env['local']
        logging.info("is client {}".format(self.is_client))
        self.listen_socket = listen_socket
        self.eventloop.add(self.listen_socket, POLL_IN, self)
        self.handle_to_handle = {}
        self.fd_handler = FD_HANDLER()

    # # @get()
    # def context(self):
    #     result = {
    #         "a": self.listen_socket
    #     }
    #     return result
    
    # # @set()
    # def context(self, v):
    #     return

    def handle_event(self, sock, fd, event):
        # handle events and dispatch to handlers
        if sock:
            logging.log(self.env['VERBOSE_LEVEL'], 'fd %d %s', fd,
                        eventloop.EVENT_NAMES.get(event, event))
        if sock == self.listen_socket:
            if event & eventloop.POLL_ERR:
                # TODO
                raise Exception('server_socket error')
            try:
                logging.debug('accepting')
                conn = self.listen_socket.accept()
                logging.info('acceptted {}, {}'.format(conn[1], conn[0]))
                TCPRelayHandler(conn[0], self.is_client, True, self.fd_handler,
                                eventloop=self.eventloop,
                                address=conn[1]
                                )
            except (OSError, IOError) as e:
                error_no = self.eventloop.errno_from_exception(e)
                if error_no in (errno.EAGAIN, errno.EINPROGRESS,
                                errno.EWOULDBLOCK):
                    return
                else:
                    logging.error(e)
                    traceback.print_exc()
                    if self._config['verbose']:
                        traceback.print_exc()
        else:
            pass
            # if sock:
            #     handler = self.fd_handler.handler(fd, None)
            #     if handler:
            #         handler.handle_event(sock, event)
            # else:
            #     logging.warn('poll removed fd')

    def destory(self):
        for handle in self.handle_to_handle:
            self.handle_to_handle[handle].close()
            del self.handle_to_handle[handle]
        self.listen_socket.close()

## todo: 
## 1. TCPRelayHandler作为一个单独的socket类 假设一下我clone了2048个这个类，占用多少内存呢？ 一个假设1k，则总共是2m，完全可以接受， 但是如果是1m，则总共就是2G，可能
## 需要先测试一下。但是实际中影响内存的更可能是内部的缓存网络数据