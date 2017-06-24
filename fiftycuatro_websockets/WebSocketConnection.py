import struct

class WebSocketConnection:
    FULL_UTF8_HEADER = struct.pack("!B", 0x80 | 0x01)

    def __init__(self, clientsocket):
        self.s = clientsocket
    
    def send(self, msg):
        bytes = self.FULL_UTF8_HEADER
        
        length = len(msg)
        if   length <= 125    : bytes += struct.pack("!B", length) 
        elif length < 0x10000 : bytes += struct.pack("!BH", 126, length)
        else                  : bytes += struct.pack("!BQ", 127, length)

        bytes += msg
        self.s.send(bytes)

    def recv(self):
        fin_and_opcode = self.s.recv(1)
        mask_and_len_indicator = struct.unpack("B", self.s.recv(1))[0]
        length_indicator = mask_and_len_indicator & 0x7F 

        if   length_indicator <= 125 : length = length_indicator
        elif length_indicator == 126 : length = struct.unpack('H', self.s.recv(2))[0]
        else                         : length = struct.unpack('L', self.s.recv(8))[0]
        
        keys = struct.unpack("4B", self.s.recv(4))
        encoded = struct.unpack("%dB" % length, self.s.recv(length))
        
        decoded = [b ^ keys[idx % 4] for idx, b in enumerate(encoded)]
        return struct.pack("%dB" % length, *decoded)

    def close(self):
        self.s.close()
