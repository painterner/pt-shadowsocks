import socket
import threading

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

sAddr = ('0.0.0.0', 8001)

s.bind(sAddr)

s.listen(1024)

print("listen at", sAddr)


while True:
    connect = s.accept()
    print("accepted", connect[1])
    try:

        data = connect[0].recv(1024*64)
        print("received", data)

        connect[0].send(b'ok')
        connect[0].close()
    except:
        print("closed", connect[1])
        break

