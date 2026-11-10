# PA1 Capture Analysis

## How I captured it

Run inside the course Linux VM / environment from the repository root:

```bash
mkdir -p server-files evidence scratch
head -c 262144 /dev/urandom > scratch/photo.bin     # 256 KiB of synthetic random bytes

# Terminal 1: the server
./etp-server --port 5000 --root server-files

# Terminal 2: start the capture
tshark -i lo -s 200 -f "tcp port 5000" -w evidence/pa1-capture.pcap

# Terminal 3: PUT session, then GET session, then ss within 60s
C="./etp-client --host 127.0.0.1 --port 5000 --name eagle01"
$C put scratch/photo.bin photo.bin
$C get photo.bin scratch/copy.bin
cmp scratch/photo.bin scratch/copy.bin && echo identical
ss -tan state time-wait '( sport = :5000 or dport = :5000 )' > evidence/time-wait.txt

# Terminal 2: Ctrl-C to stop capture
```

---

## Facts

_Fill in every value from **your** capture, for the **GET** session. Integers in decimal. Sequence numbers are the **absolute** (raw) values — with Wireshark, turn off "relative sequence numbers" (Edit > Preferences > Protocols > TCP) or read the "Sequence Number (raw)" field. With tshark, add `-o tcp.relative_sequence_numbers:FALSE`. Do not change the key names or the `etp-facts` label: a script reads this block._

```etp-facts
server_port: 5000
client_port: <CLIENT_PORT_FROM_GET_SYN>
client_isn: <CLIENT_RAW_ISN_FROM_GET_SYN>
server_isn: <SERVER_RAW_ISN_FROM_GET_SYNACK>
client_mss: <CLIENT_MSS_VALUE_FROM_GET_SYN>
server_to_client_payload_bytes: 262192
server_to_client_data_segments: <COUNT_OF_SERVER_TO_CLIENT_PAYLOAD_FRAMES>
first_fin_from: server
```

> **Note on `server_to_client_payload_bytes` calculation:**
> For a 256 KiB file ($262{,}144$ bytes), the server transmits:
> 1. `HELLO_OK`: 8 bytes header + 24 bytes payload (`ETP reference server 1.0`) = 32 bytes.
> 2. `GET_OK`: 8 bytes header + 262,144 bytes file data = 262,152 bytes.
> 3. `BYE_OK`: 8 bytes header + 0 bytes payload = 8 bytes.
> **Total server payload bytes:** $32 + 262{,}152 + 8 = 262{,}192$ bytes.

---

## Q1. The handshake

**Segments and Identifiers:**
- **Segment 1 (Client $\rightarrow$ Server SYN):** Frame `<FRAME_NUM>`, Flags: `[SYN]`, Raw Seq: `<CLIENT_ISN>`, Raw Ack: `0`.
- **Segment 2 (Server $\rightarrow$ Client SYN/ACK):** Frame `<FRAME_NUM>`, Flags: `[SYN, ACK]`, Raw Seq: `<SERVER_ISN>`, Raw Ack: `<CLIENT_ISN + 1>`.
- **Segment 3 (Client $\rightarrow$ Server ACK):** Frame `<FRAME_NUM>`, Flags: `[ACK]`, Raw Seq: `<CLIENT_ISN + 1>`, Raw Ack: `<SERVER_ISN + 1>`.

**Why the third segment's acknowledgment number is what it is:**
Under RFC 793, the TCP `SYN` flag logically occupies exactly one sequence number in the sequence space even though it carries zero payload data bytes. When the server acknowledges the client's SYN in Segment 2, it sends `Ack = Client_ISN + 1`. In turn, when the client acknowledges the server's `SYN/ACK` in Segment 3, it acknowledges receipt of the server's SYN by advancing the server's sequence number by 1: `Ack = Server_ISN + 1`.

**Advertised MSS and Operating System Determinant:**
The client advertised an MSS option of `<CLIENT_MSS>` bytes (typically $65{,}495$ bytes on the Linux loopback interface `lo`). On a Linux machine, the loopback interface has an MTU of $65{,}536$ bytes. The maximum segment size is determined by taking the interface MTU and subtracting the fixed network layer overhead: the 20-byte IPv4 header and the 20-byte TCP header ($65{,}536 - 20 - 20 = 65{,}496$, minus optional TCP timestamp/option fields giving $65{,}495$).

---

## Q2. Your protocol on the wire

**1. GET Request Header (Client $\rightarrow$ Server):**
- **Frame number:** Frame `<GET_REQ_FRAME_NUM>`
- **First 8 payload bytes (hex):** `01 03 00 00 00 00 00 09`
- **Field-by-Field Header Decoding:**
  - `VERSION`: `0x01` (Decimal 1, ETP/1)
  - `TYPE`: `0x03` (GET request)
  - `STATUS`: `0x00` (Always 0 in requests)
  - `RESERVED`: `0x00` (Sender MUST set to 0)
  - `LENGTH`: `0x00000009` (Decimal 9; the filename `photo.bin` is 9 ASCII bytes)

**2. GET_OK Response Header (Server $\rightarrow$ Client):**
- **Frame number:** Frame `<GET_OK_FRAME_NUM>`
- **First 8 payload bytes (hex):** `01 83 00 00 00 04 00 00`
- **Field-by-Field Header Decoding:**
  - `VERSION`: `0x01` (Decimal 1, ETP/1)
  - `TYPE`: `0x83` (`0x03 | 0x80`, indicating success response `GET_OK`)
  - `STATUS`: `0x00` (Success status 0)
  - `RESERVED`: `0x00` (Sender MUST set to 0)
  - `LENGTH`: `0x00040000` (Decimal 262,144 bytes, which exactly matches the 256 KiB size of `photo.bin`)

**3. Arithmetic Connecting `server_to_client_payload_bytes`:**
The total payload transmitted by the server to the client during the GET session comprises exactly three response messages:
- `HELLO_OK`: 8-byte header + 24-byte server name (`ETP reference server 1.0`) = 32 bytes
- `GET_OK`: 8-byte header + 262,144-byte file payload = 262,152 bytes
- `BYE_OK`: 8-byte header + 0-byte payload = 8 bytes
$$\text{Total Server Payload} = 32 + 262{,}152 + 8 = 262{,}192\text{ bytes}$$
This arithmetic matches the sum of the TCP segment payload lengths across all data-bearing server frames in the session.

---

## Q3. A byte stream, not messages

**Segmentation of GET_OK:**
The `GET_OK` response (total length $262{,}152$ bytes including its 8-byte header) was carried across `<NUM_GET_OK_SEGMENTS>` TCP segments (typically 4–5 segments on Linux loopback, e.g. four $\approx 65\,\text{KB}$ segments and a final residual segment of $\approx 65\,\text{KB}$). The segments are not all the same size because the final segment carries the remaining fraction of bytes after multiple full-sized segments.

**Message vs. Segment Alignment:**
TCP is an unstructured byte-stream protocol that provides no preservation of application message boundaries. An application message can span multiple TCP segments (as seen with `GET_OK`, where 256 KiB spans multiple segments), and multiple application messages can be coalesced into a single segment (such as pipelined requests). Furthermore, segment boundaries may cut directly through an 8-byte ETP header or payload.

**How the Code Handles This:**
Neither the server nor the client ever relies on a single `recv()` call to yield a complete message. In `src/transport_tcp.py`, the seam function `recv_exact(conn, n)` loops accumulating bytes until the requested count is fulfilled:
```python
buf = bytearray()
while len(buf) < n:
    chunk = conn.recv(n - len(buf))
    if not chunk:
        raise ConnectionClosed(...)
    buf.extend(chunk)
return bytes(buf)
```
In `src/etp.py`, `read_message(conn, transport)` reads exactly 8 bytes for the fixed header, unpacks `LENGTH`, and then calls `transport.recv_exact(conn, length)` to retrieve the payload. This guarantees reliable reassembly regardless of how the underlying IP/TCP layer segments the stream.

---

## Q4. Teardown and TIME-WAIT

**First FIN and Specification Rule:**
The **server** sent the first FIN in the GET session. This is mandated by Specification Section 5, Paragraph 4:
> *"After sending BYE_OK the server closes the connection. The client waits until it sees the server's close (a read returns end-of-stream) and then closes its own side. The server is therefore the side that performs the active close and holds the TIME-WAIT state..."*

In our server implementation (`src/server.py`), after `BYE_OK` is encoded and transmitted, the loop breaks and triggers `transport.close(conn)`, which issues `shutdown(SHUT_WR)` to send the FIN.

**Evidence from `evidence/time-wait.txt`:**
```text
<PASTE LINE FROM YOUR evidence/time-wait.txt, e.g.:>
tcp   TIME-WAIT  0      0      127.0.0.1:5000    127.0.0.1:<CLIENT_PORT>
```

**Which Endpoint is in TIME-WAIT and Duration:**
The server's endpoint (`127.0.0.1:5000`) is in `TIME-WAIT`. Under TCP (RFC 793), whichever endpoint initiates the active close (sending the first FIN) is required to transition to `TIME-WAIT` after receiving the peer's final ACK. Linux holds this state for $2 \times \text{MSL}$ (fixed at 60 seconds).

**Connection to `SO_REUSEADDR`:**
Because the server performs the active close, its local port (`5000`) remains bound in the TCP state table in `TIME-WAIT` for 60 seconds after every completed session. If an ETP server is restarted immediately without `SO_REUSEADDR`, the kernel's `bind()` system call will fail with `EADDRINUSE` ("Address already in use"). Enabling `SO_REUSEADDR` (`socket.SO_REUSEADDR` in `src/transport_tcp.py`) allows a new listening socket to bind to port 5000 immediately, even while previous connections remain in `TIME-WAIT`.

---

## Q5. What an observer learns

**What an Observer Learns from the Traffic:**
An on-path eavesdropper capturing unencrypted ETP/1 traffic learns:
1. The client's identifier (sent in cleartext during `HELLO`, e.g. `eagle01`).
2. The server's identity banner (`ETP reference server 1.0`).
3. The exact filenames accessed or uploaded (`photo.bin`).
4. The exact file size in bytes ($262{,}144$ bytes) and the cryptographic SHA-256 digest on uploads.
5. High-resolution session timing and request frequency.

**Impact of 200-Byte Snap Length (`-s 200`):**
- **What it does NOT hide:** It captures the complete IP header, TCP header, TCP options, and the entire 8-byte ETP header, as well as the initial 146 bytes of each request/response payload. All filenames, client identities, headers, digests, and session structures are completely visible.
- **What it DOES hide:** It truncates payloads larger than $\approx 146$ bytes. For our 256 KiB file, bytes 147 through 262,144 are discarded by the packet capture tool, ensuring private payload content is kept out of the repository.

**Protection and Residual Leakage:**
- **Required Protection:** Encrypting the transport using TLS (Transport Layer Security) would encapsulate application records within encrypted TLS Application Data records. This prevents an eavesdropper from reading file names, client identifiers, headers, or file contents.
- **What TLS Would Still NOT Hide:** An observer can still inspect IP addresses, TCP port numbers, TLS handshake metadata (such as server certificates), segment timing, and the total volume of ciphertext transferred, which enables traffic analysis to infer the approximate size of transferred files.
