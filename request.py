import socket
import struct
import json
from typing import Any

proxy = {
    "url": ('127.0.0.1', 1081)
}

def str2bytes(string: str):
    return bytes(string, "utf8")

def obj2bytes(obj : Any):
    s = json.dumps(obj)
    return str2bytes(s)

# bytes("\uxxx", "unicode")
# SyntaxError: (unicode error) 'unicodeescape' codec can't decode bytes in position 0-1: truncated \uXXXX escape
    

def requestDirect(address: tuple, options: dict = {}):
    sock = socket.socket()
    # des = proxy['url']
    des = address
    sock.connect(des)
    print("connected", des)

    data = b'aaa'
    pData = obj2bytes(address) + data
    sock.send(pData)
    print("sent", pData)
    result = sock.recv(1024)
    print("received", result)

def request(address: tuple, options: dict = {}):
    sock = socket.socket()
    des = proxy['url']
    sock.connect(des)
    print("connected", des)

    # 1. init stage
    sock.send(b'\x00\x00\x05\x00')
    result = sock.recv(10)
    print("init stage received", result)

    # 1. addr stage
    data = obj2bytes(address)
    # data = data + b'\n'
    sock.send(data)
    result = sock.recv(1024)
    # why result = sock.recv(10) will throw error (SOCK_EMPTY_DATA_TRY[sock] > e)?
    print("addr stage received", result)

    data = b'aaa'
    pData = data
    sock.send(pData)
    print("sent", pData)
    result = sock.recv(1024)
    print("received", result)

# requestDirect(('127.0.0.1', 8001))
request(('127.0.0.1', 8001))