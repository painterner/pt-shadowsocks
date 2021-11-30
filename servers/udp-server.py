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
    sock.bind(('0.0.0.0', 1082))
    sock.setsockopt(socket.SOL_IP, socket.IP_RECVDSTADDR, 1)

    # while True:
    #     try: 

    data, msg, *retu= sock.recvmsg(64*1024)
    print("data other", retu)
    print("data", data, msg)
    for m in msg:
        print("mmm", m)

            # c = AsyncSocket(connect[0], callback, eventloop)
            # break
        # except:
        #     pass

    # c = AsyncSocket(sock, callback, eventloop)

    eventloop.run()
    
main()