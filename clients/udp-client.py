import socket
import struct
from ptshadowsocks.eventloop import EventLoop
from ptshadowsocks.libs.asyncSocket import AsyncSocket

def main():
    def callback(sock, fd, event):
        SO_ORIGINAL_DST = 80 # missing definition in python, so I shiped from c++
        s_in = sock.getsockopt(socket.SOL_IP, SO_ORIGINAL_DST, 16)
        (proto, port, a, b, c, d) = struct.unpack('!HHBBBB', s_in[:8])
        o_addr = "%d.%d.%d.%d" % (a, b, c,d)
        print("original destionation was %d.%d.%d.%d:%d" % (a, b, c,d, port))
        print("accepted",sock)

        print("callback", sock, fd, event)
        
    eventloop = EventLoop()
    sock = socket.socket(type=socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 1085))

    connect = sock.sendto(b'ehll', ('127.0.0.1', 1082))
    print("accepted")
    data, addr = sock.recvfrom(64*1024)
    print("received")
    # c = AsyncSocket(connect[0], callback, eventloop)

    # c = AsyncSocket(sock, callback, eventloop)

    eventloop.run()
    
main()