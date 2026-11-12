# PA1 Capture Analysis

## How the evidence was collected

This evidence was recollected on November 10, 2026 at approximately **23:06:47 UTC (17:06:47 America/Chicago)** by Codex running the repository's client and server at the user's request. See `AI_USE.md` for the automation and writing assistance disclosure. The previous capture was replaced; every frame number below refers to this new run.

The environment was an isolated Docker Linux network namespace on the local Mac: Linux `6.10.14-linuxkit`, Alpine Linux 3.24.2, Python 3.14.10, tcpdump 4.99.6, and loopback MTU 65,536. The image, package inventory, source hashes, route, and interface settings are recorded in `container-image.txt` and `environment.txt`.

From the repository root, the exact collection entry points were:

```bash
docker build -t networkingp1-evidence:local -f tests/evidence/Dockerfile .
docker run --rm --name networkingp1-evidence-capture --network none \
  --mount "type=bind,source=$PWD,target=/workspace" \
  networkingp1-evidence:local bash tests/evidence/collect.sh
```

The checked-in collection script records its command trace in `collection.log`. Its transfer/capture commands were:

```bash
head -c 262144 /dev/urandom > scratch/photo.bin
./etp-server --port 5000 --root server-files
tcpdump -i lo -s 200 -U -w scratch/evidence-run/pa1-capture.pcap 'tcp port 5000'
./etp-client --host 127.0.0.1 --port 5000 --name eagle01 put scratch/photo.bin photo.bin
./etp-client --host 127.0.0.1 --port 5000 --name eagle01 get photo.bin scratch/copy.bin
ss -tan state time-wait '( sport = :5000 or dport = :5000 )'
ss -tano state time-wait '( sport = :5000 or dport = :5000 )'
cmp scratch/photo.bin scratch/copy.bin
cmp scratch/photo.bin server-files/photo.bin
wc -c scratch/photo.bin server-files/photo.bin scratch/copy.bin
sha256sum scratch/photo.bin server-files/photo.bin scratch/copy.bin
```

The script starts the server and tcpdump in the background, waits for each to be ready, saves both `ss` outputs immediately after GET, then stops tcpdump with SIGINT after a one-second drain interval. It stages files in `scratch/evidence-run/` and validates them before they are copied into `evidence/`. No full random file is committed.

`integrity.txt` records both successful `cmp` comparisons and all three file sizes as **262,144 bytes (256 KiB)**. Source, server copy, downloaded copy, and the PUT response's digest all agree on SHA-256:

```text
8e345f92d5faa9ebf77888860a10d6d3e8ee378ee93990cac1a795039bcc4973
```

`pa1-capture.pcap` is 5,619 bytes, snaplen 200, with 46 frames. PUT uses client port 50488 (frames 1–23); GET uses port 50498 (frames 24–46). `tcpdump.log` records zero packets dropped by the kernel. The verifier checks complete handshakes, continuous sequence ranges, both FINs and final ACKs, and every captured application byte against the expected protocol stream and retained random files. A truncated capture alone cannot establish whole-file equality; the actual files, `cmp`, and matching hashes supply that check.

## Facts

All sequence numbers below are raw, absolute 32-bit values for the GET session.

```etp-facts
server_port: 5000
client_port: 50498
client_isn: 4184521090
server_isn: 2674872784
client_mss: 65495
server_to_client_payload_bytes: 262192
server_to_client_data_segments: 8
first_fin_from: server
```

## Q1. The handshake

| Frame | Direction | Flags | Raw sequence | Raw acknowledgment |
|---|---|---|---:|---:|
| 24 | Client → server | SYN | 4184521090 | 0 (ACK flag unset) |
| 25 | Server → client | SYN, ACK | 2674872784 | 4184521091 |
| 26 | Client → server | ACK | 4184521091 | 2674872785 |

The third segment acknowledges `server_isn + 1 = 2674872784 + 1 = 2674872785`. SYN consumes one sequence number even though it contains no application data. Likewise, frame 25 acknowledges the client's ISN plus one.

The client SYN advertises **MSS 65,495**. `environment.txt` records loopback MTU **65,536**. For IPv4, Linux caps the advertised size using the 65,535-byte IPv4 packet-length limit, then subtracts the fixed 20-byte IPv4 and 20-byte TCP headers: `min(65536, 65535) − 20 − 20 = 65495`. The extra byte is due to that IPv4 size limit, not TCP-option padding. The Linux `ipv4_default_advmss` implementation applies this cap. TCP options reduce the payload available in an actual segment, not the advertised MSS value. See [Linux v6.10 route.c](https://github.com/torvalds/linux/blob/v6.10/net/ipv4/route.c) and [RFC 9293 §3.7.1](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.7.1).

## Q2. The protocol on the wire

The GET request is in **frame 31**, with first eight TCP payload bytes:

```text
01 03 00 00 00 00 00 09
```

| Field | Value | Meaning |
|---|---|---|
| VERSION | `01` | ETP/1 |
| TYPE | `03` | GET |
| STATUS | `00` | Request status zero |
| RESERVED | `00` | Reserved byte zero |
| LENGTH | `00 00 00 09` | Nine filename bytes: `photo.bin` |

GET_OK begins in **frame 32**, with header:

```text
01 83 00 00 00 04 00 00
```

VERSION is 1, TYPE is `0x83` (GET_OK), STATUS and RESERVED are zero, and the big-endian LENGTH is `0x00040000 = 262144`. This matches all three measured on-disk file sizes in `integrity.txt`.

The server's GET-session payload is:

| Message | Frames | Header + body | TCP payload bytes |
|---|---|---|---:|
| HELLO_OK | 29 | 8 + 24 (`ETP reference server 1.0`) | 32 |
| GET_OK | 32, 33, 35, 37, 38, 40 | 8 + 262144 | 262152 |
| BYE_OK | 43 | 8 + 0 | 8 |
| Total | Eight server data segments | 32 + 262152 + 8 | **262192** |

There are no retransmissions or gaps in the captured sequence ranges, so this sum does not double-count retransmitted bytes.

## Q3. A byte stream, not messages

GET_OK spans **six captured TCP segments**, excluding HELLO_OK and BYE_OK:

| Frame | TCP payload bytes | GET_OK stream offset (zero-based) |
|---|---:|---:|
| 32 | 32768 | 0 |
| 33 | 32768 | 32768 |
| 35 | 61952 | 65536 |
| 37 | 47424 | 127488 |
| 38 | 47424 | 174912 |
| 40 | 39816 | 222336 |
| Total | **262152** | |

These lengths come from the IP/TCP headers and sequence ranges; snaplen does not reduce the original payload lengths. The largest is 61,952 bytes, below the advertised MSS of 65,495 and the recorded loopback MTU. TCP buffering, flow control, and loopback offload behavior can influence packetization, but the capture does not isolate which mechanism selected these sizes.

GET_OK begins at a segment boundary in this run but extends across six segments. TCP provides an ordered byte stream, so applications cannot rely on packet boundaries to delimit messages: a read can return only part of a header or body, and consecutive messages can arrive together.

`recv_exact` in `src/transport_tcp.py` repeatedly calls `conn.recv(n - len(buf))`, appends each chunk, and returns only after collecting exactly `n` bytes; it raises `ConnectionClosed` on premature EOF. `read_message` in `src/etp.py` first requests the eight-byte header, decodes LENGTH, and then requests exactly that many body bytes. This reconstructs messages independently of how TCP segments or individual reads divide the stream.

## Q4. Teardown and TIME-WAIT

The server sends BYE_OK in **frame 43**, then the first FIN in **frame 44**. The client sends FIN+ACK in **frame 45**, and the server sends the final ACK in **frame 46**. This follows the server-active-close behavior referenced in ETP/1 Specification §5; the local code sends BYE_OK, exits its session loop, and calls `transport.close`. The specification PDF was not available in this checkout, so no verbatim quotation is asserted here.

| Frame | Direction | Flags | Raw sequence | Raw acknowledgment |
|---|---|---|---:|---:|
| 44 | Server → client | FIN, ACK | 2675134977 | 4184521131 |
| 45 | Client → server | FIN, ACK | 4184521131 | 2675134978 |
| 46 | Server → client | ACK | 2675134978 | 4184521132 |

The server receives the client's FIN and acknowledges it, entering TIME-WAIT. It **sends** the final ACK in this exchange. TIME-WAIT allows the endpoint to acknowledge a retransmitted FIN and lets old duplicate segments expire. See [RFC 9293 §3.6](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.6).

The actual `ss -tan state time-wait` output is:

```text
Recv-Q Send-Q Local Address:Port Peer Address:Port
0      0          127.0.0.1:5000    127.0.0.1:50498
0      0          127.0.0.1:5000    127.0.0.1:50488
```

The local endpoint is the server, `127.0.0.1:5000`, for both sessions. The timestamp immediately before running `ss` is **0.014337 seconds after the GET's final captured ACK**. `time-wait-timers.txt` also records `timer:(timewait,59sec,0)` for both connections, consistent with Linux's approximately 60-second TIME-WAIT interval.

The old connections can retain the local address/port after the listener exits, preventing an immediate bind without the appropriate reuse option. `listen` in `src/transport_tcp.py` sets `SO_REUSEADDR` before `bind`, allowing the listener to restart while old connections remain in TIME-WAIT. The course S18 restart test checks this behavior.

## Q5. What an observer learns

ETP/1 is cleartext. The captured bytes expose client name `eagle01`, server name `ETP reference server 1.0`, filename `photo.bin`, operation types, the exact 262,144-byte file size, and the PUT SHA-256 digest. An on-path observer can also observe endpoints, transaction timing, and estimate RTT from packet/ACK timing. Full packet access would reveal all file contents; the saved capture retains selected portions.

Snaplen 200 applies **to each captured frame**, including link and network headers. Each large data frame here has a 14-byte Ethernet header, 20-byte IPv4 header, and 32-byte TCP header including timestamp options. Thus it retains `200 − 14 − 20 − 32 = 134` TCP payload bytes. In frame 32, eight are the GET_OK header, leaving **126 file bytes**. Frame 33 exposes 134 file bytes beginning at file offset `32768 − 8 = 32760`; later segments expose prefixes at still later offsets. Truncation removes each frame's tail rather than hiding everything after one initial file prefix. The short protocol messages in this capture fit completely within snaplen.

TLS 1.3 with authenticated peer verification would encrypt the ETP messages, protecting names and file contents. Its authenticated encryption (AEAD) also detects tampering or forged records before plaintext is accepted, providing integrity as well as confidentiality. ETP's unkeyed SHA-256 digest alone does not authenticate a peer or stop an active attacker from replacing both data and digest. TLS still exposes IP endpoints, ports, packet timing, direction, and ciphertext lengths, allowing estimates of transfer volume. See [RFC 8446 §1](https://www.rfc-editor.org/rfc/rfc8446.html#section-1) and [§5.2](https://www.rfc-editor.org/rfc/rfc8446.html#section-5.2).

## Rechecking this evidence

From the repository root while the ignored random fixtures are retained:

```bash
python3 tests/evidence/verify.py --evidence evidence --analysis evidence/ANALYSIS.md
python3 tests/course/etp_selfcheck.py -v
```

`verification.json` records the strict evidence check, including the capture hash and all measured frame/sequence information. `selfcheck.txt` and `selfcheck.json` record the course check. Future recollections will have different random bytes, ports, ISNs, timestamps, and possibly segment sizes; update this analysis to their measured values before replacing the submitted evidence.
