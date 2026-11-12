# AI Use Disclosure — PA1

_Generative AI is allowed on PA1 as a tutor, reviewer, debugging partner and
helper with tooling. It is not allowed to be the author of your work. See the PA1
brief, "AI, Authorship and You". Fill in every section. "None" is an acceptable
answer only if it is true._

## 1. Did you use generative AI on this assignment?

- [ ] No. I did not use any generative AI tool for any part of PA1.
- [x] Yes, as described below.

## 2. Statement (the syllabus form)

> The author acknowledges the utilization of Claude (Opus 5.5 and 3.5 Sonnet) and Antigravity (Gemini), language models developed by Anthropic and Google DeepMind, in the preparation of this assignment. These tools were employed in the following manner(s) within this assignment: explaining socket errors; reviewing and verifying ETP/1 framing code; drafting the Makefile; suggesting test cases and building in-memory mock transports; structuring DESIGN.md and ANALYSIS.md; and reviewing loopback packet capture analysis against RFC 793.

## 3. Log

_One row per substantive interaction. Summaries are fine; you do not need to paste
whole conversations, but keep them in case you are asked._

| # | What I asked (summary) | What I used from the answer | What I changed or rejected | How I checked it was right |
|---|---|---|---|---|
| 1 | Implementing the transport seam over TCP (`src/transport_tcp.py`) and handling fragmented byte stream reads in `recv_exact`. | The loop structure for `recv_exact` accumulating bytes into a bytearray, and graceful `close` using `shutdown(SHUT_WR)` followed by drain. | Adapted socket exception handling to raise a custom `ConnectionClosed` exception with a `clean` boolean flag rather than raw `OSError`. | Verified against Figures 5.6–5.8 in course readings and validated with unit tests simulating 1-byte fragmented reads. |
| 2 | Binary framing and message deserialization (`src/etp.py`) using Python `struct.Struct("!BBBBI")` and filename regex validation. | Big-endian struct packing/unpacking patterns and regex `^[A-Za-z0-9_-][A-Za-z0-9._-]{0,63}\Z` for filename validation. | Separated header parsing from payload reading to enforce early invariant checks (`VERSION == 1`, `LENGTH <= 16 MiB`) before allocating payload memory. | Tested binary encodings against the ETP/1 Specification §12 test vector table and confirmed with test S13. |
| 3 | Multi-threaded concurrency model and atomic file operations for `PUT` and `GET` in `src/server.py`. | One worker thread per accepted session (daemon threads) and writing uploads to temporary files before calling `os.replace`. | Added a mutex (`threading.Lock`) around terminal stdout logging to prevent interleaved log lines from concurrent sessions. | Ran self-check test S16 (8 active clients served while 2 stall mid-message) and tested concurrent file overwrites. |
| 4 | Order of checks under Specification §8.1 and handling of non-fatal vs. fatal errors. | The mapping of protocol invariants to status codes (1 to 7) and error response formatting. | Rejected the AI's initial check order which checked `AWAIT_HELLO` before `TYPE`; reordered so Check 4 validates `TYPE` before Check 5 enforces `HELLO`. | Tested against Specification §5 and §8.1; verified with self-check test S11 (`unknown TYPE: BAD_TYPE, payload skipped`). |
| 5 | Wire capture analysis for `evidence/ANALYSIS.md` (interpreting loopback capture, sequence numbers, and MTU/MSS math). | RFC 793 explanations for why SYN consumes 1 sequence number, MTU-to-MSS subtraction on Linux loopback, and segment breakdown of `GET_OK`. | Verified every raw sequence number, port, frame number, and byte count directly from our actual `pa1-capture.pcap` file rather than accepting model estimations. | Executed `etp_selfcheck.py` and a verification script confirming an exact 8/8 match for all fields in `etp-facts`. |

## 4. Where AI-produced material remains

_List each file and function (or document section) that still contains code or
text an AI tool generated, even after you edited it. If none, say none._

- `src/transport_tcp.py`: The `recv_exact` loop structure and socket shutdown/close sequence.
- `src/etp.py`: The `HEADER` struct formatting string and `read_message` framing function.
- `src/server.py`: The session dispatch skeleton, Section 8.1 error response mapping, and stdout log line formatter.
- `src/client.py`: The CLI argument parsing skeleton and exit code handling.
- `tests/test_server_mock_transport.py` and `tests/test_client_mock_transport.py`: Mock in-memory transport harness and test cases.
- `DESIGN.md`: Architecture diagram and initial drafts of sections 1–7 (reviewed and verified against implementation).
- `evidence/ANALYSIS.md`: Explanatory phrasing in questions Q1–Q5 (all numerical facts and decoded hex were extracted directly from our actual capture file).

## 5. One thing the AI got wrong — or how you checked it

_Describe one answer, suggestion or piece of code that was wrong, misleading or
did not fit the specification, and how you caught it. If you found nothing wrong,
say so and describe how you checked (a test you ran, the part of the
specification you compared it with). If you did not use AI, describe one thing
you got wrong yourself and how you caught it._

When implementing the server's session loop in `src/server.py`, the AI initially proposed checking the session state (`self.state == AWAIT_HELLO`) before validating the message type. When an unknown message type (e.g. `0x42`) was sent on a new connection prior to `HELLO`, this initial implementation returned `NOT_READY` (status 4, fatal) and closed the connection.

However, ETP/1 Specification Section 8.1 explicitly mandates the exact sequence of checks: Check 4 (unknown `TYPE`, which returns non-fatal `BAD_TYPE` and consumes the payload) must precede Check 5 (`AWAIT_HELLO`, which returns fatal `NOT_READY`). I caught this bug when running self-check test S11 (`unknown TYPE: BAD_TYPE, payload skipped`), which failed because the connection was aborted prematurely. I corrected the check order in `handle_session` so that Check 4 validates `mtype in (HELLO, LIST, GET, PUT, BYE)` and returns `BAD_TYPE` while keeping the session in `AWAIT_HELLO`, which allowed the client to recover and caused test S11 to pass.
