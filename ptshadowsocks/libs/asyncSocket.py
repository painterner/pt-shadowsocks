import socket
from ptshadowsocks.eventloop import EventLoop, POLL_IN

class AsyncSocket():
    def __init__(self, sock, callback, loop=None):
        super().__init__()
        self.callback = callback
        self.sock = sock
        self.loop = loop
        if(loop is None):
            self.loop = EventLoop()
        
        self.loop.add(self.sock, POLL_IN, self)

    def handle_event(self, sock, fd, event):
        self.callback(sock, fd, event)

    def close(self):
        if(self.sock):
            self.loop.remove(self.sock)
            self.sock.close()
            self.sock = None

def test():
    def callback(sock, fd, event):
        print("callback", sock, fd, event)
    eventloop = EventLoop()
    sock = socket.socket(type=socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 2080))
    c = AsyncSocket(sock, callback, eventloop)

    eventloop.run()
    