import socket

s = socket.socket()

sAddr = ('127.0.0.1', 8001)

s.bind(sAddr)

s.listen(1024)

print("listen at", sAddr)

while True:
    connect = s.accept()
    print("accepted", connect[1])

    while True:
        try:

            data = connect[0].recv(1024)

            connect[0].send(b'ok')
        except:
            print("closed", connect[1])
            break


