import socket
import string, re
import hashlib, base64

from WebSocketConnection import WebSocketConnection

class WebSocketServer:
    
    WS_MAGIC_STRING = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(self, path="/", port=4567, host="localhost"):
        self.path = path
        self.port = port
        self.host = host
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((host, port))
        self.s.listen(5)

    def accept(self):
        (client, address) = self.s.accept()
        if self.send_handshake(client):
            return WebSocketConnection(client)
        else:
            return None

    def send_handshake(self, client):
        lines = self.splitlines(client)
        request_line = lines.next()
        header = string.join(lines, '\n')
        
        request_match = re.search(r'GET (.*) HTTP/1.1', request_line)
        header_match = re.search(r'Sec-WebSocket-Key: (.*)\r\n', header)
        
        if request_match and header_match:
            ws_accept = self.create_accept(header_match.group(1))
            self.send_handshake_response(client, ws_accept)
            return True
        else:
            self.send_400(client)
            return False

    def create_accept(self, key):
        hash = hashlib.sha1()
        hash.update(key)
        hash.update(self.WS_MAGIC_STRING)
        return base64.b64encode(hash.digest())

    def send_handshake_response(self, client, ws_accept):
        client.send(('HTTP/1.1 101 Switching Protocols\r\n'
                     'Upgrade: websocket\r\n'
                     'Connection: Upgrade\r\n'
                     'Sec-WebSocket-Accept: %s\r\n\r\n' % ws_accept))

    def send_400(self, client):
        client.send(('HTTP/1.1 400 Bad Request\r\n'
                     'Content-Type: text/plain\r\n'
                     'Connection: close\r\n'
                     '\r\n'
                     'Incorrect request'))
        client.close()

    # default bufsize is 1 to ensure it doesn't read more than
    # required for termination. This method is only used for
    # parsing the header on initial connection the performance
    # impacts if any should be negligable. If this is being used
    # for a more general purpose function then it would be best
    # to return a line, buffer tuple and take an inital buffer
    # value
    def splitlines(self, s, bufsize=1):
        buffer = s.recv(bufsize)
        buffering = True
        while buffering:
            if '\n' in buffer:
                (line, buffer) = buffer.split('\n', 1)
                if line + '\n' == '\r\n':
                    raise StopIteration

                yield line + '\n'
            else:
                more = s.recv(bufsize)
                if not more:
                    buffering = False
                else:
                    buffer += more
        if buffer:
            yield buffer

