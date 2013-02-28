import urllib
from cStringIO import StringIO
from binascii import hexlify, unhexlify
import Connecter

DEBUG = False


protocol_name = 'BitTorrent protocol'
option_pattern = chr(0) * 8


def toint(s):
    return long(hexlify(s), 16)


def tobinary(i):
    return unhexlify('{:08x}'.format(i & 0xFFFFFFFF))


def make_readable(s):
    if not s:
        return ''
    if urllib.quote(s).find('%') >= 0:
        return hexlify(s).upper()
    return '"' + s + '"'

# header, reserved, download id, my id, [length, message]

streamno = 0


class StreamCheck:
    def __init__(self):
        global streamno
        self.no = streamno
        streamno += 1
        self.buffer = StringIO()
        self.next_len, self.next_func = 1, self.read_header_len

    def read_header_len(self, s):
        if ord(s) != len(protocol_name):
            print self.no, 'BAD HEADER LENGTH'
        return len(protocol_name), self.read_header

    def read_header(self, s):
        if s != protocol_name:
            print self.no, 'BAD HEADER'
        return 8, self.read_reserved

    def read_reserved(self, s):
        return 20, self.read_download_id

    def read_download_id(self, s):
        if DEBUG:
            print self.no, 'download ID ' + hexlify(s)
        return 20, self.read_peer_id

    def read_peer_id(self, s):
        if DEBUG:
            print self.no, 'peer ID' + make_readable(s)
        return 4, self.read_len

    def read_len(self, s):
        l = toint(s)
        if l > 2 ** 23:
            print self.no, 'BAD LENGTH: ' + str(l) + ' (' + s + ')'
        return l, self.read_message

    def read_message(self, s):
        if not s:
            return 4, self.read_len
        m = s[0]
        if ord(m) > 8:
            print self.no, 'BAD MESSAGE: ' + str(ord(m))
        if m == Connecter.REQUEST:
            if len(s) != 13:
                print self.no, 'BAD REQUEST SIZE: ' + str(len(s))
                return 4, self.read_len
            index = toint(s[1:5])
            begin = toint(s[5:9])
            length = toint(s[9:])
            print self.no, 'Request: {0}: {1}-{1}+{2}'.format(index, begin,
                                                              length)
        elif m == Connecter.CANCEL:
            if len(s) != 13:
                print self.no, 'BAD CANCEL SIZE: ' + str(len(s))
                return 4, self.read_len
            index = toint(s[1:5])
            begin = toint(s[5:9])
            length = toint(s[9:])
            print self.no, 'Cancel: {0}: {1}-{1}+{2}'.format(index, begin,
                                                             length)
        elif m == Connecter.PIECE:
            index = toint(s[1:5])
            begin = toint(s[5:9])
            length = len(s) - 9
            print self.no, 'Piece: {0}: {1}-{1}+{2}'.format(index, begin,
                                                            length)
        else:
            print self.no, 'Message {} (length {})'.format(ord(m), len(s))
        return 4, self.read_len

    def write(self, s):
        while True:
            i = self.next_len - self.buffer.tell()
            if i > len(s):
                self.buffer.write(s)
                return
            self.buffer.write(s[:i])
            s = s[i:]
            m = self.buffer.getvalue()
            self.buffer.reset()
            self.buffer.truncate()
            x = self.next_func(m)
            self.next_len, self.next_func = x
