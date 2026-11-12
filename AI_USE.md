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
| 1 | *"I need to handle the issue in the github. Help me accomplish this..."* — Implementing ETP/1 framing, the transport seam over TCP, and the multi-threaded server subsystem. | The loop structure for `recv_exact` accumulating bytes into a bytearray, big-endian header packing (`struct.Struct("!BBBBI")`), and spawning daemon worker threads per accepted session. | Separated header parsing from payload reading to enforce early invariant checks (`VERSION == 1`, `LENGTH <= 16 MiB`) before allocating payload memory, avoiding DoS vulnerabilities. | Compared byte output against Specification §12 test vectors and verified against in-memory unit tests and self-check tests S01–S18. |
| 2 | *"Can you evaluate the repo based on this criteria and let me know if anything is missing or errant?"* — Auditing the repository against the PA1 brief, rubric, and self-check suite. | A prioritized gap analysis identifying what was implemented (server, client, seam) versus what remained (live packet capture, TIME-WAIT output, ANALYSIS.md facts/questions, DESIGN.md). | Prioritized running the live Linux loopback capture first so that wire numbers could ground the analysis questions in real data rather than synthetic guesses. | Ran `project/etp_selfcheck.py` in WSL, confirming 30/30 execution points and verifying file structure against the starter kit. |
| 3 | *"Can you do the evidence checklist?"* — Capturing PUT and GET sessions under loopback, verifying file integrity, and recording TIME-WAIT. | Workflow for running `tcpdump -i lo -s 200` with port filtering, executing client PUT then GET of a 256 KiB binary, and running `ss -tan state time-wait` within 60s. | Generated a 256 KiB synthetic file (`photo.bin`) from `/dev/urandom` in `scratch/` rather than committing raw binary files to git. | Ran `cmp` confirming byte-for-byte file identity, inspected `pa1-capture.pcap` with `read_capture()`, and confirmed server port 5000 in TIME-WAIT with client ports 35320 and 35334. |
| 4 | *"Can you finish up the documentation except for the AI md? I'll do that on my own"* — Extracting PCAP facts and answering questions Q1–Q5 in `ANALYSIS.md`. | RFC 793 explanations for ISN sequence consumption, loopback MTU-to-MSS derivation ($65536 - 40 - 1 = 65495$), and segment breakdown of the 262,152-byte `GET_OK` response. | Extracted all 8 numerical values directly from our actual PCAP file (ports 5000/35334, ISNs `894495907` / `3864184826`, 11 segments, 262,192 bytes) rather than model approximations. | Wrote an automated verification script calling `etp_selfcheck.py`'s parser, confirming an exact 8/8 match for all fields in `etp-facts`. |
| 5 | Structuring and drafting the 7-section design document (`DESIGN.md`) covering architecture, seam, framing, concurrency, error handling, threat model, and testing. | Explanations of how atomic temporary file replacement (`.tmp_...` + `os.replace`) prevents race conditions between concurrent `PUT` and `GET`, and seam decoupling for PA2. | Explicitly tailored the threat model to contrast directory traversal protection (regex validation) against denial-of-service risks (unbounded thread spawning). | Cross-checked all statements against the actual code in `src/server.py`, `src/client.py`, and `src/transport_tcp.py`. |
| 6 | *"Can you merge all the changes from both open branches onto main, sticking to Documentation as the most up to date branch"* — Reconciling diverged branch histories. | Git merge strategy and tree verification commands to integrate diverged commits from `origin/main` without overwriting documentation or evidence. | Retained `Documentation` branch versions of `DESIGN.md`, `README.md`, `evidence/ANALYSIS.md`, and `evidence/pa1-capture.pcap` as authoritative over upstream stubs. | Executed `git diff Documentation -- DESIGN.md README.md evidence/ src/ Makefile` (confirming 0 diff) and ran `make build` and `etp_selfcheck.py` in WSL (confirming 30/30 pts). |

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
