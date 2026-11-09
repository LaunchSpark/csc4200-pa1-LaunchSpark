## CSC 4200/5200 Computer Networks

## Programming Assignment 1

An ETP/1 client and server over TCP - and the evidence that they work

Fall 2026 · Tennessee Tech University, Department of Computer Science · Dr. Eric L. Brown

| At a Glance   |                                                                                                                                       |
|---------------|---------------------------------------------------------------------------------------------------------------------------------------|
| Due           | Friday 6 November 2026, 11:59 pm Central.                                                                                             |
| Who           | Individual.                                                                                                                           |
| Language      | C or Python, your choice. Starter kits for both are in ~/csc4200-course/project/starter/.                                             |
| Read first    | The Project Handbook; the ETP/1 Specification (all of it); Chapter 5, §5.2, §5.5 and §5.8.                                            |
| Submit        | In Canvas: your repository URL and the full commit SHA.                                                                               |
| Score         | 100 points in the Assignments category: execution 30, evidence and interpre- tation 30, engineering and documentation 40 (Section 6). |
| Check         | make check runs the course self-check: the same execution tests the grader runs.                                                      |

## Contents

| 1   | What You Are Building . . . . . . . . . . . . . . . . . .    | . . . . . . . . . . . . . . . . . . . . . 1   |
|-----|--------------------------------------------------------------|-----------------------------------------------|
| 2   | Getting Started . . . . . . . . . . . . . . . . . . . . . .  | . . . . . . . . . . . . . . . . . . . . . 2   |
| 3   | Requirements: The Programs . . . . . . . . . . . . . .       | . . . . . . . . . . . . . . . . . . . . . 3   |
|     | 3.1 The execution tests . . . . . . . . . . . . . . . .      | . . . . . . . . . . . . . . . . . . . . . 3   |
| 4   | Requirements: The Evidence . . . . . . . . . . . . . . .     | . . . . . . . . . . . . . . . . . . . . . 4   |
|     | 4.1 Capture your own sessions . . . . . . . . . . .          | . . . . . . . . . . . . . . . . . . . . . 4   |
|     | 4.2 Analyse it . . . . . . . . . . . . . . . . . . . . .     | . . . . . . . . . . . . . . . . . . . . . 5   |
| 5   | Requirements: The Documents . . . . . . . . . . . . .        | . . . . . . . . . . . . . . . . . . . . . 5   |
| 6   | How It Is Scored . . . . . . . . . . . . . . . . . . . . . . | . . . . . . . . . . . . . . . . . . . . . 6   |
| 7   | AI, Authorship and You . . . . . . . . . . . . . . . . .     | . . . . . . . . . . . . . . . . . . . . . 8   |
| 8   | Common Problems . . . . . . . . . . . . . . . . . . . .      | . . . . . . . . . . . . . . . . . . . . . 10  |

## 1 What You Are Building

A small company wants a file drop that its own tools can talk to: list what is there, fetch a file, store a file, with a digest to prove the file arrived intact. A colleague has written the protocol down - the ETP/1 Specification - and your job is to build the server and the client from that document alone, the way real network software is built from RFCs. Then you prove it works, not by saying so, but by capturing it on the wire and explaining what the capture shows.

You deliver three things:

1. Two programs that implement ETP/1 exactly: etp-server, which serves many clients at once and survives the ones that misbehave, and etp-client. All network access goes through the transport seam (Specification §11).
2. Evidence: a loopback capture of your own PUT and GET sessions, the ss output showing TIME-WAIT afterwards, and an analysis of what TCP did with your bytes (Section 4). This replaces the separate packet-analysis assignment listed in the syllabus.
3. Documents: a README, a short design document, and an AI-use disclosure (Section 5).

This is the first of three milestones (Handbook, §1). The application you build here is the application your project runs on top of your own transport in December. Build the seam carefully.

## 2 Getting Started

1. cd ~/csc4200-course &amp;&amp; git pull, then read project/README.md. It shows you how to copy a starter kit into your work folder, create a private GitHub repository named csc4200-pa1-USERNAME, and push your first commit.
2. Add the instructor and the GTA as collaborators. Their GitHub usernames are in Canvas. If they cannot clone your repository, it cannot be graded.
3. Run make build and make check. Every execution test fails: that is your starting line. The self-check is your scoreboard from here on. (C students: if the build cannot find openssl/evp.h, run sudo apt install libssl-dev once.)

## What the starter gives you, and what it does not

| Given                                                                                                                                                                                                                                        | Yours to write                                                                                                                                                                                                                            |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Makefile with build, run-server, check, clean ./etp-server and ./etp-client entry points, with argument parsing Protocol constants; the file-name check; SHA-256 helper (C) Templates: README.md, DESIGN.md, AI_USE.md, evidence/ANALYSIS.md | The transport seam over TCP (transport_tcp) Message encoding and reading (framing) The server's session loop, checks, files, logging and concurrency The client's session and its exit codes The capture, the analysis, and the documents |

Chapter 5, §5.8, Figures 5.6-5.8, shows a working TCP echo server and client in both C and Python, including recv\_exact. You may adapt them; say so in a comment.

## A plan that works

| By         | Have this working                                                                                                                                |
|------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| Tue 27 Oct | Repository pushed, collaborators added. encode produces the bytes in Specification §12 exactly - test it against that table. recv_exact written. |
| Fri 30 Oct | Server answers HELLO, LIST, GET, BYE for one client; client does list and get.                                                                   |
| Tue 3 Nov  | PUT, every error in §8, one thread per session. Self-check at 24 or above.                                                                       |
| Thu 5 Nov  | Capture, time-wait.txt, analysis, design and README written.                                                                                     |
| Fri 6 Nov  | Self-check one last time on a fresh clone; submit the SHA.                                                                                       |

## 3 Requirements: The Programs

The ETP/1 Specification is the requirement. In particular:

- Wire format and behaviour exactly as in Specification §3-§8, including the order of checks in §8.1 and the fatal/non-fatal distinction.
- Server program as in §9: command line, loopback by default, concurrency, robustness, SO\_REUSEADDR, one log line per response.
- Client program as in §10: command line, exact standard output, exit codes 0-3, waits for the server's close after BYE\_OK.
- The seam (§11): only files whose names begin with transport call the socket API.
- Build: make build on a fresh clone in the Lab 0 VM leaves executable ./etp-server and ./etp-client in the repository root. No compiled binaries are committed. Any library beyond the C standard library, pthreads and OpenSSL, or beyond the Python standard library, is declared in the README with its install command.
- Repository practice: at least five commits of your own work after the starter commit, on at least three different days. A single commit of finished work tells us nothing about how it was built.

## 3.1 The execution tests

These are the tests etp\_selfcheck.py runs and the grader runs. Each is pass/fail. The table is generated from the tool itself.

| Test   |   Pts | Checks                                  | Test   |   Pts | Checks                                               |
|--------|-------|-----------------------------------------|--------|-------|------------------------------------------------------|
| S01    |     2 | HELLO handshake and HELLO_OK format     | S13    |     1 | oversized LEN is fatal, nothing allocated            |
| S02    |     2 | LIST format, sorting and filtering      | S14    |     1 | request before HELLO is fatal                        |
| S03    |     1 | GET a small file                        | S15    |     1 | BYE: BYE_OK, then the server closes                  |
| S04    |     1 | GET a 2 MiB file                        | S16    |     2 | 8 clients served while 2 others stall                |
| S05    |     2 | PUT 300 KB, digest, then GET it back    | S17    |     1 | survives clients that vanish mid-transfer            |
| S06    |     1 | PUT and GET empty files                 | S18    |     1 | restart on the same port (SO_REUSEADDR)              |
| S07    |     1 | NOT_FOUND is non-fatal                  | C01    |     1 | list: fragmented response printed exactly; sends BYE |
| S08    |     1 | BAD_NAME blocks traversal; non-fatal    | C02    |     2 | get: 200 KB in fragments written to disk             |
| S09    |     2 | requests arriving in fragments          | C03    |     1 | put: payload layout and digest printed               |
| S10    |     2 | several requests in one write           | C04    |     1 | server ERROR: exit 1 and a stderr message            |
| S11    |     1 | unknown TYPE: BAD_TYPE, payload skipped | C05    |     1 | digest mismatch: exit 3                              |
| S12    |     1 | bad VERSION is fatal                    | C06    |     0 | no server: exit 2 (not scored)                       |

## 4 Requirements: The Evidence

## 4.1 Capture your own sessions

In your Lab 0 VM, from your repository root, using your own server and client. Pick a port (5000 below) and keep it throughout. Use a test file of random bytes between 200 and 400 KiB. Loopback carries segments of up to about 64 KB, so a file that size makes the GET response cross several TCP segments.

```
mkdir -p server-files evidence scratch # scratch/ is never committed head -c 262144 /dev/urandom > scratch/photo.bin # 256 KiB of synthetic data # Terminal 1: the server ./etp-server --port 5000 --root server-files # Terminal 2: start the capture (either line; sudo if permission is denied) tshark -i lo -s 200 -f "tcp port 5000" -w evidence/pa1-capture.pcap tcpdump -i lo -s 200 -Z $USER -w evidence/pa1-capture.pcap tcp port 5000 # Terminal 3: one PUT session, then one GET session, then ss within a minute C="./etp-client --host 127.0.0.1 --port 5000 --name YOURNAME" $C put scratch/photo.bin photo.bin $C get photo.bin scratch/copy.bin cmp scratch/photo.bin scratch/copy.bin && echo identical ss -tan state time-wait '( sport = :5000 or dport = :5000 )' \ > evidence/time-wait.txt # Terminal 2: stop the capture with Ctrl-C
```

- -s 200 keeps only the first 200 bytes of each packet: enough for every header and the start of each payload, small enough to commit, and your file's contents stay out of the repository. The test files live in scratch/, which the starter's .gitignore keeps out of git.
- The capture must contain the whole of both sessions: handshake to final FIN. Start it

before the first client and stop it after the second exits. If you captured with sudo, run sudo chown $USER evidence/pa1-capture.pcap.

- Either pcap or pcapng format is accepted (tshark writes pcapng even with a .pcap name; that is fine). Keep the file name pa1-capture.pcap.
- Linux keeps TIME-WAIT for 60 seconds. If time-wait.txt comes out empty, repeat the whole procedure from the start - capture, PUT, GET, ss - so that the two files describe the same sessions.
- If a capture shows a RST, a missing FIN, or a client that never sent HELLO, the self-check will say so. Fix the cause and capture again.

You can read the capture with tshark -r inside the VM, or copy it to your host and open it in Wireshark. For raw sequence numbers, turn off relative sequence numbers in Wireshark (Preferences → Protocols → TCP), or add -o tcp.relative\_sequence\_numbers:FALSE to tshark.

## 4.2 Analyse it

Fill in evidence/ANALYSIS.md from the template. It has two parts.

The facts block - eight values about your GET session, read from your capture, in the etp-facts block. The grader computes the same values from your capture and compares. Each value that matches earns a point. The two server-to-client counts cover all three of the server's responses in that session (HELLO\_OK, GET\_OK and BYE\_OK), each frame counted once, as captured.

Five questions - answered in your own words, each in a paragraph or two, using your own numbers. In brief:

- Q1 The handshake. The three segments, their flags and raw numbers; why the third segment's acknowledgment number is what it is; the MSS and what sets it.
- Q2 Your protocol on the wire. The GET request's header and the GET\_OK header, decoded field by field from the hex; the arithmetic that adds up the server's payload bytes.
- Q3 Byte stream, not messages. How many segments carried the GET\_OK response, their sizes, whether messages and segments line up, and where your code deals with that.
- Q4 Teardown and TIME-WAIT. Who closed first and why; which end is in TIME-WAIT, for how long, and why that is the reason for SO\_REUSEADDR.
- Q5 What an observer learns. What someone holding this capture knows about your session, what the 200-byte snap length hides and does not, and what kind of protection would change that.

The full wording is in the template. Q1-Q5 are what the old packet-analysis assignment was for; here you do it on traffic your own code produced.

## 5 Requirements: The Documents

README.md How to build and run; what works and what does not - honestly, matching your self-check output; the file list; and the signed authorship statement at the end.

- DESIGN.md One to two pages, seven short sections from the template: architecture, the seam, framing, concurrency, errors and disconnects, a threat model, and testing (including one bug you found and fixed).
Required even if the answer is "none".

| What You Submit                                                                     |
|-------------------------------------------------------------------------------------|
| In the repository csc4200-pa1-USERNAME, at the commit you submit:                   |
| □ your source code, Makefile, and (Python) the etp-server and etp-client launchers; |
| □ README.md with the signed authorship statement; DESIGN.md; AI_USE.md;             |
| □ evidence/pa1-capture.pcap, evidence/time-wait.txt, evidence/ANALYSIS.md.          |
| In Canvas: the repository URL and the full 40-character commit SHA.                 |

## 6 How It Is Scored

Table 1. The PA1 rubric. 50 points are computed; 50 are judged by people on the bands below.

| Part                               | Pts                                | Scored by                          | How                                                                                                                                                                 |
|------------------------------------|------------------------------------|------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Execution (30)                     |                                    |                                    |                                                                                                                                                                     |
| Server tests S01-S18               | 24                                 | script                             | Section 3.1; the self-check shows you this score.                                                                                                                   |
| Client tests C01-C05               | 6                                  | script                             | Section 3.1.                                                                                                                                                        |
| Evidence and interpretation (30)   | Evidence and interpretation (30)   | Evidence and interpretation (30)   |                                                                                                                                                                     |
| Capture complete                   | 2                                  | script                             | The GET session has a handshake, an ETP HELLO first, at least 200 KiB from the server, FINs from both sides, and no RST.                                            |
| Capture facts                      | 8                                  | script                             | One point for each etp-facts value that matches your capture.                                                                                                       |
| Q1-Q5                              | 20                                 | people                             | 4 each, on the interpretation bands below.                                                                                                                          |
| Engineering and documentation (40) | Engineering and documentation (40) | Engineering and documentation (40) |                                                                                                                                                                     |
| Build                              | 3                                  | script                             | make build succeeds on a fresh clone.                                                                                                                               |
| Required files                     | 2                                  | script                             | All present: 2. One or two missing: 1. More: 0.                                                                                                                     |
| Commit history                     | 3                                  | script                             | Counting commits after the starter commit: ≥5 on ≥3 days: 3. ≥5, or ≥2 days: 2. ≥2: 1.                                                                              |
| The seam                           | 2                                  | script, then people                | No socket calls outside transport* files (your own test programs in tests/ are exempt). Any- thing the script flags is checked by a person before points are taken. |
| DESIGN.md                          | 15                                 | people                             | Design bands below.                                                                                                                                                 |
| README.md                          | 10                                 | people                             | README bands below.                                                                                                                                                 |
| AI use and authorship              | 5                                  | people                             | Bands below.                                                                                                                                                        |
| Total                              | 100                                |                                    |                                                                                                                                                                     |

## Interpretation, each of Q1-Q5 (4 points)

| Band        | Points                                                                                           | What it looks like                                                                             |
|-------------|--------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| 4           | Correct, built on your own numbers - the mechanism, not just the observation specification where | Complete from your capture, and explains why - tying it to your code or the the question asks. |
| Solid       | 3                                                                                                | Correct and uses your own numbers, but the explanation is thin or has one minor error.         |
| Partial     | 2                                                                                                | Some correct elements; numbers missing or generic, or a significant error in the reasoning.    |
| Beginning 1 |                                                                                                  | Attempted, but mostly incorrect.                                                               |
| Missing     | 0                                                                                                | Not answered, or not about your capture.                                                       |

## DESIGN.md (15 points)

| Band      | Points   | What it looks like                                                                                                                                                                                          |
|-----------|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Complete  | 14-15    | All seven sections, specific and true of the code. The seam, framing and concurrency choices come with reasons. The threat model names an attack your server resists and one it does not. A real bug story. |
| Solid     | 11-13    | All sections present and accurate; one or two thin or generic.                                                                                                                                              |
| Partial   | 7-10     | Several sections generic, missing, or inconsistent with the code.                                                                                                                                           |
| Beginning | 0-6      | Largely missing, or does not describe this code.                                                                                                                                                            |

## README.md (10 points)

| Band      | Points   | What it looks like                                                                                                                                  |
|-----------|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| Complete  | 9-10     | Build and run instructions a stranger could follow; an honest "what works" that matches the self-check; the file list; signed authorship statement. |
| Solid     | 7-8      | Accurate, with a gap a grader had to work around.                                                                                                   |
| Partial   | 4-6      | Incomplete or partly inaccurate; limitations not stated.                                                                                            |
| Beginning | 0-3      | Missing or mostly template text.                                                                                                                    |

## AI use and authorship (5 points)

| Band     |   Points | What it looks like                                                                                                                                                      |
|----------|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Complete |        5 | AI_USE.md is complete and specific (or a credible "none"), including the log and section 5 (what it got wrong, or how you checked); the authorship statement is signed. |
| Partial  |        3 | Present but vague or generic (4 or 1-2 where it falls between).                                                                                                         |
| Missing  |        0 | No disclosure, or the authorship statement is missing or unsigned.                                                                                                      |

## Common Misconception

"The self-check says 30/30, so I'm done." Execution is 30 of 100 points. Half the grade is your reasoning and your writing, judged by people. A server that fails two tests, with an honest README, a clear design and an excellent analysis, outscores a perfect server with thin answers and template documents - often by a full letter grade or more.

## 7 AI, Authorship and You

For PA1, this section replaces the syllabus's "tool syntax only" rule for packet analysis: you may use AI to understand what you see in your capture, but the reading and the reasoning must be yours.

You may use generative AI tools in this project. Working engineers do, and learning to use them well is part of what this course should teach you. But the point of these assignments is that you learn network programming: how a byte stream behaves, how framing works, how a server survives its clients, how reliability is built from loss. A tool that does that thinking for you takes the learning with it, and the final exam, the project, and your first job will find the gap.

## Encouraged (disclose it)

- Explaining a concept, an error message, a manual page, or a passage of the specification.
- Reviewing code you wrote: finding bugs, questioning unclear parts, pointing at the specification rule you broke.
- Helping you design tests and think of edge cases.
- Tooling: make, git, argument parsing, shell commands, Wireshark display filters.
- Helping you understand what you are looking at in a capture - what a field means, why TIME-WAIT exists, why segment sizes vary - and editing your prose for clarity. The ideas, the numbers and the reasoning stay yours.

## Not allowed

- framing - encoding a message, and reading one from the stream. In the Python starter these are encode and read\_message; in the C starter, etp\_send and etp\_read\_header;
- the transport seam: the six functions in your transport\_tcp file;
- the server's session handling and concurrency: the request loop, the checks of Specification §8.1, and how sessions run side by side;
- the client's session: HELLO, the command, BYE, and the choice of exit status.
- Having an AI produce your answers to Q1-Q5 or your etp-facts values, or read your capture and tell you the values to write down - including having it write a command or

script that pulls those values out for you.  The values come from your own capture and the reasoning is in your own words.

## Always

- Disclose every use in AI\_USE.md: what you asked, what you used, what you changed, how you checked it, and one thing the tool got wrong - or, if you found nothing wrong, how you checked.
- Be able to explain every line you submit. Code you cannot explain is not your work, whoever typed it.
- Sign the authorship statement at the end of your README.md.

## The explanation conversation

Any student may be asked to meet with the instructor or the GTA for about ten minutes to walk through their submission: explain a function, make a small change, read a line of their capture. Some students are chosen at random; others because something in a submission needs a conversation. Being asked is not an accusation. A part of the work you cannot explain earns no credit, and a pattern of that is handled under TNTech Policy 216 (Academic Integrity).



 The instructor welcomes your help as a tutor, reviewer and debugging partner, and asks that you not act as the author.

Please do: explain concepts, the specification, the socket API, error messages and Wireshark; review and critique code the student has written, and ask questions that lead them to find and fix their own bugs; help them design tests; help with tooling such as make, git and the shell.

Please do not: write the core code each assignment brief reserves for the student (listed under Not allowed), in whole or in large part; write answers to the analysis questions; read the student's capture and report the values to fill in; or complete the assignment end to end.

If you are asked to do one of those things, please say that the course asks you not to, and offer to work through it with the student one step at a time instead. Thank you.

To the student: this note is here in the open, on purpose. 

## 8 Common Problems

- "Address already in use" when I restart the server. TIME-WAIT, because your server closes first (Specification §5). Set SO\_REUSEADDR before bind(). Test S18 checks it.
- My C server vanishes when a client disconnects. SIGPIPE. Specification §9, "Three traps".
- S09 or S10 fails but everything else passes. You are assuming one recv returns one message.

Read with recv\_exact; read the header, then exactly LENGTH bytes.

S16 fails. Your server handles one connection at a time. One thread per session.

S02 fails on ordering. Sort by byte value: uppercase letters come before lowercase ones.

- tshark says "permission denied". Run it with sudo, then sudo chown $USER the capture file.
- My facts are marked wrong. Check that you analysed the GET session (the second connection), that you used raw sequence numbers, and that both server-to-client counts include all three responses in that session.
- make check reports seam problems in my test script. Put your own test programs in a tests/ folder (or name them test\_*); they are exempt.
- I changed my code after capturing. Then capture again, so that the evidence describes the code you submit.

## You Are the Author

Before you submit, read the statement at the end of your README.md and sign it only if it is true. You are the author of everything in your repository: the code, the capture, the analysis and the documents.  You are. If any part of the work is not yours, or you could not explain it if asked, fix that before Friday - or say so plainly in your README and AI\_USE.md. Honest gaps cost points. Misrepresented work costs far more.