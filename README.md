# PA1 — ETP/1 Client and Server

**Student:** Trey Gannod (`LaunchSpark` / `tgannod42`)
**Course:** CSC 4200 — Fall 2026
**Language:** Python
**Submitted commit:** _the SHA you paste into Canvas_

## Build and run

```bash
make build
make run-server PORT=5000 ROOT=server-files      # in one terminal
./etp-client --host 127.0.0.1 --port 5000 --name eagle01 list    # in another
```

### Requirements & Testing
- Requires **Python 3.10+** (Python Standard Library only; no external package dependencies).
- To run the unit tests:
  ```bash
  python3 -m unittest discover -s tests
  ```
- To run the official course self-check:
  ```bash
  make check
  ```

## What works and what does not

All execution requirements are implemented and passing:
- **Server execution (S01–S18)**:
  - S01: HELLO handshake and HELLO_OK format.
  - S02: Directory listing with raw byte sorting and filtering (skips hidden files, subdirectories, and symlinks).
  - S03–S04: Small and 2 MiB file GET transfers.
  - S05–S06: Large (300 KB) and empty PUT/GET transfers with SHA-256 digest validation.
  - S07–S08: Non-fatal `NOT_FOUND` and `BAD_NAME` handling preventing path traversal.
  - S09–S10: Byte-by-byte fragment reassembly and multi-request coalesced reads.
  - S11: Unknown request type handled non-fatally with payload consumed.
  - S12–S14: Fatal error handling (`BAD_VERSION`, `TOO_LARGE` without allocating, `NOT_READY`).
  - S15: Graceful `BYE` active close holding TIME-WAIT.
  - S16: Concurrency serving 8 active clients while 2 other clients stall mid-message.
  - S17: Resilience to abrupt client resets mid-stream.
  - S18: Server immediate restart using `SO_REUSEADDR`.
- **Client execution (C01–C05)**:
  - C01: Fragmented list output written to stdout exactly.
  - C02: Large file GET saved to local file.
  - C03: PUT payload layout and 64-hex-digit digest output.
  - C04: Server ERROR handling exiting with code 1 and stderr message without touching local file.
  - C05: Digest mismatch detection exiting with code 3.
  - C06: Connection failure exiting with code 2.
- **Transport Seam**: Zero socket API calls outside `transport*` files (verified with `seam_scan`).

Known limitations: None within the protocol specification.

## Files

| File | What it is |
|---|---|
| `src/server.py` | Multi-threaded ETP/1 server session handler and accept loop |
| `src/client.py` | ETP/1 client CLI commands (`list`, `get`, `put`) and exit code handling |
| `src/etp.py` | Binary framing encoder, decoder, and file name validation |
| `src/transport.py` | Transport seam module selector |
| `src/transport_tcp.py` | TCP socket wrapper providing the six transport seam primitives |
| `tests/test_server_mock_transport.py` | In-memory transport unit test suite for server S01–S17 |
| `tests/test_client_mock_transport.py` | In-memory transport unit test suite for client C01–C06 |
| `tests/test_server.py` | OS loopback socket test suite for server S01–S18 |
| `tests/test_spec.py` | ETP/1 wire vector and specification compliance unit tests |
| `DESIGN.md` | Design document covering architecture, seam, framing, concurrency, and security |
| `AI_USE.md` | AI-use disclosure and interaction log |
| `evidence/pa1-capture.pcap` | Loopback packet capture of PUT and GET sessions |
| `evidence/time-wait.txt` | `ss` command output verifying server-side TIME-WAIT state |
| `evidence/ANALYSIS.md` | Wireshark/tshark packet capture analysis and Q1–Q5 answers |

---

## Authorship statement

I am the author of this submission. Except where this README or `AI_USE.md`
says otherwise, I wrote, or rewrote and understand, every part of it — code,
documents and evidence — and I can explain any line of it to the instructor or
GTA. I am responsible for its correctness, including any part a
generative AI tool helped me produce. My use of AI tools is disclosed in full in
`AI_USE.md`. The capture and measurements in `evidence/` come from my own programs,
run by me.

**Signed:** Trey Gannod  **Date:** November 10, 2026
