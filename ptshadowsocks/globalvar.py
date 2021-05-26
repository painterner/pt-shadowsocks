global crypto
crypto = None

global relay_sock
relay_sock= None

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

# def get_g_relay_sock():
#     return relay_sock