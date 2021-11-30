from termcolor import colored
import logging

def clSprintf(s : str, *args):
    nArgs = []
    for a in args:
        nArgs.append(colored("{}".format(a), "yellow"))
    return s.format(*nArgs)

class CustomLog():
    def __init__(self, logImpl : logging.Logger) -> None:
        self.logging = logImpl

    def setLogging(self, logImpl: logging.Logger):
        self.logging = logImpl

    def enterFunc(self,msg):
        self.logging.debug(colored(msg, "blue"))