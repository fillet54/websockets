import sys
import socket
import string, re
import hashlib, base64
import threading
import struct

from WebSocketConnection import WebSocketConnection

class WebSocketServer(object):
    
    WS_MAGIC_STRING = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(self, path="/", port=4567, host="localhost"):
        self.path = path
        self.port = port
        self.host = host
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((host, port))
        self.s.listen(5)
        self.factory = None 
        self.clients = dict()

    def runForever(self):
        while True:
            try:
                client = self.accept()
                runner = WebSocketClientRunner(client)
                self.clients[client] = runner
                t = threading.Thread(target=runner.run)
                t.daemon = True
                t.start()
            except socket.error:
                return

    def accept(self):
        (client, address) = self.s.accept()
        if self.send_handshake(client) and self.factory is not None:
            return WebSocketNofityOnCloseClient(self.factory(client, address), self.onClientClose)
        else:
            return None

    def close(self):
        [c.close() for c in self.clients.keys()]
        self.s.close()

    def onClientClose(self, client):
        print "Closing Client"
        try:
            del self.clients[client]
        except KeyError:
            print "ERROR"

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

class WebSocketClientRunner(object):
    def __init__(self, ws_conn):
        self.ws_conn = ws_conn

    def run(self):
        self.ws_conn.onOpen()
        while True:
            print self.ws_conn
            try:
                msg = self.ws_conn.recv(timeout=15.0)
                if msg == "":
                    self.ws_conn.close()
                    return
                elif msg is not None:
                    print struct.unpack("%dB" % len(msg), msg)
                    self.ws_conn.onMessage(msg)

            except socket.timeout:
                print "Timeout!"
            except socket.error:
                self.ws_conn.close()
                return


    def close(self):
        self.ws_conn.close()
        self.ws_conn.onClose()

class WebSocketNofityOnCloseClient(WebSocketConnection):
    def __init__(self, ws_conn, onCloseCallback):
        self.ws_conn = ws_conn
        self.onCloseCallback = onCloseCallback

    def onOpen(self):
        try:
            self.ws_conn.onOpen()
        except:
            pass

    def onMessage(self, message):
        try:
            self.ws_conn.onMessage(message)
        except:
            pass

    def onClose(self):
        self.onCloseCallback(self)

    def recv(self, timeout=None):
        return self.ws_conn.recv(timeout)

    def send(self, message):
        return self.ws_conn.send(message)

    def close(self):
        self.onClose()
        try:
            self.ws_conn.close()
        except:
            pass

