# PA1 Design — ETP/1 Client and Server

## 1. Architecture

The ETP/1 system is structured in three distinct layers to separate network transport, protocol wire formatting, and application session logic:

```
+-----------------------------------------------------------+
|                   Application Layer                       |
|   etp-server (src/server.py)    etp-client (src/client.py)|
+-----------------------------------------------------------+
                             |
+-----------------------------------------------------------+
|                   Protocol Framing Layer                  |
|                      src/etp.py                           |
|       - encode(mtype, payload, status)                    |
|       - read_message(conn, transport)                     |
|       - valid_name(name_bytes)                            |
+-----------------------------------------------------------+
                             |
+-----------------------------------------------------------+
|                   Transport Seam Layer                    |
|                      src/transport.py                     |
|                   src/transport_tcp.py                    |
|   listen(), accept(), connect(), send_all(),              |
|   recv_exact(), close()                                   |
+-----------------------------------------------------------+
                             |
                   OS TCP Socket Interface
```

- **`src/transport_tcp.py`**: Encapsulates all interactions with the operating system's socket API. Exposes the six required seam primitives (`listen`, `accept`, `connect`, `send_all`, `recv_exact`, `close`).
- **`src/transport.py`**: The seam selector. Contains a single import line (`from transport_tcp import *`) that the application code imports.
- **`src/etp.py`**: Protocol wire definitions, binary header packing/unpacking using Python's `struct.Struct("!BBBBI")`, message encoding, header parsing, and regular expression validation for file names.
- **`src/server.py`**: Accepts incoming connections, spawns a worker thread per session, evaluates protocol invariants according to Section 8.1, manages local file storage in the root directory, logs each response to standard output, and executes active socket closure.
- **`src/client.py`**: Parses CLI parameters (`list`, `get`, `put`), establishes the transport connection, performs the HELLO handshake, issues the command, verifies response headers and payloads, logs diagnostic errors to standard error, and returns exit codes 0–3.

---

## 2. The transport seam

The transport module is implemented in `src/transport_tcp.py` and exported through `src/transport.py`. The six seam operations are:

1. `listen(bind_addr, port)`: Creates an `AF_INET` streaming TCP socket, enables `SO_REUSEADDR`, binds to `(bind_addr, port)`, sets a backlog of 128, and returns the listening socket.
2. `accept(listener)`: Blocks on `listener.accept()` and returns `(conn, f"{host}:{port}")` for per-session identification and logging.
3. `connect(host, port)`: Creates an `AF_INET` streaming socket, connects to `(host, port)`, and returns the connected socket object.
4. `send_all(conn, data)`: Invokes `conn.sendall(data)` in a single call, guaranteeing that all bytes are transmitted or an exception is raised.
5. `recv_exact(conn, n)`: Loops calling `conn.recv(...)` until exactly `n` bytes have accumulated. If the stream closes before any bytes arrive, it raises `ConnectionClosed(clean=True)`. If it closes mid-stream, it raises `ConnectionClosed(clean=False)`.
6. `close(conn)`: Performs a graceful active shutdown by issuing `shutdown(SHUT_WR)`, setting a 1.0-second timeout, draining and discarding residual incoming bytes until EOF, and finally invoking `conn.close()`.

No file outside `src/transport_tcp.py` imports `socket` or calls any socket method. This is verified by running the course `seam_scan` tool, which yields zero violations.

**Swapping Transport in PA2**: When replacing TCP with the UDP-based ETP-T transport in PA2, the only modification needed is implementing the identical six operations in a new transport file (e.g. `src/transport_etpt.py`) and updating the single import line in `src/transport.py`. Neither `src/server.py`, `src/client.py`, nor `src/etp.py` will require any code changes, because all byte transfer and lifecycle calls flow strictly through the six seam functions.

---

## 3. Framing

ETP/1 operates over an unstructured byte stream. To read an ETP message without boundary ambiguity, the receiver reads in two discrete phases using `transport.recv_exact`:

1. **Fixed Header Phase**: Reads exactly 8 bytes (`etp.HEADER_SIZE`). `HEADER.unpack` parses `VERSION`, `TYPE`, `STATUS`, `RESERVED`, and `LENGTH` (network byte order, big-endian).
2. **Early Invariant Validation**: Before reading the payload or allocating memory, the code verifies:
   - `VERSION == 1`: If mismatched, returns fatal error `BAD_VERSION` (1) immediately.
   - `LENGTH <= MAX_LEN` ($16\,\text{MiB}$): If `LENGTH` exceeds $16\,\text{MiB}$, returns fatal error `TOO_LARGE` (5) immediately.
   This pre-payload check prevents malicious or corrupted clients from triggering multi-gigabyte memory allocations or denial-of-service hanging while waiting for nonexistent bytes.
3. **Payload Phase**: Once verified, `transport.recv_exact(conn, length)` is called to retrieve exactly `LENGTH` bytes.

**Framing Edge Cases**:
- *Fragmented Header*: If an 8-byte header arrives in multiple small TCP segments (e.g. 1 byte at a time), `recv_exact` maintains an internal `bytearray` buffer and continues calling `conn.recv()` until all 8 bytes have been read.
- *Coalesced Requests*: If a client transmits multiple requests in a single TCP write (e.g. `HELLO + LIST + GET + BYE`), the server loops: it reads 8 bytes, reads the exact payload, processes the request, sends the reply, and then immediately reads the next 8 header bytes from the remaining bytes in the TCP receive buffer.

---

## 4. Concurrency

The server uses a **multi-threaded concurrency model** (one worker thread per accepted session):

- In `src/server.py`, `main()` runs an infinite accept loop. When `transport.accept` returns a new connection, the server immediately constructs and starts a `threading.Thread(target=handle_session, args=(conn, peer, root), daemon=True)`.
- **Stalled Client Isolation**: Because each session runs in its own OS thread, a client that pauses or stalls mid-header or mid-payload only blocks its own worker thread in `recv_exact`. The main accept loop and all other client threads continue processing concurrently without latency.
- **Shared State & Protection**: The only shared state between threads is the server's root directory on the filesystem:
  - *Concurrent PUT and GET*: To prevent a concurrent `GET` from reading a partially-written file during a `PUT`, the server writes the uploaded payload into a temporary file whose name starts with a period (`.tmp_<thread_id>_<timestamp>`). Because valid ETP file names cannot start with a dot (Section 7), the temporary file is completely invisible to `LIST` and cannot be fetched via `GET`. Once the payload is flushed to disk, the server calls `os.replace` (atomic file rename) to swap the completed file into place.
  - *Concurrent PUT and PUT*: If two clients store the same file simultaneously, each writes to its own temporary file. The POSIX / OS filesystem atomic rename ensures that the last `os.replace` cleanly overwrites the destination without data corruption.
  - *Standard Output Synchronization*: Standard output logging is protected by a global `threading.Lock()` (`_log_lock`) so that log lines from concurrent sessions never interleave on the terminal.

---

## 5. Errors and disconnects

- **Fatal vs. Non-Fatal Errors**:
  - *Fatal Errors* (`BAD_VERSION`, `TOO_LARGE`, `NOT_READY`): The server encodes and transmits an `ERROR` response with the respective status code, breaks the session loop, and initiates an active close (`transport.close(conn)`).
  - *Non-Fatal Errors* (`BAD_TYPE`, `NOT_FOUND`, `BAD_NAME`, `BAD_REQUEST`, `SERVER_ERROR`): The server encodes and transmits the `ERROR` response. Crucially, the entire payload of the faulty request has already been consumed from the byte stream, keeping the connection synchronized. The session state is maintained, allowing the client to continue issuing requests or gracefully exit with `BYE`.
- **Abrupt Client Disconnects**: If a client abruptly closes, crashes, or sends a TCP RST during a transfer (such as in the middle of a 2 MiB `GET`), `transport.send_all` or `transport.recv_exact` catches `BrokenPipeError`, `ConnectionResetError`, or `transport.ConnectionClosed`. The session handler catches this exception, cleanly executes `transport.close(conn)` in its `finally:` block, and terminates only that session's thread. The main server process remains running.
- **Client Exit Codes**: The client selects its exit status according to Section 10 Table 3:
  - `0`: Command succeeded (`LIST_OK`, `GET_OK`, or matching `PUT_OK`).
  - `1`: Server returned an `ERROR` response (`mtype == 0xFF`). The code and error message are printed to `sys.stderr`.
  - `2`: Network or system failure (connection refused, stream terminated prematurely, invalid header field, local file I/O error, or invalid CLI parameters).
  - `3`: Integrity failure on `PUT` (the SHA-256 digest in `PUT_OK` did not match the local SHA-256 computation).

---

## 6. Threat model

An ETP/1 server operates on an unauthenticated, unencrypted TCP channel. Any on-path network observer can sniff traffic, inspect file contents, client identifiers, and directory listings, or perform active man-in-the-middle attacks to modify messages in transit.

- **Attack Resisted (Directory Traversal)**: The server strongly defends against directory traversal attacks (such as `GET ../../../etc/passwd` or `PUT ../secret`). In Section 7, all file names are strictly validated against `^[A-Za-z0-9_-][A-Za-z0-9._-]{0,63}\Z`. Any name containing a path separator (`/`), starting with a period (`.hidden`), or containing control characters is rejected with `BAD_NAME` before any filesystem path resolution occurs, ensuring file access cannot escape the designated root.
- **Attack Not Resisted (Denial of Service via Connection Exhaustion)**: Because the server spawns an unthrottled worker thread for every accepted connection and does not enforce a connection cap or an idle read timeout, a malicious client opening hundreds of simultaneous connections and stalling indefinitely could exhaust available file descriptors and system thread capacity.

---

## 7. Testing

In addition to running the course `etp_selfcheck.py` test suite, we built two automated test suites in `tests/`:

1. **`tests/test_server_mock_transport.py`**: An automated unit suite utilizing an in-memory duplex stream transport. This tests the complete protocol state machine, Section 8.1 check ordering, byte-by-byte fragment reassembly, request coalescing, and concurrent multi-client worker threads with stalled peers in a fast, isolated environment.
2. **`tests/test_client_mock_transport.py`**: Validates client behavior across all exit codes (0, 1, 2, 3), ensuring that on server errors the local destination file is never modified or created.

**Bug Found and Fixed**:
During initial server implementation, `0x42` (an unknown message type) was tested on a connection in the `AWAIT_HELLO` state. The initial code checked session state before message type, which caused the server to emit `NOT_READY` (fatal) and terminate the connection. However, Specification Section 5 and Section 8.1 mandate that header validation and unknown `TYPE` checking (Check 4) must precede the `AWAIT_HELLO` check (Check 5). The unknown type must be answered with `BAD_TYPE` (code 2, non-fatal), and the session must remain in `AWAIT_HELLO`. We fixed the check ordering in `handle_session` so that Check 4 validates `mtype in (HELLO, LIST, GET, PUT, BYE)` before Check 5 enforces `mtype == HELLO`, satisfying test S11.
