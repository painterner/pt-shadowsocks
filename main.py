#-*-coding:utf-8-*-
import json
from ptshadowsocks.globalvar import set_g_crypto, set_g_relay_sock, password, env

import socket
import sys,os
from  termcolor import colored
import argparse

from ptshadowsocks.tcprelay import TCPRelay
from ptshadowsocks.eventloop import EventLoop, POLL_IN, POLL_OUT
from ptshadowsocks.dnsresolver import dnsresolver
import signal
import logging
from ptshadowsocks.crypto import Encryptor

## best prectice?: logging只需要两个级别就可，一个是info(开发，发布时使用), 一个是debug(开发时使用)
logging.getLogger().setLevel(logging.INFO)

class Initer():
    def __init__(self):
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
        port = env['port']
        # if(env['server']):
        #     port = env['relay_port']
        
        logging.info(colored("listen at {}".format(port), "green"))
        self.sock.bind(('127.0.0.1', port))
        self.sock.setblocking(False)
        self.sock.listen(1024)

        if env['local']:
            relay_sock = socket.socket()
            logging.info(colored('start connecting server {}:{}'.format('127.0.0.1', env['relay_port']), 'yellow'))
            relay_sock.connect(('127.0.0.1', env['relay_port']))
            logging.info(colored('connect server done', 'green'))
            set_g_relay_sock(relay_sock)

        crypto = Encryptor(password, 'aes-256-cfb')
        set_g_crypto(crypto)

        self.eventLoop = EventLoop()
        dnsresolver.add_to_loop(self.eventLoop)
        self.worker = TCPRelay(self.sock, self.eventLoop, env)

        signal.signal(signal.SIGTERM, self.exit_handler)
        signal.signal(signal.SIGQUIT, self.exit_handler)
        signal.signal(signal.SIGINT, self.exit_handler)

    def run(self):
        self.eventLoop.run()

    def exit_handler(self, *args):
        logging.info("received exit command: {}".format(args))
        self.worker.destory()
        sys.exit()
            
def main():
    print(colored(json.dumps(env), 'yellow'))

    init = Initer()
    init.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--local', action='store_true')
    parser.add_argument('--server', action='store_true')
    parser.add_argument('--port', type=int, default=1081)
    parser.add_argument('--relay_port', type=int, default=1092)
    parser.add_argument('--timeout', type=int, default=300)  # seconds
    parser.add_argument('-v', '--VERBOSE', action='store_true')  # verbose
    parser.add_argument('--log', type=int, default=0)  # log level, unimplemented
    args = parser.parse_args()  # type of Namespace()
    for k in vars(args):
        env[k] = getattr(args, k)

    main()
