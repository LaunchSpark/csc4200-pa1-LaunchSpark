"""In-memory seam tests for ETP/1 server (pure Python, zero OS socket dependency)."""
import hashlib
import os
import shutil
import struct
import tempfile
import threading
import time
import unittest
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import etp
import server

CLIENT_NAME = b"eagle01"
ALPHA = b"Hello, ETP!\n"
ZULU = b"zulu\n"
BETA = bytes((i * 37) % 256 for i in range(2 * 1024 * 1024))  # 2 MiB


class MockConnectionClosed(Exception):
    def __init__(self, clean=True):
        self.clean = clean
        super().__init__("connection closed")


class DuplexPipe:
    def __init__(self):
        self._c2s_buf = bytearray()
        self._s2c_buf = bytearray()
        self._cv = threading.Condition()
        self._c2s_closed = False
        self._s2c_closed = False

    def client_send(self, data):
        with self._cv:
            if self._c2s_closed:
                raise BrokenPipeError("client write to closed pipe")
            self._c2s_buf.extend(data)
            self._cv.notify_all()

    def client_recv(self, n):
        with self._cv:
            while len(self._s2c_buf) < n and not self._s2c_closed:
                self._cv.wait()
            if len(self._s2c_buf) < n:
                if len(self._s2c_buf) == 0:
                    raise MockConnectionClosed(clean=True)
                raise MockConnectionClosed(clean=False)
            res = bytes(self._s2c_buf[:n])
            del self._s2c_buf[:n]
            return res

    def server_send(self, data):
        with self._cv:
            if self._s2c_closed:
                raise BrokenPipeError("server write to closed pipe")
            self._s2c_buf.extend(data)
            self._cv.notify_all()

    def server_recv(self, n):
        with self._cv:
            while len(self._c2s_buf) < n and not self._c2s_closed:
                self._cv.wait()
            if len(self._c2s_buf) < n:
                if len(self._c2s_buf) == 0:
                    raise MockConnectionClosed(clean=True)
                raise MockConnectionClosed(clean=False)
            res = bytes(self._c2s_buf[:n])
            del self._c2s_buf[:n]
            return res

    def client_close(self):
        with self._cv:
            self._c2s_closed = True
            self._cv.notify_all()

    def server_close(self):
        with self._cv:
            self._s2c_closed = True
            self._cv.notify_all()


class ServerTransportAdapter:
    ConnectionClosed = MockConnectionClosed

    @staticmethod
    def send_all(conn, data):
        conn.server_send(data)

    @staticmethod
    def recv_exact(conn, n):
        return conn.server_recv(n)

    @staticmethod
    def close(conn):
        conn.server_close()


def frame(mtype, payload=b"", ver=1, status=0, length=None):
    if length is None:
        length = len(payload)
    return struct.pack("!BBBBI", ver, mtype, status, 0, length) + payload


def client_read_msg(pipe):
    hdr = pipe.client_recv(8)
    ver, mtype, status, rsv, length = struct.unpack("!BBBBI", hdr)
    body = pipe.client_recv(length) if length > 0 else b""
    return ver, mtype, status, rsv, body


def expect_ok(resp, req_type, what=""):
    ver, mtype, status, rsv, body = resp
    if mtype == etp.ERROR:
        raise AssertionError(f"{what}: got ERROR code {status} ({body[:80]!r})")
    assert ver == 1, f"Expected ver 1, got {ver}"
    assert mtype == (req_type | 0x80), f"Expected type {req_type | 0x80:#04x}, got {mtype:#04x}"
    assert status == 0, f"Expected status 0, got {status}"
    assert rsv == 0, f"Expected rsv 0, got {rsv}"
    return body


def expect_error(resp, code, what=""):
    ver, mtype, status, rsv, body = resp
    assert mtype == etp.ERROR, f"{what}: expected ERROR, got {mtype:#04x}"
    assert status == code, f"{what}: expected code {code}, got {status}"
    assert ver == 1, f"{what}: expected ver 1, got {ver}"
    assert len(body) <= 200, f"{what}: error text > 200 bytes ({len(body)})"


def expect_eof(pipe):
    try:
        pipe.client_recv(1)
        raise AssertionError("Expected EOF, but received bytes")
    except MockConnectionClosed:
        pass


class TestServerMockTransport(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.mkdtemp(prefix="etp_mock_")
        self.root = os.path.join(self.workdir, "root")
        os.makedirs(self.root)
        os.makedirs(os.path.join(self.root, "subdir"))

        for name, data in [
            ("alpha.txt", ALPHA),
            ("Zulu.txt", ZULU),
            ("beta.bin", BETA),
            ("empty.dat", b""),
            (".hidden", b"not listed\n"),
            ("bad name.txt", b"not listed\n"),
            ("subdir/inner.txt", b"not listed\n"),
        ]:
            with open(os.path.join(self.root, name), "wb") as f:
                f.write(data)

        # Monkey-patch server's transport module to ServerTransportAdapter
        self._orig_transport = server.transport
        server.transport = ServerTransportAdapter

    def tearDown(self):
        server.transport = self._orig_transport
        shutil.rmtree(self.workdir, ignore_errors=True)

    def start_session(self):
        pipe = DuplexPipe()
        t = threading.Thread(
            target=server.handle_session,
            args=(pipe, "127.0.0.1:42000", self.root),
            daemon=True,
        )
        t.start()
        return pipe, t

    def hello(self, pipe):
        pipe.client_send(frame(etp.HELLO, CLIENT_NAME))
        return expect_ok(client_read_msg(pipe), etp.HELLO, "HELLO")

    def test_S01_hello(self):
        pipe, t = self.start_session()
        body = self.hello(pipe)
        self.assertTrue(1 <= len(body) <= 64)
        self.assertTrue(all(0x20 <= b <= 0x7E for b in body))
        pipe.client_close()
        t.join(1)

    def test_S02_list(self):
        pipe, t = self.start_session()
        self.hello(pipe)
        pipe.client_send(frame(etp.LIST))
        body = expect_ok(client_read_msg(pipe), etp.LIST, "LIST")

        lines = body.split(b"\n")
        if lines[-1] == b"":
            lines.pop()
        names = [line.split(b"\t")[0] for line in lines]
        self.assertEqual(names, [b"Zulu.txt", b"alpha.txt", b"beta.bin", b"empty.dat"])
        pipe.client_close()
        t.join(1)

    def test_S03_get_small(self):
        pipe, t = self.start_session()
        self.hello(pipe)
        pipe.client_send(frame(etp.GET, b"alpha.txt"))
        got = expect_ok(client_read_msg(pipe), etp.GET, "GET alpha.txt")
        self.assertEqual(got, ALPHA)
        pipe.client_close()
        t.join(1)

    def test_S04_get_large(self):
        pipe, t = self.start_session()
        self.hello(pipe)
        pipe.client_send(frame(etp.GET, b"beta.bin"))
        got = expect_ok(client_read_msg(pipe), etp.GET, "GET beta.bin")
        self.assertEqual(got, BETA)
        pipe.client_close()
        t.join(1)

    def test_S05_put_and_get(self):
        data = bytes((i * 17) % 256 for i in range(300_000))
        name = b"gamma-put.dat"
        pipe, t = self.start_session()
        self.hello(pipe)
        payload = struct.pack("!H", len(name)) + name + data
        pipe.client_send(frame(etp.PUT, payload))
        digest = expect_ok(client_read_msg(pipe), etp.PUT, "PUT gamma-put.dat")
        self.assertEqual(digest, hashlib.sha256(data).digest())

        pipe.client_send(frame(etp.GET, name))
        got = expect_ok(client_read_msg(pipe), etp.GET, "GET after PUT")
        self.assertEqual(got, data)
        pipe.client_close()
        t.join(1)

    def test_S06_put_get_empty(self):
        pipe, t = self.start_session()
        self.hello(pipe)
        name = b"empty-put.dat"
        pipe.client_send(frame(etp.PUT, struct.pack("!H", len(name)) + name))
        digest = expect_ok(client_read_msg(pipe), etp.PUT, "PUT empty")
        self.assertEqual(digest, hashlib.sha256(b"").digest())

        pipe.client_send(frame(etp.GET, b"empty.dat"))
        got = expect_ok(client_read_msg(pipe), etp.GET, "GET empty.dat")
        self.assertEqual(got, b"")
        pipe.client_close()
        t.join(1)

    def test_S07_not_found(self):
        pipe, t = self.start_session()
        self.hello(pipe)
        pipe.client_send(frame(etp.GET, b"no-such-file.txt"))
        expect_error(client_read_msg(pipe), etp.NOT_FOUND, "GET missing file")
        pipe.client_send(frame(etp.LIST))
        expect_ok(client_read_msg(pipe), etp.LIST, "LIST after NOT_FOUND")
        pipe.client_close()
        t.join(1)

    def test_S08_bad_name(self):
        pipe, t = self.start_session()
        self.hello(pipe)
        bad_names = [
            b"../alpha.txt",
            b"subdir/inner.txt",
            b".hidden",
            b"a" * 65,
            b"bad name.txt",
            b"alpha.txt\n",
            b"alpha.txt\x00junk",
        ]
        for bad in bad_names:
            pipe.client_send(frame(etp.GET, bad))
            expect_error(client_read_msg(pipe), etp.BAD_NAME, f"GET {bad!r}")

        for bad in [b"../escaped.txt", b".sneaky"]:
            pipe.client_send(frame(etp.PUT, struct.pack("!H", len(bad)) + bad + b"x"))
            expect_error(client_read_msg(pipe), etp.BAD_NAME, f"PUT {bad!r}")

        self.assertFalse(os.path.exists(os.path.join(self.workdir, "escaped.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.root, ".sneaky")))

        pipe.client_send(frame(etp.LIST))
        expect_ok(client_read_msg(pipe), etp.LIST, "LIST after BAD_NAME")
        pipe.client_close()
        t.join(1)

    def test_S09_fragments(self):
        pipe, t = self.start_session()
        for byte in frame(etp.HELLO, CLIENT_NAME):
            pipe.client_send(bytes([byte]))
            time.sleep(0.005)
        expect_ok(client_read_msg(pipe), etp.HELLO, "HELLO fragmented")

        req = frame(etp.GET, b"alpha.txt")
        for piece in (req[:3], req[3:8], req[8:12], req[12:]):
            pipe.client_send(piece)
            time.sleep(0.01)
        got = expect_ok(client_read_msg(pipe), etp.GET, "GET fragmented")
        self.assertEqual(got, ALPHA)
        pipe.client_close()
        t.join(1)

    def test_S10_coalesced(self):
        pipe, t = self.start_session()
        combined = (
            frame(etp.HELLO, CLIENT_NAME)
            + frame(etp.LIST)
            + frame(etp.GET, b"alpha.txt")
            + frame(etp.BYE)
        )
        pipe.client_send(combined)
        expect_ok(client_read_msg(pipe), etp.HELLO, "1st HELLO")
        expect_ok(client_read_msg(pipe), etp.LIST, "2nd LIST")
        got = expect_ok(client_read_msg(pipe), etp.GET, "3rd GET")
        self.assertEqual(got, ALPHA)
        expect_ok(client_read_msg(pipe), etp.BYE, "4th BYE")
        expect_eof(pipe)
        pipe.client_close()
        t.join(1)

    def test_S11_bad_type(self):
        pipe, t = self.start_session()
        self.hello(pipe)
        pipe.client_send(frame(0x42, b"abcde"))
        expect_error(client_read_msg(pipe), etp.BAD_TYPE, "0x42 unknown")
        pipe.client_send(frame(etp.LIST))
        expect_ok(client_read_msg(pipe), etp.LIST, "LIST after BAD_TYPE")
        pipe.client_close()
        t.join(1)

    def test_S12_bad_version(self):
        pipe, t = self.start_session()
        pipe.client_send(frame(etp.HELLO, ver=2, length=0))
        expect_error(client_read_msg(pipe), etp.BAD_VERSION, "ver 2")
        expect_eof(pipe)
        pipe.client_close()
        t.join(1)

    def test_S13_too_large(self):
        pipe, t = self.start_session()
        self.hello(pipe)
        pipe.client_send(struct.pack("!BBBBI", 1, etp.PUT, 0, 0, 0xFFFFFFFF))
        expect_error(client_read_msg(pipe), etp.TOO_LARGE, "len 0xFFFFFFFF")
        expect_eof(pipe)
        pipe.client_close()
        t.join(1)

    def test_S14_not_ready(self):
        pipe, t = self.start_session()
        pipe.client_send(frame(etp.LIST))
        expect_error(client_read_msg(pipe), etp.NOT_READY, "LIST before HELLO")
        expect_eof(pipe)
        pipe.client_close()
        t.join(1)

    def test_S15_bye_and_close(self):
        pipe, t = self.start_session()
        self.hello(pipe)
        pipe.client_send(frame(etp.BYE))
        expect_ok(client_read_msg(pipe), etp.BYE, "BYE")
        expect_eof(pipe)
        pipe.client_close()
        t.join(1)

    def test_S16_concurrency_with_stalls(self):
        stall1, t1 = self.start_session()
        stall1.client_send(frame(etp.HELLO, CLIENT_NAME)[:3])

        stall2, t2 = self.start_session()
        stall2.client_send(frame(etp.HELLO, CLIENT_NAME))
        expect_ok(client_read_msg(stall2), etp.HELLO, "HELLO on stall2")
        stall2.client_send(frame(etp.PUT, b"\x00\x05stall" + b"x" * 80)[:20])

        errors, done = [], []

        def worker(i):
            try:
                pipe, tw = self.start_session()
                self.hello(pipe)
                pipe.client_send(frame(etp.GET, b"alpha.txt"))
                got = expect_ok(client_read_msg(pipe), etp.GET, f"worker {i}")
                if got != ALPHA:
                    errors.append(f"worker {i} bad data")
                pipe.client_send(frame(etp.BYE))
                expect_ok(client_read_msg(pipe), etp.BYE, f"worker {i} BYE")
                expect_eof(pipe)
                pipe.client_close()
                tw.join(2.0)
                done.append(i)
            except Exception as e:
                errors.append(f"worker {i}: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for th in threads:
            th.start()
        for th in threads:
            th.join(5.0)

        stall1.client_close()
        stall2.client_close()
        t1.join(2)
        t2.join(2)

        self.assertEqual(len(done), 8, f"Errors: {errors}")

    def test_S17_survive_vanishing_clients(self):
        # 1. Ask for 2 MiB, read 8 bytes, reset / close abruptly
        pipe, t = self.start_session()
        self.hello(pipe)
        pipe.client_send(frame(etp.GET, b"beta.bin"))
        pipe.client_recv(8)
        pipe.client_close()
        t.join(2)

        # 2. Ask for 2 MiB and close immediately without reading
        pipe, t = self.start_session()
        self.hello(pipe)
        pipe.client_send(frame(etp.GET, b"beta.bin"))
        pipe.client_close()
        t.join(2)

        # 3. Half message and close
        pipe, t = self.start_session()
        self.hello(pipe)
        pipe.client_send(struct.pack("!BBBBI", 1, etp.PUT, 0, 0, 1000) + b"\x00\x03abc")
        pipe.client_close()
        t.join(2)

        # Server still accepts and serves new clients
        pipe, t = self.start_session()
        self.hello(pipe)
        pipe.client_send(frame(etp.LIST))
        expect_ok(client_read_msg(pipe), etp.LIST, "LIST after vanish")
        pipe.client_close()
        t.join(2)


if __name__ == "__main__":
    unittest.main()
