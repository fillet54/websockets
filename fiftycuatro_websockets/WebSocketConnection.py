import struct
import socket

class WebSocketConnection(object):
    FULL_UTF8_HEADER = struct.pack("!B", 0x80 | 0x01)

    def __init__(self, clientsocket):
        self.s = clientsocket
        self.recv_data = ""
        self.header = None

    def onOpen(self):
        pass

    def onMessage(self, message):
        pass

    def onClose(self):
        pass

    def send(self, msg):
        bytes = self.FULL_UTF8_HEADER
        
        length = len(msg)
        if   length <= 125    : bytes += struct.pack("!B", length) 
        elif length < 0x10000 : bytes += struct.pack("!BH", 126, length)
        else                  : bytes += struct.pack("!BQ", 127, length)

        bytes += msg
        self.s.send(bytes)

    def recv(self, timeout=None):
        # Simple state machine to collect bytes and allow timeouts
        self.s.settimeout(timeout)

        data = self.s.recv(1024)
        self.recv_data += data
        if data == "":             # Safari
            return "" 

        if not self.header:
            if len(self.recv_data) >= 2:
                # Possibly enough for a full header
                header = struct.unpack("!BB", self.recv_data[:2])
                len_indicator = header[1] & 0x7F
                if len_indicator <= 125:
                    self.header = dict(fin_op=header[0], msg_len=len_indicator)
                    self.recv_data = self.recv_data[2:]
                elif len_indicator == 126 and len(self.recv_data) >= 4:
                    self.header = dict(fin_op=header[0], msg_len=struct.unpack("!BBH", self.recv_data[:4])[2]) 
                    self.recv_data = self.recv_data[4:]
                elif len_indicator == 127 and len(self.recv_data) >= 10:
                    self.header = dict(fin_op=header[0], msg_len=struct.unpack("!BBL", self.recv_data[:10])[2]) 
                    self.recv_data = self.recv_data[10:]

        if self.header:
            msg_len = self.header['msg_len']
            if len(self.recv_data) >= self.header['msg_len'] + 4:
                keys = struct.unpack("!4B", self.recv_data[:4])
                encoded = struct.unpack("%dB" % msg_len, self.recv_data[4:msg_len+4])
                decoded = [b ^ keys[idx % 4] for idx, b in enumerate(encoded)]
                self.recv_data = self.recv_data[msg_len+4:]
                self.header = None
                
                msg = struct.pack("%dB" % msg_len, *decoded)
                if msg == struct.pack("BB", 3, 233):          #Firefox and Chrome on close. Must be a standard
                    return ""
                else : 
                    return msg

        return None


    def close(self):
        self.onClose()
        self.s.close()

