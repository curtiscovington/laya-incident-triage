"""Run the fixture evaluation while rejecting network connections in this process."""
import socket
import sys
import triage


def no_network(*args, **kwargs):
    raise RuntimeError('Network access blocked during offline verification')


if __name__ == '__main__':
    socket.socket.connect = no_network
    socket.socket.connect_ex = no_network
    raise SystemExit(triage.main(['--backend', 'laya', *sys.argv[1:]]))
