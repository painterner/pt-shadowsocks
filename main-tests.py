import ptshadowsocks as ptss
from ptshadowsocks.libs import asyncSocket
import argparse

env = {}

def main():
    if(env['name'] == 'asyncSocket'):
        asyncSocket.test()        

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('name', metavar='name') # position argument
    args = parser.parse_args()  # type of Namespace()
    for k in vars(args):
        env[k] = getattr(args, k)

    main()