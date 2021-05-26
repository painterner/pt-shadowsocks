import socket
import threading

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

sAddr = ('127.0.0.1', 8001)

s.bind(sAddr)

s.listen(1024)

print("listen at", sAddr)

class Th(threading.Thread):
    def __init__(self, connect):
        threading.Thread.__init__(self)
        self.connect = connect
    
    def run(self):
        connect = self.connect
        while True:
            try:

                data = connect[0].recv(1024*64)
                print("received", data)

                connect[0].send(b'ok')
            except:
                print("closed", connect[1])
                break


while True:
    connect = s.accept()
    print("accepted", connect[1])

    th = Th(connect)
    th.start()

