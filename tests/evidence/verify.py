#!/usr/bin/env python3
"""Verify this controlled PUT/GET run against retained files and packet evidence.

The course parser supplies frame fields; these stricter checks require both
sessions, uninterrupted sequence ranges, final ACKs, captured-byte agreement
with the real files, matching hashes, and timely TIME-WAIT evidence.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct


def require(condition, message):
    if not condition:
        raise ValueError(message)


def frame(kind, payload=b""):
    return struct.pack("!BBBBI", 1, kind, 0, 0, len(payload)) + payload


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence", default="evidence")
    ap.add_argument("--analysis", help="Also compare the analysis facts with the capture")
    args = ap.parse_args()
    out = Path(args.evidence)
    # A failed recheck must not leave a previous PASS report beside new inputs.
    (out / "verification.json").unlink(missing_ok=True)
    spec = importlib.util.spec_from_file_location("course_checker", "tests/course/etp_selfcheck.py")
    course = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(course)

    paths = [Path(p) for p in ("scratch/photo.bin", "server-files/photo.bin", "scratch/copy.bin")]
    blobs = [p.read_bytes() for p in paths]
    require(all(b == blobs[0] for b in blobs), "source, server, and download differ")
    data = blobs[0]
    require(len(data) == 262144, "fixture must be exactly 256 KiB")
    digest = hashlib.sha256(data).digest()
    require((out / "put.stdout").read_text().strip() == digest.hex(), "PUT digest differs from source")
    integrity = (out / "integrity.txt").read_text()
    require("cmp source/download: PASS" in integrity and "cmp source/server: PASS" in integrity,
            "missing successful cmp results")
    for path in paths:
        require(f"{digest.hex()}  {path}" in integrity, f"missing recorded hash for {path}")

    cap = out / "pa1-capture.pcap"
    pkts, snaplen = course.read_capture(cap)
    require(snaplen == 200 and cap.stat().st_size < 5 * 1024 * 1024, "capture size/snaplen invalid")
    conns = course.connections(pkts)
    require(len(conns) == 2, "expected exactly PUT and GET sessions")
    require(sum(len(c["pkts"]) for c in conns) == len(pkts), "unassociated packets")
    capture_log = (out / "tcpdump.log").read_text()
    require(re.search(r"^0 packets dropped by kernel$", capture_log, re.M), "capture reported drops")
    require(re.search(rf"^{len(pkts)} packets captured$", capture_log, re.M), "capture packet count differs")

    hello = frame(1, b"eagle01")
    hello_ok = frame(0x81, b"ETP reference server 1.0")
    name = b"photo.bin"
    streams = [
        (hello + frame(4, struct.pack("!H", len(name)) + name + data) + frame(5),
         hello_ok + frame(0x84, digest) + frame(0x85)),
        (hello + frame(3, name) + frame(5), hello_ok + frame(0x83, data) + frame(0x85)),
    ]
    sessions = []
    for label, c, (client_stream, server_stream) in zip(("PUT", "GET"), conns, streams):
        packets = c["pkts"]
        s = course.summarize(c)
        require(s["server_port"] == 5000 and c["client"][0] == c["server"][0] == "127.0.0.1",
                f"{label}: unexpected endpoints")
        require(not s["rst"] and s["fin_from_both"] and s["first_fin_from"] == "server",
                f"{label}: unclean close")
        syn, synack, ack = packets[:3]
        require([p.flags & 0x17 for p in packets[:3]] == [2, 18, 16], f"{label}: handshake flags")
        require(synack.ack == (syn.seq + 1) % 2**32 and ack.seq == synack.ack
                and ack.ack == (synack.seq + 1) % 2**32, f"{label}: handshake sequence/ACK")
        captured_bytes = 0
        for endpoint, isn, expected in ((c["client"], syn.seq, client_stream),
                                        (c["server"], synack.seq, server_stream)):
            next_offset = 0
            for p in packets:
                if (p.src, p.sport) != endpoint or not p.plen:
                    continue
                offset = (p.seq - isn - 1) % 2**32
                require(offset == next_offset, f"{label} frame {p.frame}: gap/overlap/retransmission")
                require(p.payload == expected[offset:offset + len(p.payload)],
                        f"{label} frame {p.frame}: captured bytes differ from expected file/protocol")
                next_offset += p.plen
                captured_bytes += len(p.payload)
            require(next_offset == len(expected), f"{label}: incomplete stream byte count")
        fins = [p for p in packets if p.flags & 1]
        require(len(fins) == 2 and fins[1].sport == c["client"][1], f"{label}: FIN order/count")
        require(fins[0].seq == (synack.seq + 1 + len(server_stream)) % 2**32
                and fins[1].seq == (syn.seq + 1 + len(client_stream)) % 2**32,
                f"{label}: FIN does not follow the full stream")
        final = packets[-1]
        require(final.frame > fins[1].frame and final.sport == 5000 and final.flags & 0x17 == 16
                and final.ack == (fins[1].seq + 1) % 2**32
                and final.seq == (fins[0].seq + 1) % 2**32
                and fins[1].ack == final.seq, f"{label}: missing final FIN acknowledgment")
        sessions.append({
            "operation": label,
            "summary": {k: v.hex() if isinstance(v, bytes) else v for k, v in s.items()},
            "handshake": [{"frame": p.frame, "seq": p.seq, "ack": p.ack, "flags": p.flags}
                          for p in packets[:3]],
            "fin_frames": [p.frame for p in fins], "final_ack_frame": final.frame,
            "first_timestamp_utc": datetime.fromtimestamp(syn.ts, timezone.utc).isoformat(),
            "last_timestamp_utc": datetime.fromtimestamp(final.ts, timezone.utc).isoformat(),
            "captured_payload_bytes_checked": captured_bytes,
            "data_frames": [{"frame": p.frame, "direction": "server" if p.sport == 5000 else "client",
                             "seq": p.seq, "payload_bytes": p.plen, "captured_payload_bytes": len(p.payload)}
                            for p in packets if p.plen],
        })
    require(conns[0]["pkts"][-1].ts <= conns[1]["syn"].ts, "GET precedes completed PUT")

    time_wait = (out / "time-wait.txt").read_text()
    timers = (out / "time-wait-timers.txt").read_text()
    observed = datetime.fromisoformat((out / "time-wait-collected-at.txt").read_text().strip()).timestamp()
    for c in conns:
        port = c["client"][1]
        require(re.search(rf"127\.0\.0\.1:5000\s+127\.0\.0\.1:{port}\b", time_wait),
                f"missing server TIME-WAIT for client {port}")
        require(re.search(rf"127\.0\.0\.1:5000\s+127\.0\.0\.1:{port}\s+timer:\(timewait,", timers),
                f"missing live TIME-WAIT timer for client {port}")
        require(0 <= observed - c["pkts"][-1].ts < 60, "TIME-WAIT snapshot was not within 60 seconds")

    facts_checked = False
    if args.analysis:
        facts = course.parse_facts(Path(args.analysis).read_text())
        require(facts is not None and set(facts) == set(course.FACT_KEYS), "analysis facts incomplete")
        actual = course.summarize(conns[1])
        require(all(str(actual[k]) == facts[k] for k in course.FACT_KEYS), "analysis facts differ from capture")
        facts_checked = True

    report = {
        "status": "PASS", "capture_sha256": hashlib.sha256(cap.read_bytes()).hexdigest(),
        "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "analysis_sha256": hashlib.sha256(Path(args.analysis).read_bytes()).hexdigest() if args.analysis else None,
        "capture_bytes": cap.stat().st_size, "snaplen": snaplen, "frames": len(pkts),
        "fixture_bytes": len(data), "fixture_sha256": digest.hex(),
        "identical_files": [str(p) for p in paths], "put_digest_matches": True,
        "all_captured_payload_prefixes_match_expected_streams": True,
        "sequence_gaps_overlaps_or_retransmissions": 0, "kernel_capture_drops": 0,
        "time_wait_seconds_after_get": round(observed - conns[1]["pkts"][-1].ts, 6),
        "analysis_facts_match": facts_checked, "sessions": sessions,
    }
    (out / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS: {len(pkts)} frames; complete PUT and GET; matching 256 KiB files and SHA-256; "
          f"both server TIME-WAIT rows; analysis facts checked={facts_checked}")


if __name__ == "__main__":
    main()
