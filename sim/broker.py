"""
Broker MQTT 3.1.1 mínimo (TCP y WebSocket) para la simulación.
Soporta: CONNECT/CONNACK (usuario y testamento), SUBSCRIBE/SUBACK con comodines
+ y #, PUBLISH QoS 0/1 (entrega en QoS 0), mensajes retenidos, PINGREQ y
DISCONNECT. Basta para probar el firmware y la app; no es un broker de producción.
"""
import asyncio, base64, hashlib, struct, threading


def _match(filtro, topico):
    f, t = filtro.split('/'), topico.split('/')
    for i, p in enumerate(f):
        if p == '#':
            return True
        if i >= len(t) or (p != '+' and p != t[i]):
            return False
    return len(f) == len(t)


def _enc_len(n):
    out = bytearray()
    while True:
        d, n = n % 128, n // 128
        out.append(d | (128 if n else 0))
        if not n:
            return bytes(out)


def _pkt(h, body):
    return bytes([h]) + _enc_len(len(body)) + body


def _str(s):
    b = s.encode()
    return struct.pack('!H', len(b)) + b


class Cliente:
    def __init__(self, broker, enviar):
        self.broker, self.enviar = broker, enviar
        self.subs, self.id, self.will = [], None, None

    def entregar(self, topico, payload, retain=False):
        body = _str(topico) + payload.encode()
        self.enviar(_pkt(0x30 | (1 if retain else 0), body))


class Broker:
    def __init__(self):
        self.clientes, self.retenidos, self.observadores = set(), {}, []

    def publicar(self, topico, payload, retain=False, origen=None):
        if retain:
            if payload == '':
                self.retenidos.pop(topico, None)
            else:
                self.retenidos[topico] = payload
        for obs in self.observadores:
            obs(topico, payload, retain)
        for c in list(self.clientes):
            if any(_match(f, topico) for f in c.subs):
                try:
                    c.entregar(topico, payload)
                except Exception:
                    pass

    def suscribir(self, c, filtro):
        c.subs.append(filtro)
        for t, p in list(self.retenidos.items()):
            if _match(filtro, t):
                c.entregar(t, p, retain=True)

    # ---------------------------------------------------------------- protocolo
    def procesar(self, c, h, body):
        tipo = h >> 4
        if tipo == 1:   # CONNECT
            p = 0
            n = struct.unpack('!H', body[p:p + 2])[0]; p += 2 + n
            p += 1  # nivel
            flags = body[p]; p += 1
            p += 2  # keepalive
            n = struct.unpack('!H', body[p:p + 2])[0]; c.id = body[p + 2:p + 2 + n].decode(); p += 2 + n
            if flags & 0x04:
                n = struct.unpack('!H', body[p:p + 2])[0]; wt = body[p + 2:p + 2 + n].decode(); p += 2 + n
                n = struct.unpack('!H', body[p:p + 2])[0]; wm = body[p + 2:p + 2 + n].decode(); p += 2 + n
                c.will = (wt, wm, bool(flags & 0x20))
            self.clientes.add(c)
            c.enviar(bytes([0x20, 2, 0, 0]))
        elif tipo == 3:  # PUBLISH
            qos, retain = (h >> 1) & 3, bool(h & 1)
            n = struct.unpack('!H', body[:2])[0]
            topico = body[2:2 + n].decode(); p = 2 + n
            if qos:
                c.enviar(bytes([0x40, 2]) + body[p:p + 2]); p += 2
            self.publicar(topico, body[p:].decode(errors='replace'), retain, c)
        elif tipo == 8:  # SUBSCRIBE
            pid = body[:2]; p = 2; filtros = []
            while p < len(body):
                n = struct.unpack('!H', body[p:p + 2])[0]
                filtros.append(body[p + 2:p + 2 + n].decode()); p += 2 + n + 1
            c.enviar(_pkt(0x90, pid + bytes([0] * len(filtros))))
            for f in filtros:
                self.suscribir(c, f)
        elif tipo == 12:  # PINGREQ
            c.enviar(bytes([0xD0, 0]))
        elif tipo == 14:  # DISCONNECT
            c.will = None

    def desconectar(self, c):
        if c in self.clientes:
            self.clientes.discard(c)
            if c.will:
                self.publicar(*c.will)

    # ---------------------------------------------------------------- transporte
    async def _leer_paquetes(self, c, leer):
        buf = bytearray()
        while True:
            datos = await leer()
            if not datos:
                return
            buf += datos
            while len(buf) >= 2:
                mult, n, i, completo = 1, 0, 1, False
                while i < len(buf):
                    b = buf[i]; i += 1; n += (b & 127) * mult; mult *= 128
                    if not b & 128:
                        completo = True
                        break
                if not completo or len(buf) < i + n:
                    break
                h, body = buf[0], bytes(buf[i:i + n]); del buf[:i + n]
                self.procesar(c, h, body)

    async def tcp(self, reader, writer):
        c = Cliente(self, lambda d: writer.write(d))
        try:
            await self._leer_paquetes(c, lambda: reader.read(4096))
        except Exception:
            pass
        self.desconectar(c); writer.close()

    async def websocket(self, reader, writer):
        req = (await reader.readuntil(b'\r\n\r\n')).decode()
        hdr = {l.split(':', 1)[0].strip().lower(): l.split(':', 1)[1].strip() for l in req.split('\r\n')[1:] if ':' in l}
        if 'sec-websocket-key' not in hdr:   # petición HTTP normal: servir la app
            await self._servir_http(req, writer); return
        acc = base64.b64encode(hashlib.sha1((hdr['sec-websocket-key'] + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
        writer.write(('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                      f'Sec-WebSocket-Accept: {acc}\r\nSec-WebSocket-Protocol: mqtt\r\n\r\n').encode())

        def enviar(d):
            n = len(d)
            cab = bytes([0x82, n]) if n < 126 else (bytes([0x82, 126]) + struct.pack('!H', n) if n < 65536 else bytes([0x82, 127]) + struct.pack('!Q', n))
            writer.write(cab + d)

        async def leer_frame():
            while True:
                b0, b1 = await reader.readexactly(2)
                op, n = b0 & 15, b1 & 127
                if n == 126: n = struct.unpack('!H', await reader.readexactly(2))[0]
                elif n == 127: n = struct.unpack('!Q', await reader.readexactly(8))[0]
                mask = await reader.readexactly(4) if b1 & 128 else b'\0\0\0\0'
                d = bytearray(await reader.readexactly(n))
                for i in range(n): d[i] ^= mask[i % 4]
                if op == 8: return b''
                if op == 9: writer.write(bytes([0x8A, 0])); continue
                if op in (0, 1, 2): return bytes(d)

        c = Cliente(self, enviar)
        try:
            await self._leer_paquetes(c, leer_frame)
        except Exception:
            pass
        self.desconectar(c); writer.close()

    async def _servir_http(self, req, writer):
        ruta = req.split(' ')[1].split('?')[0]
        try:
            cuerpo = open(self.archivo_app, 'rb').read() if ruta in ('/', '/index.html') else None
        except Exception:
            cuerpo = None
        if cuerpo is None:
            writer.write(b'HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n')
        else:
            writer.write(b'HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: '
                         + str(len(cuerpo)).encode() + b'\r\n\r\n' + cuerpo)
        await writer.drain(); writer.close()

    def iniciar(self, puerto_tcp=1883, puerto_ws=9001, archivo_app=None):
        self.archivo_app = archivo_app
        self.loop = asyncio.new_event_loop()
        listo = threading.Event()

        def correr():
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(asyncio.start_server(self.tcp, '127.0.0.1', puerto_tcp))
            self.loop.run_until_complete(asyncio.start_server(self.websocket, '127.0.0.1', puerto_ws))
            listo.set()
            self.loop.run_forever()

        threading.Thread(target=correr, daemon=True).start()
        listo.wait()

    def en_hilo(self, fn, *a):
        self.loop.call_soon_threadsafe(fn, *a)
