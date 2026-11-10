# PA1 Evidence Collection & Analysis Checklist

This checklist covers all requirements for the **Evidence and Interpretation** component (30 of 100 points) of Programming Assignment 1, derived from **PA1 Brief §4, §4.1, §4.2** and **§6 Rubric**.

---

## 1. Prerequisites & Environment Setup

- [ ] Ensure `server-files/`, `evidence/`, and `scratch/` directories exist:
  ```bash
  mkdir -p server-files evidence scratch
  ```
- [ ] Confirm `scratch/` is ignored by git (test files must **never** be committed).
- [ ] Generate synthetic test file of random bytes between **200 KiB and 400 KiB** (e.g., exactly 256 KiB = 262,144 bytes):
  ```bash
  head -c 262144 /dev/urandom > scratch/photo.bin
  ```

---

## 2. Wire Capture Workflow (`evidence/pa1-capture.pcap`)

The capture must record **both sessions completely** (PUT followed by GET), from the initial TCP SYN to the final FIN-ACK teardown.

- [ ] **Step 2.1: Start Server**
  ```bash
  ./etp-server --port 5000 --root server-files
  ```
- [ ] **Step 2.2: Start Packet Capture**
  *Snap length `-s 200` is required: it preserves packet headers and starts of messages while keeping file content small and out of git.*
  - **Linux / Lab VM:**
    ```bash
    tcpdump -i lo -s 200 -Z $USER -w evidence/pa1-capture.pcap tcp port 5000
    ```
  - **macOS (if capturing locally):**
    ```bash
    sudo tcpdump -i lo0 -s 200 -w evidence/pa1-capture.pcap tcp port 5000
    ```
- [ ] **Step 2.3: Execute PUT Session**
  ```bash
  ./etp-client --host 127.0.0.1 --port 5000 --name student put scratch/photo.bin photo.bin
  ```
- [ ] **Step 2.4: Execute GET Session**
  ```bash
  ./etp-client --host 127.0.0.1 --port 5000 --name student get photo.bin scratch/copy.bin
  ```
- [ ] **Step 2.5: Verify Integrity**
  ```bash
  cmp scratch/photo.bin scratch/copy.bin && echo "Files match!"
  ```
- [ ] **Step 2.6: Capture TIME-WAIT Immediately** *(Must run within 60 seconds)*
  ```bash
  ss -tan state time-wait '( sport = :5000 or dport = :5000 )' > evidence/time-wait.txt
  ```
- [ ] **Step 2.7: Stop Capture**
  - Stop `tcpdump` with `Ctrl-C`.
  - If captured with `sudo`, fix permissions:
    ```bash
    sudo chown $USER evidence/pa1-capture.pcap
    chmod 644 evidence/pa1-capture.pcap evidence/time-wait.txt
    ```

---

## 3. PCAP Quality Verification (`etp_selfcheck.py`)

Run `python3 project/etp_selfcheck.py` to confirm the capture meets all automated checks:

- [ ] **File Size:** Under 5 MiB (guaranteed by `-s 200`).
- [ ] **Snap Length:** Snaplen $\le 512$ bytes.
- [ ] **Handshake Present:** Complete 3-way SYN $\to$ SYN/ACK $\to$ ACK.
- [ ] **First Message:** First client application payload starts with ETP/1 `HELLO` (`0x01 0x01`).
- [ ] **Transfer Volume:** Server sent $\ge 200\text{ KiB}$ in the GET session.
- [ ] **Clean Teardown:** Both sides sent FIN segments (`fin_from_both == True`).
- [ ] **No Resets:** Connection contains **zero RST packets** (`rst == False`).

---

## 4. Complete `evidence/ANALYSIS.md`

Open `evidence/ANALYSIS.md` and complete both parts:

### Part A: Commands & Facts Block (8 Points)
- [ ] **How I captured it:** Paste the exact commands executed and the transferred file size.
- [ ] **`etp-facts` block:** Fill in all 8 fields for the **GET session** using **raw (absolute) sequence numbers**:
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

- [ ] **Q1: The Handshake**
  - [ ] Frame numbers of the 3 handshake segments for the GET session.
  - [ ] Flags (`SYN`, `SYN-ACK`, `ACK`) and raw sequence/acknowledgment numbers.
  - [ ] Explanation of why segment 3 ACK equals `server_isn + 1` (SYN consumes 1 sequence number in sequence space).
  - [ ] Client advertised MSS and what on your system determines it (MTU of loopback interface minus 40 bytes for IP/TCP headers).

- [ ] **Q2: Protocol on the Wire**
  - [ ] Frame number of client's GET request.
  - [ ] First 8 payload bytes in hex and field-by-field decode: `VERSION (1)`, `TYPE (3)`, `STATUS (0)`, `RESERVED (0)`, `LENGTH (filename length)`.
  - [ ] Frame number of server's `GET_OK` response header and field-by-field decode.
  - [ ] Verification that `GET_OK` `LENGTH` matches the exact byte size of `scratch/photo.bin`.
  - [ ] Arithmetic breakdown showing how `server_to_client_payload_bytes` equals:
    $$\text{Payload} = (8 + \text{len}(\text{HELLO\_OK})) + (8 + \text{len}(\text{GET\_OK})) + (8 + 0 \text{ for BYE\_OK})$$

- [ ] **Q3: Byte Stream, Not Messages**
  - [ ] Number of TCP segments carrying the `GET_OK` response (excluding `HELLO_OK` and `BYE_OK`).
  - [ ] Payload sizes of those segments (noting whether any hit loopback MTU/segment limits).
  - [ ] Explanation of message boundary handling: whether messages align with packet boundaries.
  - [ ] Code reference: Point to `recv_exact` in `src/transport_tcp.py` and explain how the read loop handles stream reassembly across arbitrary chunk sizes.

- [ ] **Q4: Teardown and TIME-WAIT**
  - [ ] State which side sent the first FIN (`server`) and cite **Specification §5** (server closes connection after `BYE_OK`).
  - [ ] Paste the relevant line from `evidence/time-wait.txt`.
  - [ ] Identify which end is in TIME-WAIT (`127.0.0.1:5000`) and the default kernel duration (~60 seconds on Linux).
  - [ ] Explain why the server in TIME-WAIT necessitates `SO_REUSEADDR` before `bind()`.

- [ ] **Q5: What an Observer Learns**
  - [ ] List information an on-path eavesdropper obtains (client name, file names, file sizes, session timestamps/rtt).
  - [ ] Impact of the 200-byte snap length: what it conceals (file content beyond offset 192) and what it exposes (all headers, protocol metadata, small payloads).
  - [ ] Cryptographic defense: How TLS / authenticated encryption (AEAD) protects payload confidentiality and integrity, and what metadata remains observable (IP endpoints, packet timing, approximate payload size).

---

## 5. Final Self-Check Verification

- [ ] Run the complete course self-check:
  ```bash
  python3 project/etp_selfcheck.py -v
  ```
- [ ] Confirm:
  - `Execution: 30 / 30 points`
  - `Build and repository: 10 / 10`
  - No warnings on `evidence/pa1-capture.pcap`
  - `ANALYSIS.md`: all facts present
