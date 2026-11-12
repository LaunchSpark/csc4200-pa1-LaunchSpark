# AI Use Disclosure — PA1

## 1. Did you use generative AI on this assignment?

- [ ] No. I did not use any generative AI tool for any part of PA1.
- [x] Yes, as described below.

## 2. Statement (the syllabus form)

> The authors acknowledge the utilization of Claude (Opus 5.5 and 3.5 Sonnet) and Antigravity (Gemini), language models developed by Anthropic and Google DeepMind, in the preparation of this assignment. We employed these tools as technical assistants for reviewing socket error handling idioms, exploring bytearray stream accumulator patterns, drafting the initial Makefile, structuring unit test mocks, and verifying packet analysis interpretations against RFC 793. We maintained complete oversight of all protocol invariants, state machines, and evidence gathering.

## 3. Log

| # | What I asked (summary) | What I used from the answer | What I changed or rejected | How I checked it was right |
|---|---|---|---|---|
| 1 | I prompted the model for common accumulator idioms in Python for fixed-size socket reads (`recv_exact`), struct packing conventions, and thread dispatch patterns. | I adapted the basic bytearray accumulator pattern for chunked socket reads and the `!BBBBI` format string for 8-byte big-endian header serialization. | I rejected the proposed all-in-one read structure. I decoupled the 8-byte header read from payload extraction so I could evaluate Section 8.1 invariants (`VERSION == 1`, `LENGTH <= 16 MiB`) before allocating payload memory, protecting the server from memory exhaustion attacks. | I asserted byte-for-byte fidelity against the Specification Section 12 test vectors and confirmed passing status on tests S09 (fragmented requests) and S13 (oversized length rejection without memory allocation). |
| 2 | I asked the model to audit the repository structure against the assignment brief rubric to confirm all required files and capture prerequisites were identified. | I used its checklist of deliverables to verify that my live loopback capture, socket TIME-WAIT dump, and analysis sections aligned with the rubric. | I rejected any synthetic estimation for the analysis answers. I insisted on running the live Linux loopback capture first so that every metric in `etp-facts` and every explanation in Q1–Q5 derived strictly from my own Wireshark trace. | I executed `etp_selfcheck.py` in WSL, confirming that `check_evidence` verified 2 complete TCP connections, matched all 8 fact keys, and scored 30/30 execution points. |
| 3 | I consulted on git commands to cleanly merge my partner's branch into `main` without risking overwrites of our verified capture and analysis files. | I used the suggested command sequence to fetch, inspect diffs, and perform a fast-forward merge of upstream commits. | I rejected an automated rebase that would have rewritten commit timestamps, keeping the branch's verified versions of `DESIGN.md`, `README.md`, and `evidence/` authoritative. | I ran `git diff Documentation -- DESIGN.md README.md evidence/ src/ Makefile` confirming zero discrepancies, followed by `make check` verifying 30/30 execution and 10/10 repository points. |

## 4. Where AI-produced material remains

I wrote the protocol state machines, validation logic, and architectural designs across the repository. Material derived from AI suggestions remains strictly in structural boilerplate and low-level idioms:

- `src/transport_tcp.py`: I adapted the model's accumulator loop pattern for chunked reads in `recv_exact` and the socket shutdown/drain boilerplate in `close`. I authored the seam boundary and exception hierarchy (`ConnectionClosed(clean=...)`).
- `src/etp.py`: I adopted the standard `struct.Struct("!BBBBI")` format string for the 8-byte header. I personally authored the Section 7 regex filename validation (`valid_name`) and the Section 8.1 two-stage read logic in `read_message`.
- `src/server.py`: I adapted the basic `threading.Thread` dispatch skeleton and the ISO-8601 timestamp string formatting. I authored the entire Section 8.1 check pipeline, all state transitions (`AWAIT_HELLO` to `READY`), request handlers (`LIST`, `GET`, `PUT`, `BYE`), atomic temporary file replacement, and stdout logging synchronization.
- `src/client.py`: I used standard `argparse` scaffolding generated with AI assistance. I authored the complete client session lifecycle, stdout/stderr stream isolation, and strict exit code mapping (0, 1, 2, 3).
- `tests/`: I adapted the structural harness for mock in-memory transports in `tests/test_server_mock_transport.py` and `tests/test_client_mock_transport.py`, but wrote the specific protocol assertions and test vectors myself.

## 5. One thing the AI got wrong — or how you checked it

When implementing the server's session loop in `src/server.py`, the AI initially proposed checking the session state (`self.state == AWAIT_HELLO`) before validating the message type. When an unknown message type (e.g. `0x42`) was sent on a new connection prior to `HELLO`, this initial implementation returned `NOT_READY` (status 4, fatal) and closed the connection.

However, ETP/1 Specification Section 8.1 explicitly mandates the exact sequence of checks: Check 4 (unknown `TYPE`, which returns non-fatal `BAD_TYPE` and consumes the payload) must precede Check 5 (`AWAIT_HELLO`, which returns fatal `NOT_READY`). I caught this bug when running self-check test S11 (`unknown TYPE: BAD_TYPE, payload skipped`), which failed because the connection was aborted prematurely. I corrected the check order in `handle_session` so that Check 4 validates `mtype in (HELLO, LIST, GET, PUT, BYE)` and returns `BAD_TYPE` while keeping the session in `AWAIT_HELLO`, which allowed the client to recover and caused test S11 to pass.
