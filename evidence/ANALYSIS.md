# PA1 Capture Analysis

## How I captured it

Run inside the Linux environment from the repository root:

```bash
mkdir -p server-files evidence scratch
head -c 262144 /dev/urandom > scratch/photo.bin     # 256 KiB of synthetic random bytes

# Terminal 1: the server
./etp-server --port 5000 --root server-files

# Terminal 2: start the capture (snap length 200)
tcpdump -i lo -s 200 -U -w evidence/pa1-capture.pcap "tcp port 5000"

# Terminal 3: PUT session, then GET session, then ss within 60s
C="./etp-client --host 127.0.0.1 --port 5000 --name eagle01"
$C put scratch/photo.bin photo.bin
$C get photo.bin scratch/copy.bin
cmp scratch/photo.bin scratch/copy.bin && echo identical
ss -tan state time-wait '( sport = :5000 or dport = :5000 )' > evidence/time-wait.txt

# Terminal 2: Ctrl-C to stop capture
```

File transferred: `photo.bin`, exactly 262,144 bytes (256 KiB).

---

## Facts

```etp-facts
server_port: 5000
client_port: 35334
client_isn: 894495907
server_isn: 3864184826
client_mss: 65495
server_to_client_payload_bytes: 262192
server_to_client_data_segments: 11
first_fin_from: server
```

---

## Q1. The handshake

**Segments and Identifiers:**
- **Segment 1 (Client $\rightarrow$ Server SYN):** Frame 28, Flags: `[SYN]`, Raw Seq: `894495907`, Raw Ack: `0`.
- **Segment 2 (Server $\rightarrow$ Client SYN/ACK):** Frame 29, Flags: `[SYN, ACK]`, Raw Seq: `3864184826`, Raw Ack: `894495908`.
- **Segment 3 (Client $\rightarrow$ Server ACK):** Frame 30, Flags: `[ACK]`, Raw Seq: `894495908`, Raw Ack: `3864184827`.

**Why the third segment's acknowledgment number is what it is:**
Under RFC 793, the TCP `SYN` flag logically occupies exactly one sequence number in the sequence space even though it carries zero application payload bytes. In Segment 2, the server acknowledges the client's SYN (`894495907`) by sending `Ack = 894495908` ($894495907 + 1$). In turn, when the client acknowledges the server's SYN/ACK in Segment 3, it advances the server's Initial Sequence Number (`3864184826`) by 1:
$$\text{Ack} = \text{Server\_ISN} + 1 = 3864184826 + 1 = 3864184827$$

**Advertised MSS and Operating System Determinant:**
The client advertised an MSS option of `65495` bytes in its SYN packet (Frame 28). On Linux, the loopback interface (`lo`) has a default Maximum Transmission Unit (MTU) of 65,536 bytes ($2^{16}$). The MSS represents the maximum TCP payload size excluding IP and TCP headers:
$$\text{MSS} = \text{MTU} - 20\,(\text{IPv4 Header}) - 20\,(\text{TCP Header}) - 1\,(\text{TCP Options Padding}) = 65{,}495\text{ bytes}$$

---

## Q2. Your protocol on the wire

**1. GET Request Header (Client $\rightarrow$ Server):**
- **Frame number:** Frame 35
- **First 8 payload bytes (hex):** `01 03 00 00 00 00 00 09`
- **Field-by-Field Header Decoding:**
  - `VERSION`: `0x01` (Decimal 1, ETP/1)
  - `TYPE`: `0x03` (ETP request type GET)
  - `STATUS`: `0x00` (Must be 0 in requests)
  - `RESERVED`: `0x00` (Must be 0)
  - `LENGTH`: `0x00000009` (Decimal 9; corresponding to the 9 ASCII bytes of `"photo.bin"`)

**2. GET_OK Response Header (Server $\rightarrow$ Client):**
- **Frame number:** Frame 36
- **First 8 payload bytes (hex):** `01 83 00 00 00 04 00 00`
- **Field-by-Field Header Decoding:**
  - `VERSION`: `0x01` (Decimal 1, ETP/1)
  - `TYPE`: `0x83` (`0x03 | 0x80`, indicating success response `GET_OK`)
  - `STATUS`: `0x00` (Success status 0)
  - `RESERVED`: `0x00` (Must be 0)
  - `LENGTH`: `0x00040000` (Decimal 262,144 bytes, exactly matching the 256 KiB size of `photo.bin`)

**3. Arithmetic Connecting `server_to_client_payload_bytes`:**
The total payload transmitted by the server to the client during the GET session comprises exactly three response messages:
- `HELLO_OK` (Frame 33): 8-byte header + 24-byte server name (`ETP reference server 1.0`) = 32 bytes
- `GET_OK` (Frames 36, 37, 40, 41, 43, 44, 46, 47, 49): 8-byte header + 262,144 bytes data = 262,152 bytes
- `BYE_OK` (Frame 51): 8-byte header + 0-byte payload = 8 bytes
$$\text{Total Server Payload} = 32 + 262{,}152 + 8 = 262{,}192\text{ bytes}$$
This matches the sum of the payload lengths across all 11 server-to-client data segments in the session.

---

## Q3. A byte stream, not messages

**Segmentation of GET_OK:**
The `GET_OK` response (totaling 262,152 bytes) was carried across **9 TCP segments**:
- Frames 36, 37, 40, 41, 43, 44, 46, 47: each carried 32,768 bytes of TCP payload.
- Frame 49: carried the final residual 8 bytes of TCP payload ($8 \times 32{,}768 + 8 = 262{,}152\text{ bytes}$).
The segments were not all the same size due to the final 8-byte segment, and none of them reached the loopback MSS of 65,495 bytes because Linux TCP window buffering and socket write buffering split the output into 32 KiB chunks.

**Message vs. Segment Alignment:**
TCP delivers a continuous, unstructured byte stream with no application message boundaries. A single ETP message can span multiple TCP segments (here `GET_OK` spans 9 segments), or multiple ETP messages can be delivered in a single segment if sent back-to-back. Furthermore, a segment boundary can cut directly across an 8-byte ETP header or payload.

**How the Code Handles This:**
Neither server nor client assumes that a single `recv()` call returns a complete message.
- In `src/transport_tcp.py`, `recv_exact(conn, n)` loops accumulating bytes until exactly `n` bytes arrive:
  ```python
  buf = bytearray()
  while len(buf) < n:
      chunk = conn.recv(n - len(buf))
      if not chunk:
          raise ConnectionClosed(...)
      buf.extend(chunk)
  return bytes(buf)
  ```
- In `src/etp.py`, `read_message(conn, transport)` reads the 8-byte header first, unpacks `LENGTH`, and then calls `transport.recv_exact(conn, length)` to retrieve the payload. This guarantees reliable message framing regardless of segment fragmentation.

---

## Q4. Teardown and TIME-WAIT

**First FIN and Specification Rule:**
The **server** sent the first FIN in the GET session (Frame 52). This is required by Specification Section 5, Paragraph 4:
> *"After sending BYE_OK the server closes the connection. The client waits until it sees the server's close (a read returns end-of-stream) and then closes its own side. The server is therefore the side that performs the active close and holds the TIME-WAIT state..."*

In `src/server.py`, after sending `BYE_OK`, the server breaks its session loop and calls `transport.close(conn)`, which invokes `shutdown(socket.SHUT_WR)` to emit the initial FIN.

**Evidence from `evidence/time-wait.txt`:**
```text
Recv-Q Send-Q Local Address:Port Peer Address:Port Process
0      0          127.0.0.1:5000    127.0.0.1:35334       
```

**Which Endpoint is in TIME-WAIT and Duration:**
The server's endpoint (`127.0.0.1:5000`) is in `TIME-WAIT` connected to the client's port (`35334`). Under TCP, whichever side initiates the active close (sending the first FIN) must enter `TIME-WAIT` upon receiving the final ACK to absorb delayed duplicate segments. Linux maintains `TIME-WAIT` for $2 \times \text{MSL}$ (60 seconds).

**Connection to `SO_REUSEADDR`:**
Because the server holds port 5000 in `TIME-WAIT` for 60 seconds after closing, restarting the server immediately without `SO_REUSEADDR` would cause `bind()` to fail with `EADDRINUSE` ("Address already in use"). Enabling `SO_REUSEADDR` on the listening socket allows the server to bind port 5000 immediately even while previous connections linger in `TIME-WAIT`.

---

## Q5. What an observer learns

**What an Observer Learns from the Traffic:**
Because ETP/1 transmits all application bytes in cleartext over TCP, an observer sniffing the link learns:
1. Client identity: `"eagle01"` transmitted in the HELLO request.
2. Server identity: `"ETP reference server 1.0"` in HELLO_OK.
3. Filenames: `"photo.bin"` in the GET request.
4. Exact file length: 262,144 bytes ($0x00040000$) in the GET_OK header.
5. Exact transaction timestamps and round-trip latencies.

**Impact of 200-Byte Snap Length (`-s 200`):**
- **What it does NOT hide:** It captures the complete IP and TCP headers, TCP options, the entire 8-byte ETP message headers, and the first 146 bytes of application payload. All protocol commands, names, digests, and session structures remain visible.
- **What it DOES hide:** It discards payload bytes beyond the initial 146 bytes. For `photo.bin`, bytes 147 through 262,144 are truncated, ensuring proprietary file contents are kept out of the repository.

**Protection and Residual Leakage:**
- **Required Protection:** Wrapping the transport in TLS (Transport Layer Security) would encrypt all record payloads, hiding file names, message types, and file data from passive eavesdroppers.
- **What TLS Would Still NOT Hide:** An observer could still inspect the IP addresses, TCP port numbers, TLS handshake packet lengths, segment timing, and the total volume of encrypted ciphertext ($262\,\text{KB}$), enabling traffic analysis to infer file size and access patterns.
