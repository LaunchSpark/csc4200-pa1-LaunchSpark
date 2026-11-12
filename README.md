# PA1 — ETP/1 Client and Server

**Student:** Lucas Starkey (`LaunchSpark`)
**Course:** CSC 4200 — Fall 2026
**Language:** Python
**Submission commit:** After the final edits are committed and pushed, run `git rev-parse HEAD` and paste that full SHA into Canvas.

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
  The bundled, unmodified checker is at `tests/course/etp_selfcheck.py`.

### Evidence verification

The evidence was recollected on November 10, 2026 in a local Docker Linux
container, using the automation disclosed in `AI_USE.md`. The full command
trace, environment, packet capture, file sizes/hashes, and TIME-WAIT output
are retained in `evidence/`. See `evidence/ANALYSIS.md` for measured results.

To verify the capture against the retained source, server copy, and download:

```bash
python3 tests/evidence/verify.py --evidence evidence --analysis evidence/ANALYSIS.md
```

The random files remain in ignored `scratch/` and `server-files/` directories;
this command requires those local fixtures. A fresh clone can inspect the
recorded hashes and logs, or recollect a new run using
`tests/evidence/README.md`. Each new capture requires updated analysis facts.

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
| `evidence/ANALYSIS.md` | Packet capture measurements and corrected Q1–Q5 answers |
| `evidence/integrity.txt` | Successful byte comparisons, exact sizes, and matching SHA-256 hashes |
| `evidence/verification.json` | Strict verification of both sessions, captured file bytes, and analysis facts |
| `tests/evidence/` | Reproducible Linux capture workflow and evidence verifier |
| `tests/course/etp_selfcheck.py` | Unmodified course checker, kept with test tooling |

---

## Authorship statement

I am the author of this submission. Except where this README or `AI_USE.md`
says otherwise, I wrote, or rewrote and understand, every part of it — code,
documents and evidence — and I can explain any line of it to the instructor or
GTA. I am responsible for its correctness, including any part a
generative AI tool helped me produce. My use of AI tools is disclosed in full in
`AI_USE.md`. The capture and measurements in `evidence/` come from this repository's
programs, run through the containerized collection workflow disclosed there.

**Signed:** Lucas Starkey  **Date:** November 12, 2026
