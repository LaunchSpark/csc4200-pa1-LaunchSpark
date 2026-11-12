# AI Use Disclosure — PA1

_Generative AI is allowed on PA1 as a tutor, reviewer, debugging partner and
helper with tooling. It is not allowed to be the author of your work. See the PA1
brief, "AI, Authorship and You". Fill in every section. "None" is an acceptable
answer only if it is true._

## 1. Did you use generative AI on this assignment?

- [ ] No. I did not use any generative AI tool for any part of PA1.
- [x] Yes, as described below.

## 2. Statement (the syllabus form)

> The author acknowledges the utilization of Claude (Opus 5.5 and 3.5 Sonnet) and Antigravity (Gemini), language models developed by Anthropic and Google DeepMind, in the preparation of this assignment. These tools were employed in the following manner(s) within this assignment: explaining socket errors; reviewing and verifying ETP/1 framing code; drafting the Makefile; suggesting test cases and building in-memory mock transports; and reviewing loopback packet capture analysis against RFC 793.

## 3. Log

| # | What I asked (summary) | What I used from the answer | What I changed or rejected | How I checked it was right |
|---|---|---|---|---|
| 1 | Implementing ETP/1 framing, the transport seam over TCP, and the multi-threaded server subsystem. | The loop structure for `recv_exact` accumulating bytes into a bytearray, big-endian header packing (`struct.Struct("!BBBBI")`), and spawning daemon worker threads per accepted session. | Separated header parsing from payload reading to enforce early invariant checks (`VERSION == 1`, `LENGTH <= 16 MiB`) before allocating payload memory, avoiding DoS vulnerabilities. | Compared byte output against Specification §12 test vectors and verified against in-memory unit tests and self-check tests S01–S18. |
| 2 | Auditing the repository against the PA1 brief, rubric, and self-check suite. | A prioritized gap analysis identifying what was implemented (server, client, seam) versus what remained (live packet capture, TIME-WAIT output, ANALYSIS.md facts/questions, DESIGN.md). | Prioritized running the live Linux loopback capture first so that wire numbers could ground the analysis questions in real data rather than synthetic guesses. | Ran `project/etp_selfcheck.py` in WSL, confirming 30/30 execution points and verifying file structure against the starter kit. |
| 3 | Reconciling diverged branch histories. | Git merge strategy and tree verification commands to integrate diverged commits from `origin/main` without overwriting documentation or evidence. | Retained `Documentation` branch versions of `DESIGN.md`, `README.md`, `evidence/ANALYSIS.md`, and `evidence/pa1-capture.pcap` as authoritative over upstream stubs. | Executed `git diff Documentation -- DESIGN.md README.md evidence/ src/ Makefile` (confirming 0 diff) and ran `make build` and `etp_selfcheck.py` in WSL (confirming 30/30 pts). |

## 4. Where AI-produced material remains
- `src/transport_tcp.py`: The `recv_exact` loop structure and socket shutdown/close sequence.
- `src/etp.py`: The `HEADER` struct formatting string and `read_message` framing function.
- `src/server.py`: The session dispatch skeleton, Section 8.1 error response mapping, and stdout log line formatter.
- `src/client.py`: The CLI argument parsing skeleton and exit code handling.
- `tests/test_server_mock_transport.py` and `tests/test_client_mock_transport.py`: Mock in-memory transport harness and test cases.

## 5. One thing the AI got wrong — or how you checked it

When implementing the server's session loop in `src/server.py`, the AI initially proposed checking the session state (`self.state == AWAIT_HELLO`) before validating the message type. When an unknown message type (e.g. `0x42`) was sent on a new connection prior to `HELLO`, this initial implementation returned `NOT_READY` (status 4, fatal) and closed the connection.

However, ETP/1 Specification Section 8.1 explicitly mandates the exact sequence of checks: Check 4 (unknown `TYPE`, which returns non-fatal `BAD_TYPE` and consumes the payload) must precede Check 5 (`AWAIT_HELLO`, which returns fatal `NOT_READY`). I caught this bug when running self-check test S11 (`unknown TYPE: BAD_TYPE, payload skipped`), which failed because the connection was aborted prematurely. I corrected the check order in `handle_session` so that Check 4 validates `mtype in (HELLO, LIST, GET, PUT, BYE)` and returns `BAD_TYPE` while keeping the session in `AWAIT_HELLO`, which allowed the client to recover and caused test S11 to pass.
