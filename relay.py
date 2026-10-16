import socket, threading, base64, os, sys

LISTEN = ('127.0.0.1', 8888)
px = os.environ['https_proxy'].replace('http://', '')
creds, hp = px.split('@')
host, port = hp.split(':')
port = int(port)
auth = base64.b64encode(creds.encode()).decode()

def relay(a, b):
    try:
        while True:
            d = a.recv(65536)
            if not d:
                break
            b.sendall(d)
    except Exception:
        pass
    finally:
        try: a.shutdown(socket.SHUT_RD)
        except Exception: pass

def handle(c):
    u = None
    try:
        req = b''
        while b'\r\n\r\n' not in req:
            d = c.recv(4096)
            if not d:
                return
            req += d
            if len(req) > 65536:
                return
        header, _, body = req.partition(b'\r\n\r\n')
        lines = header.decode('latin1').split('\r\n')
        print('>>> ' + lines[0], flush=True)
        u = socket.create_connection((host, port), timeout=15)
        lines.insert(1, 'Proxy-Authorization: Basic ' + auth)
        u.sendall(('\r\n'.join(lines) + '\r\n\r\n').encode('latin1') + body)
        resp = b''
        while b'\r\n\r\n' not in resp:
            d = u.recv(4096)
            if not d:
                break
            resp += d
        first = resp.split(b'\r\n')[0].decode('latin1', 'replace') if resp else '<empty>'
        print('<<< ' + first, flush=True)
        if not resp:
            return
        c.sendall(resp)
        t = threading.Thread(target=relay, args=(u, c), daemon=True)
        t.start()
        relay(c, u)
        t.join(timeout=1)
    except Exception as e:
        print('ERR ' + str(e), flush=True)
    finally:
        for s in (c, u):
            try:
                if s: s.close()
            except Exception:
                pass

srv = socket.socket()
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(LISTEN)
srv.listen(100)
print('relay listening on 127.0.0.1:8888 -> egress proxy', flush=True)
while True:
    c, addr = srv.accept()
    print('+++ accept from %s:%d' % (addr[0], addr[1]), flush=True)
    threading.Thread(target=handle, args=(c,), daemon=True).start()
