# PA1 Evidence Collection & Analysis Checklist

This checklist covers all requirements for the **Evidence and Interpretation** component (30 of 100 points) of Programming Assignment 1, derived from **PA1 Brief §4, §4.1, §4.2** and **§6 Rubric**.

## Verified recollection — November 10, 2026; rechecked November 12, 2026

The evidence was recollected in a local Docker Linux container. The checklist below refers to that new run, not the previous capture. The exact commands, environment, source hashes, and outputs are retained in `evidence/`; the workflow is reproducible using `tests/evidence/README.md`.

- **Capture:** 5,619 bytes, snaplen 200, 46 frames. PUT uses client port 50488; GET uses 50498. Both sessions contain complete three-way handshakes, HELLO-first application streams, server-first FINs, both FINs, and final ACKs. There are no resets, gaps, overlaps, retransmissions, or kernel capture drops.
- **Integrity:** source, server copy, and downloaded copy each contain 262,144 bytes; both `cmp` checks pass. Their SHA-256 hashes and the PUT digest all equal `8e345f92d5faa9ebf77888860a10d6d3e8ee378ee93990cac1a795039bcc4973`. The random files remain locally in ignored directories.
- **TIME-WAIT:** both server-side entries are present. The timestamp before `ss` was 0.014337 seconds after the GET's final ACK; the timer output records 59 seconds remaining.
- **Analysis:** all eight facts match the new capture. Q1–Q5 use the new frame numbers and corrected MSS, segmentation, teardown, snaplen, and TLS explanations. GET_OK spans six data segments; total server payload is 262,192 bytes across eight segments.
- **Validation:** `tests/evidence/verify.py --evidence evidence --analysis evidence/ANALYSIS.md` passes. The complete course self-check scores **30/30 execution** and **10/10 repository**; all **44 repository unit tests** pass. Results are retained in `verification.json`, `selfcheck.txt`, `selfcheck.json`, and `unittest.txt`.
- **Packaging correction:** the course checker was moved unchanged to `tests/course/etp_selfcheck.py`, which fixes the false transport-seam finding. The seam now scores 2/2. `make check` uses the new fallback location and propagates a failing check's exit status.

**November 12 recheck:** commit history now spans November 9, 10, and 12, so history scores 3/3 and the repository scores 10/10. The current `selfcheck.txt` and `selfcheck.json` record this local recheck; the Linux capture and collection logs remain from November 10. The course PDFs are not in this checkout, so the rubric interpretation and specification section reference still need the submitting author's confirmation; automated checks do not award the human-graded analysis points.

---

## 1. Prerequisites & Environment Setup

- [x] Ensure `server-files/`, `evidence/`, and `scratch/` directories exist:
  ```bash
  mkdir -p server-files evidence scratch
  ```
- [x] Confirm `scratch/` is ignored by git (test files must **never** be committed).
- [x] Generate synthetic test file of random bytes between **200 KiB and 400 KiB** (e.g., exactly 256 KiB = 262,144 bytes):
  ```bash
  head -c 262144 /dev/urandom > scratch/photo.bin
  ```

---

## 2. Wire Capture Workflow (`evidence/pa1-capture.pcap`)

The capture must record **both sessions completely** (PUT followed by GET), from the initial TCP SYN to the final FIN-ACK teardown.

- [x] **Step 2.1: Start Server**
  ```bash
  ./etp-server --port 5000 --root server-files
  ```
- [x] **Step 2.2: Start Packet Capture**
  *Snap length `-s 200` is required: it preserves packet headers and message prefixes while limiting captured file content. Some file bytes remain visible in each data packet.*
  - **Linux / Lab VM:**
    ```bash
    tcpdump -i lo -s 200 -Z $USER -w evidence/pa1-capture.pcap tcp port 5000
    ```
  - **macOS (if capturing locally):**
    ```bash
    sudo tcpdump -i lo0 -s 200 -w evidence/pa1-capture.pcap tcp port 5000
    ```
- [x] **Step 2.3: Execute PUT Session**
  ```bash
  ./etp-client --host 127.0.0.1 --port 5000 --name eagle01 put scratch/photo.bin photo.bin
  ```
- [x] **Step 2.4: Execute GET Session**
  ```bash
  ./etp-client --host 127.0.0.1 --port 5000 --name eagle01 get photo.bin scratch/copy.bin
  ```
- [x] **Step 2.5: Verify Integrity**
  ```bash
  cmp scratch/photo.bin scratch/copy.bin && echo "Files match!"
  ```
- [x] **Step 2.6: Capture TIME-WAIT Immediately** *(Must run within 60 seconds; command and output recorded in submitted evidence)*
  ```bash
  ss -tan state time-wait '( sport = :5000 or dport = :5000 )' > evidence/time-wait.txt
  ```
- [x] **Step 2.7: Stop Capture**
  - Stop `tcpdump` with `Ctrl-C`.
  - If captured with `sudo`, fix permissions:
    ```bash
    sudo chown $USER evidence/pa1-capture.pcap
    chmod 644 evidence/pa1-capture.pcap evidence/time-wait.txt
    ```

---

## 3. PCAP Quality Verification (`etp_selfcheck.py`)

Run `python3 tests/course/etp_selfcheck.py` to confirm the capture meets all automated checks:

- [x] **File Size:** Under 5 MiB (measured: 5,619 bytes; `-s 200` limits per-packet size, not total file size).
- [x] **Snap Length:** Snaplen $\le 512$ bytes (measured: 200).
- [x] **Handshake Present:** Complete 3-way SYN $\to$ SYN/ACK $\to$ ACK.
- [x] **First Message:** First client application payload starts with ETP/1 `HELLO` (`0x01 0x01`).
- [x] **Transfer Volume:** Server sent $\ge 200\text{ KiB}$ in the GET session.
- [x] **Clean Teardown:** Both sides sent FIN segments (`fin_from_both == True`).
- [x] **No Resets:** Connection contains **zero RST packets** (`rst == False`).

---

## 4. Complete `evidence/ANALYSIS.md`

Open `evidence/ANALYSIS.md` and complete both parts:

### Part A: Commands & Facts Block (8 Points)
- [x] **How I captured it:** Paste the exact commands executed and the transferred file size.
- [x] **`etp-facts` block:** Fill in all 8 fields for the **GET session** using **raw (absolute) sequence numbers**:
  ```etp-facts
  server_port: 5000
  client_port: <client ephemeral port>
  client_isn: <raw 32-bit sequence number from client SYN>
  server_isn: <raw 32-bit sequence number from server SYN/ACK>
  client_mss: <MSS option value from client SYN in bytes>
  server_to_client_payload_bytes: <total TCP payload bytes sent by server in GET session>
  server_to_client_data_segments: <count of server-to-client frames carrying payload>
  first_fin_from: server
  ```
  *(Note: Wireshark: Edit $\to$ Preferences $\to$ Protocols $\to$ TCP $\to$ uncheck "Relative sequence numbers", or tshark `-o tcp.relative_sequence_numbers:FALSE`)*

---

### Part B: Analysis Questions Q1–Q5 (20 Points, 4 Points Each)

- [x] **Q1: The Handshake**
  - [x] Frame numbers of the 3 handshake segments for the GET session.
  - [x] Flags (`SYN`, `SYN-ACK`, `ACK`) and raw sequence/acknowledgment numbers.
  - [x] Explanation of why segment 3 ACK equals `server_isn + 1` (SYN consumes 1 sequence number in sequence space).
  - [x] Client advertised MSS and its basis in the measured loopback MTU, fixed IP/TCP header sizes, and IPv4 packet-length limit.

- [x] **Q2: Protocol on the Wire**
  - [x] Frame number of client's GET request.
  - [x] First 8 payload bytes in hex and field-by-field decode: `VERSION (1)`, `TYPE (3)`, `STATUS (0)`, `RESERVED (0)`, `LENGTH (filename length)`.
  - [x] Frame number of server's `GET_OK` response header and field-by-field decode.
  - [x] Verification that `GET_OK` `LENGTH` matches the actual byte size of `scratch/photo.bin`, `server-files/photo.bin`, and `scratch/copy.bin`, recorded in `integrity.txt`.
  - [x] Arithmetic breakdown showing how `server_to_client_payload_bytes` equals:
    $$\text{Payload} = (8 + \text{len}(\text{HELLO\_OK})) + (8 + \text{len}(\text{GET\_OK})) + (8 + 0 \text{ for BYE\_OK})$$

- [x] **Q3: Byte Stream, Not Messages**
  - [x] Number of TCP segments carrying the `GET_OK` response (excluding `HELLO_OK` and `BYE_OK`).
  - [x] Payload sizes of those segments (noting whether any hit loopback MTU/segment limits).
  - [x] Explanation of message boundary handling: whether messages align with packet boundaries.
  - [x] Code reference: Point to `recv_exact` in `src/transport_tcp.py` and explain how the read loop handles stream reassembly across arbitrary chunk sizes.

- [x] **Q4: Teardown and TIME-WAIT**
  - [x] State which side sent the first FIN (`server`) and cite **Specification §5** (server closes connection after `BYE_OK`; citation present, course PDF unavailable for verification).
  - [x] Paste the relevant line from `evidence/time-wait.txt`.
  - [x] Identify which end is in TIME-WAIT (`127.0.0.1:5000`) and the default kernel duration (~60 seconds on Linux).
  - [x] Explain why the server in TIME-WAIT necessitates `SO_REUSEADDR` before `bind()`.

- [x] **Q5: What an Observer Learns**
  - [x] List information an on-path eavesdropper obtains (client name, file names, file sizes, session timestamps/rtt).
  - [x] Impact of the 200-byte snap length: explain truncation per packet after accounting for link/IP/TCP headers, including file prefixes exposed at multiple offsets, protocol metadata, and small payloads.
  - [x] Cryptographic defense: How TLS / authenticated encryption (AEAD) protects payload confidentiality and integrity, and what metadata remains observable (IP endpoints, packet timing, approximate payload size).

---

## 5. Final Self-Check Verification

- [x] Run the complete course self-check:
  ```bash
  python3 tests/course/etp_selfcheck.py -v
  ```
- [x] Confirm all scoring targets:
  - [x] `Execution: 30 / 30 points`
  - [x] `Build and repository: 10 / 10` — verified November 12, including the three-day history requirement.
  - [x] No warnings on `evidence/pa1-capture.pcap`
  - [x] `ANALYSIS.md`: all facts present and all eight values independently matched to the capture.

## 6. Recollection proof

- [x] `evidence/collection.log`: executed commands and UTC start/end timestamps.
- [x] `evidence/environment.txt`: Linux/kernel/tool versions, loopback MTU, route, source/checker hashes.
- [x] `evidence/integrity.txt`: source/server/download comparisons, sizes, and matching SHA-256 hashes.
- [x] `evidence/put.stdout`: matching digest returned by PUT.
- [x] `evidence/time-wait-collected-at.txt` and `time-wait-timers.txt`: immediate snapshot and live timers.
- [x] `evidence/tcpdump.log`: 46 captured packets and zero kernel drops.
- [x] `evidence/verification.json`: both streams checked against retained files, full teardown, and exact analysis facts.
- [x] `evidence/selfcheck.txt`, `selfcheck.json`, and `unittest.txt`: complete validation results.
- [x] `evidence/verifier-negative-checks.txt`: the verifier rejects a missing final ACK, altered captured file bytes, an incorrect analysis fact, and missing TIME-WAIT output; failures remove stale PASS reports.
- [ ] `AI_USE.md`: author to finish the collection, analysis, and verification disclosure in their own voice before submission.
