global crypto
crypto = None

global relay_sock
global status_sock
relay_sock= None
status_sock = None

password="admin123"

env={}
def get_env():
    return env

def set_g_crypto(v):
    global crypto
    crypto = v

# def get_g_crypto(v):
#     global crypto
#     return crypto

def set_g_relay_sock(v):
    global relay_sock
    relay_sock = v

def set_g_status_sock(v):
    global status_sock
    status_sock = v

# def get_g_relay_sock():
#     return relay_sock