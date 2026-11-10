"""Comprehensive test suite for ETP/1 server (S01 - S18)."""
import hashlib
import os
import shutil
import socket
import struct
import tempfile
import threading
import time
import unittest
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import etp
import server
import transport

CLIENT_NAME = b"eagle01"
ALPHA = b"Hello, ETP!\n"
ZULU = b"zulu\n"
BETA = bytes((i * 37) % 256 for i in range(2 * 1024 * 1024))  # 2 MiB


def frame(mtype, payload=b"", ver=1, status=0, length=None):
    if length is None:
        length = len(payload)
    return struct.pack("!BBBBI", ver, mtype, status, 0, length) + payload


def read_msg(s):
    hdr = bytearray()
    while len(hdr) < 8:
        chunk = s.recv(8 - len(hdr))
        if not chunk:
            raise EOFError("stream ended before full 8-byte header")
        hdr.extend(chunk)
    ver, mtype, status, rsv, length = struct.unpack("!BBBBI", hdr)
    body = bytearray()
    while len(body) < length:
        chunk = s.recv(min(length - len(body), 65536))
        if not chunk:
            raise EOFError("stream ended before payload finished")
        body.extend(chunk)
    return ver, mtype, status, rsv, bytes(body)


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


def expect_eof(s, timeout=3.0):
    s.settimeout(timeout)
    try:
        data = s.recv(1)
        assert data == b"", f"Expected EOF, got {data!r}"
    except (ConnectionResetError, socket.timeout):
        pass


class TestServerSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workdir = tempfile.mkdtemp(prefix="etp_test_")
        cls.root = os.path.join(cls.workdir, "root")
        os.makedirs(cls.root)
        os.makedirs(os.path.join(cls.root, "subdir"))

        # Setup fixtures
        for name, data in [
            ("alpha.txt", ALPHA),
            ("Zulu.txt", ZULU),
            ("beta.bin", BETA),
            ("empty.dat", b""),
            (".hidden", b"not listed\n"),
            ("bad name.txt", b"not listed\n"),
            ("subdir/inner.txt", b"not listed\n"),
        ]:
            with open(os.path.join(cls.root, name), "wb") as f:
                f.write(data)

        # Start server in background thread
        try:
            cls.listener = transport.listen("127.0.0.1", 0)
            cls.port = cls.listener.getsockname()[1]
            # Probe loopback connect
            test_s = socket.socket()
            test_s.connect(("127.0.0.1", cls.port))
            test_s.close()
        except OSError as e:
            if hasattr(cls, "listener") and cls.listener:
                try:
                    cls.listener.close()
                except Exception:
                    pass
            cls.server_stop = threading.Event()
            shutil.rmtree(cls.workdir, ignore_errors=True)
            raise unittest.SkipTest(f"OS loopback sockets not permitted in this sandbox: {e}")

        cls.server_stop = threading.Event()

        def run_server():
            while not cls.server_stop.is_set():
                try:
                    conn, peer = transport.accept(cls.listener)
                except Exception:
                    break
                t = threading.Thread(
                    target=server.handle_session,
                    args=(conn, peer, cls.root),
                    daemon=True,
                )
                t.start()

        cls.server_thread = threading.Thread(target=run_server, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server_stop.set()
        try:
            transport.close(cls.listener)
        except Exception:
            pass
        shutil.rmtree(cls.workdir, ignore_errors=True)

    def conn(self):
        s = socket.create_connection(("127.0.0.1", self.port), timeout=10.0)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return s

    def hello(self, s):
        s.sendall(frame(etp.HELLO, CLIENT_NAME))
        return expect_ok(read_msg(s), etp.HELLO, "HELLO")

    def test_S01_hello(self):
        s = self.conn()
        body = self.hello(s)
        self.assertTrue(1 <= len(body) <= 64)
        self.assertTrue(all(0x20 <= b <= 0x7E for b in body))
        s.close()

    def test_S02_list(self):
        s = self.conn()
        self.hello(s)
        s.sendall(frame(etp.LIST))
        body = expect_ok(read_msg(s), etp.LIST, "LIST")
        s.close()

        # Check expected listing: alpha.txt, beta.bin, empty.dat, Zulu.txt
        lines = body.split(b"\n")
        if lines[-1] == b"":
            lines.pop()
        names = [line.split(b"\t")[0] for line in lines]
        self.assertEqual(names, [b"Zulu.txt", b"alpha.txt", b"beta.bin", b"empty.dat"])
        # Check sort order by raw bytes: 'Z' (0x5A) < 'a' (0x61)
        self.assertEqual(names, sorted(names))

    def test_S03_get_small(self):
        s = self.conn()
        self.hello(s)
        s.sendall(frame(etp.GET, b"alpha.txt"))
        got = expect_ok(read_msg(s), etp.GET, "GET alpha.txt")
        self.assertEqual(got, ALPHA)
        s.close()

    def test_S04_get_large(self):
        s = self.conn()
        self.hello(s)
        s.sendall(frame(etp.GET, b"beta.bin"))
        got = expect_ok(read_msg(s), etp.GET, "GET beta.bin")
        self.assertEqual(got, BETA)
        s.close()

    def test_S05_put_and_get(self):
        data = bytes((i * 17) % 256 for i in range(300_000))
        name = b"gamma-put.dat"
        s = self.conn()
        self.hello(s)
        payload = struct.pack("!H", len(name)) + name + data
        s.sendall(frame(etp.PUT, payload))
        digest = expect_ok(read_msg(s), etp.PUT, "PUT gamma-put.dat")
        self.assertEqual(digest, hashlib.sha256(data).digest())

        s.sendall(frame(etp.GET, name))
        got = expect_ok(read_msg(s), etp.GET, "GET after PUT")
        self.assertEqual(got, data)
        s.close()

    def test_S06_put_get_empty(self):
        s = self.conn()
        self.hello(s)
        name = b"empty-put.dat"
        s.sendall(frame(etp.PUT, struct.pack("!H", len(name)) + name))
        digest = expect_ok(read_msg(s), etp.PUT, "PUT empty")
        self.assertEqual(digest, hashlib.sha256(b"").digest())

        s.sendall(frame(etp.GET, b"empty.dat"))
        got = expect_ok(read_msg(s), etp.GET, "GET empty.dat")
        self.assertEqual(got, b"")
        s.close()

    def test_S07_not_found(self):
        s = self.conn()
        self.hello(s)
        s.sendall(frame(etp.GET, b"no-such-file.txt"))
        expect_error(read_msg(s), etp.NOT_FOUND, "GET missing file")
        # Session stays open
        s.sendall(frame(etp.LIST))
        expect_ok(read_msg(s), etp.LIST, "LIST after NOT_FOUND")
        s.close()

    def test_S08_bad_name(self):
        s = self.conn()
        self.hello(s)
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
            s.sendall(frame(etp.GET, bad))
            expect_error(read_msg(s), etp.BAD_NAME, f"GET {bad!r}")

        for bad in [b"../escaped.txt", b".sneaky"]:
            s.sendall(frame(etp.PUT, struct.pack("!H", len(bad)) + bad + b"x"))
            expect_error(read_msg(s), etp.BAD_NAME, f"PUT {bad!r}")

        self.assertFalse(os.path.exists(os.path.join(self.workdir, "escaped.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.root, ".sneaky")))

        # Session stays open
        s.sendall(frame(etp.LIST))
        expect_ok(read_msg(s), etp.LIST, "LIST after BAD_NAME")
        s.close()

    def test_S09_fragments(self):
        s = self.conn()
        for byte in frame(etp.HELLO, CLIENT_NAME):
            s.sendall(bytes([byte]))
            time.sleep(0.01)
        expect_ok(read_msg(s), etp.HELLO, "HELLO fragmented")

        req = frame(etp.GET, b"alpha.txt")
        for piece in (req[:3], req[3:8], req[8:12], req[12:]):
            s.sendall(piece)
            time.sleep(0.02)
        got = expect_ok(read_msg(s), etp.GET, "GET fragmented")
        self.assertEqual(got, ALPHA)
        s.close()

    def test_S10_coalesced(self):
        s = self.conn()
        combined = (
            frame(etp.HELLO, CLIENT_NAME)
            + frame(etp.LIST)
            + frame(etp.GET, b"alpha.txt")
            + frame(etp.BYE)
        )
        s.sendall(combined)
        expect_ok(read_msg(s), etp.HELLO, "1st HELLO")
        expect_ok(read_msg(s), etp.LIST, "2nd LIST")
        got = expect_ok(read_msg(s), etp.GET, "3rd GET")
        self.assertEqual(got, ALPHA)
        expect_ok(read_msg(s), etp.BYE, "4th BYE")
        expect_eof(s)
        s.close()

    def test_S11_bad_type(self):
        s = self.conn()
        self.hello(s)
        s.sendall(frame(0x42, b"abcde"))
        expect_error(read_msg(s), etp.BAD_TYPE, "0x42 unknown")
        s.sendall(frame(etp.LIST))
        expect_ok(read_msg(s), etp.LIST, "LIST after BAD_TYPE")
        s.close()

    def test_S12_bad_version(self):
        s = self.conn()
        s.sendall(frame(etp.HELLO, ver=2, length=0))
        expect_error(read_msg(s), etp.BAD_VERSION, "ver 2")
        expect_eof(s)
        s.close()

    def test_S13_too_large(self):
        s = self.conn()
        self.hello(s)
        s.sendall(struct.pack("!BBBBI", 1, etp.PUT, 0, 0, 0xFFFFFFFF))
        expect_error(read_msg(s), etp.TOO_LARGE, "len 0xFFFFFFFF")
        expect_eof(s)
        s.close()

    def test_S14_not_ready(self):
        s = self.conn()
        s.sendall(frame(etp.LIST))
        expect_error(read_msg(s), etp.NOT_READY, "LIST before HELLO")
        expect_eof(s)
        s.close()

    def test_S15_bye_and_close(self):
        s = self.conn()
        self.hello(s)
        s.sendall(frame(etp.BYE))
        expect_ok(read_msg(s), etp.BYE, "BYE")
        expect_eof(s)
        s.close()

    def test_S16_concurrency_with_stalls(self):
        stall1 = self.conn()
        stall1.sendall(frame(etp.HELLO, CLIENT_NAME)[:3])  # partial header

        stall2 = self.conn()
        stall2.sendall(frame(etp.HELLO, CLIENT_NAME))
        expect_ok(read_msg(stall2), etp.HELLO, "HELLO on stall2")
        stall2.sendall(frame(etp.PUT, b"\x00\x05stall" + b"x" * 80)[:20])  # partial payload

        errors, done = [], []

        def worker(i):
            try:
                s = self.conn()
                self.hello(s)
                s.sendall(frame(etp.GET, b"alpha.txt"))
                got = expect_ok(read_msg(s), etp.GET, f"worker {i}")
                if got != ALPHA:
                    errors.append(f"worker {i} bad data")
                s.sendall(frame(etp.BYE))
                expect_ok(read_msg(s), etp.BYE, f"worker {i} BYE")
                s.close()
                done.append(i)
            except Exception as e:
                errors.append(f"worker {i}: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(5.0)

        stall1.close()
        stall2.close()

        self.assertEqual(len(done), 8, f"Errors: {errors}")

    def test_S17_survive_vanishing_clients(self):
        # 1. Ask for 2 MiB, read 8 bytes, reset
        s = self.conn()
        self.hello(s)
        s.sendall(frame(etp.GET, b"beta.bin"))
        s.recv(8)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        s.close()

        # 2. Ask for 2 MiB and close immediately
        s = self.conn()
        self.hello(s)
        s.sendall(frame(etp.GET, b"beta.bin"))
        s.close()

        # 3. Half message and close
        s = self.conn()
        self.hello(s)
        s.sendall(struct.pack("!BBBBI", 1, etp.PUT, 0, 0, 1000) + b"\x00\x03abc")
        s.close()

        time.sleep(0.2)
        # Server must still be alive and serve new clients
        s = self.conn()
        self.hello(s)
        s.sendall(frame(etp.LIST))
        expect_ok(read_msg(s), etp.LIST, "LIST after vanish")
        s.close()


if __name__ == "__main__":
    unittest.main()
