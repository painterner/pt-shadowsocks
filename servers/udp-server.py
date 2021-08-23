import socket
from ptshadowsocks.eventloop import EventLoop
from ptshadowsocks.libs.asyncSocket import AsyncSocket

def main():
    def callback(sock, fd, event):
        print("callback", sock, fd, event)
        
    eventloop = EventLoop()
    sock = socket.socket(type=socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 1082))
    c = AsyncSocket(sock, callback, eventloop)

    eventloop.run()
    