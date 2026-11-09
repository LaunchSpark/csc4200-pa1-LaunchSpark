"""The transport seam, TCP version (Specification, Section 11).

This is the ONLY file in your project that may use the socket module. Your
server, client and protocol code call these six functions (through
transport.py) and nothing else.
In the final project you will write a second module with the same six
functions over your PA2 transport and switch to it.

Chapter 5, Section 5.8 (Figures 5.6-5.8) shows TCP sockets in Python,
including a recv_exact; you may adapt it, with a comment saying so.
"""
import socket


class ConnectionClosed(Exception):
    """The peer closed the stream.

    `clean` is True when the close happened before any byte of the requested
    read arrived (a close on a message boundary), False when it happened
    part-way through.
    """

    def __init__(self, clean):
        super().__init__("connection closed by peer")
        self.clean = clean


def listen(bind_addr, port):
    """Start accepting sessions on bind_addr:port; return a listener.
    Remember SO_REUSEADDR (Specification, Section 9)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((bind_addr, port))
    s.listen(128)
    return s


def accept(listener):
    """Wait for the next session; return (conn, peer_address)."""
    conn, (host, port) = listener.accept()
    return conn, f"{host}:{port}"


def connect(host, port):
    """Open a session to host:port; return conn."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    return s


def send_all(conn, data):
    """Send every byte of `data`, or raise an exception."""
    conn.sendall(data)


def recv_exact(conn, n):
    """Return exactly n bytes. Raise ConnectionClosed(clean=...) if the stream ends."""
    buf = bytearray()
    while len(buf) < n:
        try:
            chunk = conn.recv(n - len(buf))
        except (ConnectionResetError, BrokenPipeError):
            raise ConnectionClosed(clean=False)
        if not chunk:
            if len(buf) == 0:
                raise ConnectionClosed(clean=True)
            raise ConnectionClosed(clean=False)
        buf.extend(chunk)
    return bytes(buf)


def close(conn):
    """Close the session gracefully: shut down your sending side, read and
    discard whatever is still arriving until end-of-stream (or about a second
    passes), then close. Specification, Section 8.2 explains why."""
    try:
        conn.shutdown(socket.SHUT_WR)
        conn.settimeout(1.0)
        while True:
            data = conn.recv(4096)
            if not data:
                break
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
