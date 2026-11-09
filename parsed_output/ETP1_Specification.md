## CSC 4200/5200 Computer Networks

## ETP/1 Specification

The Eagle Transfer Protocol, version 1.0 · Normative for Programming Assignment 1 and the Final Project

Fall 2026 · Tennessee Tech University, Department of Computer Science · Dr. Eric L. Brown

## Status of This Document

Version 1.0, issued 20 October 2026. This document defines what goes on the wire. Where it and any other course document disagree about protocol behaviour, this document wins. If you find an ambiguity, ask in the Canvas discussion ETP Specification Questions. Every answer that changes or clarifies a rule is added to the change log in Section 14 with a date, and announced in Canvas.

PA2 will add a second document, ETP-T, for the transport you build over UDP. ETP/1 itself does not change when that happens - that is the point of the transport seam in Section 11.

## Contents

|   1 | Conventions . . . . . . . . . . . . . . . . . . . . . . .    | . . . . . . . . . . . . . . . . . . . . . . 2   |
|-----|--------------------------------------------------------------|-------------------------------------------------|
|   2 | Overview . . . . . . . . . . . . . . . . . . . . . . . . .   | . . . . . . . . . . . . . . . . . . . . . . 2   |
|   3 | Message Format . . . . . . . . . . . . . . . . . . . . .     | . . . . . . . . . . . . . . . . . . . . . . 2   |
|   4 | Message Types . . . . . . . . . . . . . . . . . . . . . .    | . . . . . . . . . . . . . . . . . . . . . . 3   |
|   5 | Sessions . . . . . . . . . . . . . . . . . . . . . . . . . . | . . . . . . . . . . . . . . . . . . . . . . 4   |
|   6 | Requests . . . . . . . . . . . . . . . . . . . . . . . . .   | . . . . . . . . . . . . . . . . . . . . . . 4   |
| 6.1 | HELLO . . . . . . . . . . . . . . . . . . . . . .            | . . . . . . . . . . . . . . . . . . . . . . 4   |
| 6.2 | LIST . . . . . . . . . . . . . . . . . . . . . . .           | . . . . . . . . . . . . . . . . . . . . . . 5   |
| 6.3 | GET . . . . . . . . . . . . . . . . . . . . . . . .          | . . . . . . . . . . . . . . . . . . . . . . 5   |
| 6.4 | PUT . . . . . . . . . . . . . . . . . . . . . . . .          | . . . . . . . . . . . . . . . . . . . . . . 5   |
| 6.5 | BYE . . . . . . . . . . . . . . . . . . . . . . . .          | . . . . . . . . . . . . . . . . . . . . . . 6   |
|   7 | File Names . . . . . . . . . . . . . . . . . . . . . . . .   | . . . . . . . . . . . . . . . . . . . . . . 6   |
|   8 | Errors . . . . . . . . . . . . . . . . . . . . . . . . . . . | . . . . . . . . . . . . . . . . . . . . . . 6   |
| 8.1 | Order of checks . . . . . . . . . . . . . . . . .            | . . . . . . . . . . . . . . . . . . . . . . 6   |
| 8.2 | Fatal and non-fatal . . . . . . . . . . . . . . .            | . . . . . . . . . . . . . . . . . . . . . . 7   |
|   9 | The Server Program . . . . . . . . . . . . . . . . . . .     | . . . . . . . . . . . . . . . . . . . . . . 7   |
|  10 | The Client Program . . . . . . . . . . . . . . . . . . .     | . . . . . . . . . . . . . . . . . . . . . . 8   |
|  11 | The Transport Seam . . . . . . . . . . . . . . . . . . .     | . . . . . . . . . . . . . . . . . . . . . . 9   |
|  12 | Worked Example . . . . . . . . . . . . . . . . . . . .       | . . . . . . . . . . . . . . . . . . . . . . 10  |
|  13 | Security Considerations . . . . . . . . . . . . . . . .      | . . . . . . . . . . . . . . . . . . . . . . 11  |
|  14 | Change Log . . . . . . . . . . . . . . . . . . . . . . .     | . . . . . . . . . . . . . . . . . . . . . . 11  |

## 1 Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY are used as in RFC 2119 and RFC 8174: MUST is an absolute requirement, SHOULD means there may be a valid reason to do otherwise but you must understand the consequences, and MAY is truly optional. A "byte" is eight bits. Hexadecimal values are written 0x2A. All multi-byte integers are unsigned and are sent in network byte order (big-endian, most significant byte first).

Message names are set in bold sans-serif (HELLO, GET\_OK) and header fields in plain sansserif (LENGTH) . . . . \_OK means any of the five success responses (Table 1). A request is a message from client to server; a response is a message from server to client.

## 2 Overview

ETP is a small file-transfer protocol. A client opens a connection to a server, identifies itself, asks for one thing - a directory listing, a file, or permission to store a file - and leaves. The server keeps a single flat directory of files, its root, and serves any number of clients at once.

ETP is an application-layer protocol. It assumes the layer below it delivers a reliable, ordered byte stream and nothing more. In PA1 that layer is TCP. In the final project it is the transport you build over UDP in PA2. Your application code reaches the network only through a small transport seam (Section 11), so that the swap touches only the transport files and the Makefile.

Figure 1. Where ETP/1 sits. Only the bottom row changes between PA1 and the project.

<!-- image -->

## 3 Message Format

Every ETP message, in either direction, is an 8-byte header followed by a payload of exactly LENGTH bytes. There are no delimiters, terminators or padding. The next message begins on the byte after the last payload byte.

Figure 2. The ETP/1 header. In Python, struct.Struct("!BBBBI") packs and unpacks it.

<!-- image -->

| Field    |   Bytes | Rule                                                                                                                                                                              |
|----------|---------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| VERSION  |       1 | Always 1. A server that sees anything else applies Section 8; a client applies Section 10.                                                                                        |
| TYPE     |       1 | The message type, Table 1.                                                                                                                                                        |
| STATUS   |       1 | 0 in every request and every . . . _OK response. In an ERROR response, the error code (Table 2). A server ignores STATUS in requests; a client ignores it in . . . _OK responses. |
| RESERVED |       1 | Senders MUST set it to 0. Receivers MUST ignore it.                                                                                                                               |
| LENGTH   |       4 | Number of payload bytes that follow, from 0 up to MAX_LEN = 16777216 (0x01000000, which is 2 24 ).                                                                                |

## Common Misconception: One send is one receive

TCP delivers a byte stream, not messages. The 8-byte header you send with one call may arrive in two pieces, or glued to the end of the previous message, or together with the next three. A receiver MUST read the header with a loop that keeps reading until it has exactly 8 bytes (the recv\_exact of Chapter 5, §5.8), then read exactly LENGTH more the same way. A single recv(8) works on your laptop most of the time and fails in grading.

## 4 Message Types

Requests go from client to server. Every request has exactly one response: its . . . \_OK type, which is the request type with the high bit set (TYPE | 0x80), or ERROR.

Table 1. ETP/1 message types. Every other TYPE value is undefined.

| TYPE   | Name     | Direction   | Payload                                                 |
|--------|----------|-------------|---------------------------------------------------------|
| 0x01   | HELLO    | C→S         | Client name, 1-32 printable ASCII bytes (0x21-0x7E)     |
| 0x81   | HELLO_OK | S→C         | Server name, 1-64 printable ASCII bytes (0x20-0x7E)     |
| 0x02   | LIST     | C→S         | Empty                                                   |
| 0x82   | LIST_OK  | S→C         | The listing, Section 6.2                                |
| 0x03   | GET      | C→S         | A file name (Section 7)                                 |
| 0x83   | GET_OK   | S→C         | The file's contents                                     |
| 0x04   | PUT      | C→S         | NAMELEN (2 bytes), name, file contents (Section 6.4)    |
| 0x84   | PUT_OK   | S→C         | The 32-byte SHA-256 digest of DATA as received          |
| 0x05   | BYE      | C→S         | Empty                                                   |
| 0x85   | BYE_OK   | S→C         | Empty                                                   |
| 0xFF   | ERROR    | S→C         | Human-readable text, 0-200 bytes; the code is in STATUS |

## 5 Sessions

A session is one connection. It starts in state AWAIT\_HELLO.

<!-- image -->

LIST, GET, PUT or BYE first: NOT\_READY; or a fatal ERROR; or the client disconnects

Figure 3. Session states at the server.

1. The first request on a session MUST be HELLO. Any other request type (0x02-0x05) arriving in AWAIT\_HELLO is answered with ERROR NOT\_READY and the server closes the connection. Header errors and other types are handled first, exactly as in Section 8.1: a TYPE outside 0x01-0x05, or a HELLO with a bad name, gets a non-fatal ERROR and the session stays in AWAIT\_HELLO.
2. In READY, the client may send any number of LIST, GET and PUT requests, then BYE.
3. Ordering. A server MUST process the requests on one connection in the order they arrive and send exactly one response to each request it processes, in the same order. After a fatal error it processes nothing further. The clients in this course send one request and wait for its response, but a server MUST NOT assume that: several complete requests may arrive in a single read.
4. Closing. After sending BYE\_OK the server closes the connection. The client waits until it sees the server's close (a read returns end-of-stream) and then closes its own side. The server is therefore the side that performs the active close and holds the TIME-WAIT state: for about a minute after closing, Linux keeps the old connection's address and port pair reserved so that delayed segments from it cannot be mistaken for a new connection (Chapter 5, §5.5.3).
5. If the client's connection ends without BYE - cleanly between messages, or abruptly in the middle of one - the server abandons any partial request, sends nothing, releases the connection, and carries on serving everyone else.

## 6 Requests

## 6.1 HELLO

Payload: the client's name, 1-32 bytes, each in 0x21-0x7E (printable ASCII, no spaces). The client sends the --name it was given, unchecked; the server's answer decides.

The server replies HELLO\_OK with its own name (1-64 bytes, each in 0x20-0x7E). A name that breaks the rule, or a second HELLO on a session already in READY, is answered with ERROR

BAD\_REQUEST (non-fatal; the state does not change).

## 6.2 LIST

Payload: empty. A non-empty payload is answered with ERROR BAD\_REQUEST.

LIST\_OK payload: one line per file in the root, each line the file name, one TAB byte (0x09), the file size in bytes as a decimal number with no leading zeros (0 for an empty file), and one LF byte (0x0A). The lines MUST be sorted by name in ascending byte order - so Zulu.txt sorts before alpha.txt, because Z is 0x5A and a is 0x61. The listing includes only entries that are regular files and whose names are valid ETP names (Section 7); directories, symbolic links and anything else are left out. An empty root gives an empty payload. If the root cannot be read, or the listing would exceed MAX\_LEN, the reply is SERVER\_ERROR. A file larger than MAX\_LEN is listed, but cannot be fetched (GET answers SERVER\_ERROR).

## 6.3 GET

Payload: the name of the file, with no terminator. The server checks, in this order: an invalid name gives ERROR BAD\_NAME; a name that is not a regular file in the root gives NOT\_FOUND; a file too large for one message, or one that cannot be read, gives SERVER\_ERROR. Otherwise the server replies GET\_OK whose payload is the file's entire contents. All three errors are non-fatal.

## 6.4 PUT

Figure 4. The PUT payload. NAMELEN is big-endian.

| NAMELEN 2 bytes   | NAME NAMELEN bytes   | DATA LENGTH - 2 - NAMELEN bytes   |
|-------------------|----------------------|-----------------------------------|

The server checks, in this order: if LENGTH &lt; 2, or NAMELEN &gt; LENGTH - 2, the reply is BAD\_REQUEST; an invalid name gives BAD\_NAME; a failure to store gives SERVER\_ERROR. All three are non-fatal. Otherwise the server stores DATA under that name in its root, replacing any existing file of that name, and replies PUT\_OK whose 32-byte payload is the SHA-256 digest of DATA. An empty DATA is legal and stores an empty file.

If the name exists but is not a regular file (a directory, say), the reply is SERVER\_ERROR; if it is a symbolic link, the link itself is replaced, never its target.

The server SHOULD write to a temporary file in the root and rename it into place, so a concurrent GET never sees half a file. The temporary name MUST NOT be a valid ETP name (start it with a period), so it is never listed or fetched, and it is removed if the store fails. If two clients PUT the same name at once, the last rename wins.

The client MUST compute the SHA-256 of the data it sent and compare it with the digest it receives. A mismatch means the file did not arrive intact (Section 10). The digest covers DATA exactly as received; the server need not read the file back.

## 6.5 BYE

Payload: empty (otherwise BAD\_REQUEST). The server replies BYE\_OK and then closes the connection, as in Section 5.

## 7 File Names

A valid ETP name is 1 to 64 bytes, every byte one of A-Z, a-z, 0-9, period ., underscore \_ or hyphen -, and the first byte is not a period. As a regular expression:

```
^[A-Za-z0-9_-][A-Za-z0-9._-]{0,63}$
```

The pattern must match the whole name. In Python, use re.fullmatch, or end the pattern with \Z: a plain $ also matches just before a final newline, so re.match would accept alpha.txt followed by a newline. In C, check every byte against the rule; never treat a name as a C string, because alpha.txt followed by a zero byte and more text is not a valid name.

| Name                                                                                                                       | Valid?       | Why                                                                                                                                                                         |
|----------------------------------------------------------------------------------------------------------------------------|--------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| report-v2.pdf, a, Zulu.txt, x..y ../secret, dir/file .hidden, ., .. my file.txt, résumé.txt the empty name; a 65-byte name | yes no no no | only allowed bytes; does not start with a period / is not allowed: no way out of the root starts with a period space and non-ASCII bytes are not allowed outside 1-64 bytes |
|                                                                                                                            | no           |                                                                                                                                                                             |

The rule is deliberately strict. Because no valid name contains / or starts with a period, joining a valid name to the root path can never point outside the root. Check the name before you build a path from it.

## 8 Errors

Table 2. Error codes, carried in the STATUS byte of an ERROR response.

|   Code | Name         | Fatal?   | When                                                                           |
|--------|--------------|----------|--------------------------------------------------------------------------------|
|      1 | BAD_VERSION  | yes      | VERSION is not 1                                                               |
|      2 | BAD_TYPE     | no       | TYPE is not a request type (0x01-0x05)                                         |
|      3 | NOT_FOUND    | no       | GET names no regular file in the root                                          |
|      4 | BAD_NAME     | no       | a GET or PUT name breaks Section 7                                             |
|      5 | TOO_LARGE    | yes      | LENGTH exceeds MAX_LEN                                                         |
|      6 | BAD_REQUEST  | no       | a payload is malformed for its type; a duplicate HELLO                         |
|      7 | NOT_READY    | yes      | a request other than HELLO arrives in AWAIT_HELLO                              |
|      8 | SERVER_ERROR | no       | the server failed (a file it cannot read or write, a file larger than MAX_LEN) |

## 8.1 Order of checks

When a server has read a header, it checks in this order and stops at the first problem:

1. VERSION ̸= 1: BAD\_VERSION, fatal.
2. LENGTH &gt; MAX\_LEN: TOO\_LARGE, fatal. The server MUST NOT try to allocate or read that payload.
3. Read the LENGTH-byte payload.
4. TYPE is not a request type: BAD\_TYPE, non-fatal. (The payload has been read and is discarded, so the stream is still in step.)
5. State is AWAIT\_HELLO and TYPE is not HELLO: NOT\_READY, fatal.
6. The checks belonging to that request type, in the order given in its subsection.

## 8.2 Fatal and non-fatal

For a fatal error the server sends the ERROR response and then closes the connection; it need not process anything further. Closing a socket that still has unread bytes waiting makes TCP send a reset, which on some systems can discard the ERROR before the client reads it. So the transport's close SHOULD shut down its sending side (shutdown(SHUT\_WR)), read and discard whatever is still arriving until end-of-stream or about a second passes, and only then close. That logic belongs inside close in your transport file, not in your server. A client MAY therefore see a reset instead of the ERROR after a fatal error, and treats it as exit status 2. For a non-fatal error the server sends the ERROR response and the session continues in the same state: the request's whole payload has been consumed, so the next byte is the start of the next request.

The ERROR payload is UTF-8 text of at most 200 bytes, for people to read. Programs MUST NOT make decisions based on it - use the code.

## 9 The Server Program

```
./etp-server --port PORT --root DIR [--bind ADDR]
```

- --port and --root are required. --bind defaults to 127.0.0.1: the server listens on loopback unless told otherwise, which keeps it inside the course's authorised scope.
- If an argument is missing or invalid (a non-numeric port, a port outside 1-65535, a DIR that is not a directory, an unknown option), or the port cannot be bound, the server prints a message on standard error and exits with a non-zero status.
- The server runs until it is killed (SIGINT or SIGTERM). No clean-up is required.
- Concurrency. The server MUST serve at least 16 simultaneous sessions, and a session whose client has stalled part-way through a message MUST NOT delay any other session. One thread per connection is the expected design; an event loop is also fine. Serving one connection at a time is not.
- Robustness. A client that vanishes at any moment - including while the server is in the middle of sending it 2 MiB - affects only its own session. The server process MUST NOT exit, and it MUST release the connection.
- Restart. The server MUST be able to restart on the same port immediately, while old connections are still in TIME-WAIT.
- Files. The server serves only regular files directly inside its root. A symbolic link is never a regular file for ETP purposes: it is not listed, and GET answers NOT\_FOUND.

- Idle sessions. A server MAY close, without sending anything, a session from which no byte has arrived for 60 seconds.
- Logging. The server MUST write one line to standard output for every response it sends (including ERRORs), and flush it. Standard output carries nothing but these lines; any other message goes to standard error. Lines from different sessions MUST NOT interleave. The fields, separated by single spaces, are: the local time when the response is sent, as YYYY-MM-DDTHH:MM:SS.mmm; the client's address and port as address:port; the request's type name (HELLO, . . . , BYE), or 0x and two hex digits for any TYPE outside 0x01-0x05; the status code sent (0 for success); and the LENGTH from the request's header, even if the payload was never read:

```
2026-11-02T14:03:11.412 127.0.0.1:51544 GET 0 9
```

```
2026-11-02T14:03:12.007 127.0.0.1:51546 0x42 2 5
```

## Practitioner Note: Three traps every year

"Address already in use" on restart. The server performs the active close, so its port is held in TIME-WAIT after each BYE. Set SO\_REUSEADDR on the listening socket before bind().

The server dies when a client disconnects. In C, writing to a connection the peer has reset raises SIGPIPE, which kills the process by default. Pass MSG\_NOSIGNAL to send() or ignore the signal with signal(SIGPIPE, SIG\_IGN), then handle the EPIPE error. Python raises BrokenPipeError or ConnectionResetError instead; catch them per connection.

One slow client freezes everyone. If your accept loop handles a connection before accepting the next, a client that sends half a header holds the whole server hostage. That is a denial-of-service in miniature (Chapter 5, §5.9).

## 10 The Client Program

```
./etp-client --host HOST --port PORT --name NAME list ./etp-client --host HOST --port PORT --name NAME get REMOTE LOCAL ./etp-client --host HOST --port PORT --name NAME put LOCAL REMOTE
```

All three options are required and come before the command, in any order. The client does not check NAME or REMOTE against the ETP rules: it sends them as given and the server's answer decides.

Each run is one session: connect; send HELLO with NAME; perform the one command; send BYE; wait for BYE\_OK and then for the server to close; close; exit. A reset instead of a clean close after BYE\_OK still counts as success. A client MAY give up on a silent server after a timeout of its choosing.

Checking a response. For each response header the client checks, in order: VERSION is 1; LENGTH is at most MAX\_LEN; TYPE is the expected . . . \_OK or ERROR. Only then does it read the payload. A PUT\_OK whose LENGTH is not 32 is a protocol failure.

| Command          | On success                                                                                                                                                                         |
|------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| list             | Writes the LIST_OK payload to standard output exactly, byte for byte, and nothing else.                                                                                            |
| get REMOTE LOCAL | Writes the GET_OK payload to the local file LOCAL, replacing it if it exists. On any failure, LOCAL is not created or changed.                                                     |
| put LOCAL REMOTE | Sends the contents of LOCAL stored as REMOTE, checks the digest, and prints the digest on standard output as 64 lowercase hexadecimal digits followed by one LF, and nothing else. |

Diagnostics and progress messages go to standard error, never standard output.

|   Exit | Meaning                                                                                                                                                                                                                                                                             |
|--------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|      0 | The command succeeded.                                                                                                                                                                                                                                                              |
|      1 | The server answered with ERROR. Print the code and the text on standard error. If the code is a non-fatal one from Table 2 and the failed request was not HELLO, the session is still open in READY: the client SHOULD still send BYE and close normally. Otherwise it just closes. |
|      2 | Anything else went wrong: bad arguments, cannot connect, the connection ended early, a response that fails the checks above, a local file that cannot be read or written.                                                                                                           |
|      3 | put only: the PUT_OK digest does not match the SHA-256 of the data sent. (The client still sends BYE; the exit status stays 3.)                                                                                                                                                     |

## 11 The Transport Seam

Your server and client MUST reach the network only through a transport module that offers the six operations below, and nothing else in your code may use the operating system's socket interface. That means: in Python, the socket module; in C, the headers sys/socket.h, netinet/in.h and netdb.h, and the C library's own socket(), bind(), listen(), accept(), connect(), send(), recv() (and their to/from forms), setsockopt(), shutdown() and getaddrinfo(). Your seam's own functions are not the operating system's, even when they share a name: calling transport.listen() or tp\_accept() from your server is exactly the point. Byte-order conversion is not networking: arpa/inet.h for htonl and ntohl, and Python's struct, may be used anywhere. Your own test programs, kept in a tests/ folder or named test\_*, are exempt. In PA1 the module wraps TCP. In the final project you will write a second module with the same six operations over your PA2 transport, and switch to it without touching your ETP code. If the seam is clean, that switch is an afternoon. If socket calls are scattered through your server, it is a rewrite.

The C starter declares the operations in transport.h and defines them in transport\_tcp.c. In the Python starter they are written in transport\_tcp.py, and your programs import them through transport.py, whose one line chooses the transport: in the project you change that line and nothing else. You may change the signatures to suit your design, but keep the six operations, keep them in files whose names begin with transport, and keep every socket call inside those files.

Table 3. Client exit status.

Table 4. The six operations of the transport seam, as the starter kits name them.

| Operation (Python name)                  | C name                 | Meaning                                                                                                                                                                                         |
|------------------------------------------|------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| listen(addr, port)                       | tp_listen              | Start accepting sessions on addr:port. Returns a listener.                                                                                                                                      |
| accept(listener)                         | tp_accept              | Wait for the next session. Returns a connection and the peer's address and port, for logging.                                                                                                   |
| connect(host, port) send_all(conn, data) | tp_connect tp_send_all | Open a session to a server. Returns a connection. Hand every byte to the transport, in order, or report                                                                                         |
| recv_exact(conn, n)                      | tp_recv_exact          | failure. Never a partial send. Return exactly n bytes. If the stream ends before any of them arrives, report a clean close (the peer finished between messages); if it ends part-way, report an |
| close(conn)                              |                        | error. Finish the session gracefully: shut down the sending side, read and discard until end-of-stream or about a second passes, then close (Section 8). A seventh                              |
|                                          | tp_close               | helper to close the listener is fine.                                                                                                                                                           |

## 12 Worked Example

One session, every byte. The client is named eagle01; the root holds Zulu.txt (5 bytes) and alpha.txt, whose 12 bytes are Hello, ETP! and a newline. The client lists the root, fetches alpha.txt, stores Go Eagles! plus a newline as notes.txt, asks for a file that does not exist, and says goodbye. The server's name and the error text are free-form; yours will differ, and so will those messages' lengths. In each message the first 8 bytes are the header. This table was produced by the reference encoder, not typed.

| Dir   | Message   | Bytes   | On the wire (hex)   | On the wire (hex)   | On the wire (hex)   | On the wire (hex)   | On the wire (hex)   | On the wire (hex)   | On the wire (hex)   | On the wire (hex)   | On the wire (hex)   | On the wire (hex)   | On the wire (hex)   | On the wire (hex)   | On the wire (hex)   | On the wire (hex)   | On the wire (hex)   | On the wire (hex)   |
|-------|-----------|---------|---------------------|---------------------|---------------------|---------------------|---------------------|---------------------|---------------------|---------------------|---------------------|---------------------|---------------------|---------------------|---------------------|---------------------|---------------------|---------------------|
| C→S   | HELLO     | 15      | 01                  | 01                  | 00                  | 00                  | 00                  | 00                  | 00                  | 07                  | 65                  | 61                  | 67                  | 6c                  | 65                  | 30                  | 31                  |                     |
| S→C   | HELLO_OK  | 32      | 01 72               | 81 65               | 00 6e               | 00 63               | 00 65               | 00 20               | 00 73               | 18 65               | 45 72               | 54 76               | 50 65               | 20 72               | 72 20               | 65 31               | 66 2e               | 65 30               |
| C→S   | LIST      | 8       | 01                  | 02                  | 00                  | 00                  | 00                  | 00                  | 00                  | 00                  |                     |                     |                     |                     |                     |                     |                     |                     |
| S→C   | LIST_OK   | 32      | 01 09               | 82 35               | 00 0a               | 00 61               | 00 6c               | 00 70               | 00 68               | 18 61               | 5a 2e               | 75 74               | 6c 78               | 75 74               | 2e 09               | 74 31               | 78 32               | 74 0a               |
| C→S   | GET       | 17      | 01 74               | 03                  | 00                  | 00                  | 00                  | 00                  | 00                  | 09                  | 61                  | 6c                  | 70                  | 68                  | 61                  | 2e                  | 74                  | 78                  |
| S→C   | GET_OK    | 20      | 01 54               | 83 50               | 00 21               | 00 0a               | 00                  | 00                  | 00                  | 0c                  | 48                  | 65                  | 6c                  | 6c                  | 6f                  | 2c                  | 20                  | 45                  |
| C→S   | PUT       | 30      | 01 74               | 04 78               | 00 74               | 00 47               | 00 6f               | 00 20               | 00 45               | 16 61               | 00 67               | 09 6c               | 6e 65               | 6f 73               | 74 21               | 65 0a               | 73                  | 2e                  |
| S→C   | PUT_OK    | 40      | 01 ee 28            | 84 c1 a2            | 00 32 5e            | 00 13 7d            | 00 8d 2f            | 00 8d 66            | 00 be b7            | 20 96 bf            | 1c 50               | 94 71               | 1d 7a               | ab 75               | 3d ca               | 13 d2               | 2a f2               | 68 8f               |
| C→S   | GET       | 19      | 01 74               | 03 78               | 00 74               | 00                  | 00                  | 00                  | 00                  | 0b                  | 6d                  | 69                  | 73                  | 73                  | 69                  | 6e                  | 67                  | 2e                  |
|       | ERROR     | 20      | 01                  | ff                  | 03                  | 00                  | 00                  | 00                  | 00                  | 0c                  | 6e                  | 6f                  | 20                  | 73                  | 75                  | 63                  | 68                  |                     |
| S→C   |           |         | 66                  | 69                  | 6c                  | 65                  |                     |                     | 00                  |                     |                     |                     |                     |                     |                     |                     |                     | 20                  |
| C→S   | BYE       | 8       | 01                  | 05                  | 00                  | 00                  | 00                  | 00                  |                     | 00                  |                     |                     |                     |                     |                     |                     |                     |                     |

| Dir   | Message   | Bytes On the wire (hex)   |
|-------|-----------|---------------------------|
| S→C   | BYE_OK    | 8 01 85 00 00 00 00 00 00 |

Points worth checking against your own encoder:

- HELLO: 01 01 00 00 then LENGTH 00 00 00 07, then the seven bytes of eagle01.
- LIST\_OK: LENGTH 0x18 = 24, which is Zulu.txt\t5\n (11) plus alpha.txt\t12\n (13).
- PUT: LENGTH 0x16 = 22 = 2 (NAMELEN) + 9 (notes.txt) + 11 (data). NAMELEN is 00 09.
- PUT\_OK: the payload is SHA-256(Go Eagles!\n) = 1c941dab...2f66b7bf. Check yours with printf 'Go Eagles!\n' | sha256sum.
- ERROR: TYPE 0xFF, STATUS 0x03 (NOT\_FOUND). The session continues, so BYE follows.

## 13 Security Considerations

## Threat Model

Everything is in the clear. Anyone who can see the traffic reads every file name, every file, and every client name, and could alter them in flight. The SHA-256 digest in PUT\_OK detects accidental corruption; it does not stop an attacker who can rewrite both the data and the digest. Confidentiality and integrity against an attacker is one of the project extensions.

There is no authentication. The client name is a label, not an identity. Any client may read or overwrite any file in the root.

Resource exhaustion. One PUT may ask the server to hold 16 MiB in memory, and nothing limits the number of connections. A real server would cap connections, stream large payloads to disk, and time out idle sessions (Section 9 allows the last).

Path traversal is prevented only because Section 7 is strict and the server checks names before using them. Loosen the rule and the root is no longer a boundary.

Scope. Run your server on loopback or inside your Lab 0 virtual machine. The course's authorised-scope rules (syllabus) apply to everything you build here.

## 14 Change Log

|   Version | Date        | Change                                                                                                                                  |
|-----------|-------------|-----------------------------------------------------------------------------------------------------------------------------------------|
|       1.0 | 20 Oct 2026 | First issue. Reviewed before release by an independent implementation writ- ten from this document alone, and by an independent reader. |