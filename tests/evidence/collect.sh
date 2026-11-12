#!/usr/bin/env bash
# Run from the repository root inside the disposable Linux evidence container.
# Keep large random fixtures in ignored directories; stage evidence until verified.
set -euo pipefail
out=scratch/evidence-run
mkdir -p "$out" scratch server-files evidence
exec > >(tee "$out/collection.log") 2>&1
set -x

server_pid=
capture_pid=
cleanup() {
    if [[ -n "$capture_pid" ]]; then
        kill -INT "$capture_pid" 2>/dev/null || true
        wait "$capture_pid" 2>/dev/null || true
    fi
    if [[ -n "$server_pid" ]]; then
        kill -TERM "$server_pid" 2>/dev/null || true
        wait "$server_pid" 2>/dev/null || true
    fi
}
trap cleanup EXIT

date -u --iso-8601=ns
{
    date -u --iso-8601=ns
    uname -a
    cat /etc/os-release
    python3 --version
    tcpdump --version
    ss --version
    apk info -v
    ip -details link show lo
    ip route get 127.0.0.1
    git rev-parse HEAD
    git status --short
    sha256sum src/*.py etp-client etp-server tests/course/etp_selfcheck.py tests/evidence/collect.sh
} > "$out/environment.txt" 2>&1
make build
head -c 262144 /dev/urandom > scratch/photo.bin

./etp-server --port 5000 --root server-files > "$out/server.log" 2>&1 &
server_pid=$!
# Inspect the listening socket without making an extra TCP connection.
for attempt in {1..100}; do
    kill -0 "$server_pid"
    if [[ -n "$(ss -H -ltn 'sport = :5000')" ]]; then break; fi
    sleep 0.05
done
test -n "$(ss -H -ltn 'sport = :5000')"

tcpdump -i lo -s 200 -U -w "$out/pa1-capture.pcap" 'tcp port 5000' > "$out/tcpdump.log" 2>&1 &
capture_pid=$!
for attempt in {1..100}; do
    kill -0 "$capture_pid"
    if grep -q 'listening on lo' "$out/tcpdump.log"; then break; fi
    sleep 0.05
done
grep -q 'listening on lo' "$out/tcpdump.log"

./etp-client --host 127.0.0.1 --port 5000 --name eagle01 put scratch/photo.bin photo.bin | tee "$out/put.stdout"
./etp-client --host 127.0.0.1 --port 5000 --name eagle01 get photo.bin scratch/copy.bin
date -u --iso-8601=ns > "$out/time-wait-collected-at.txt"
ss -tan state time-wait '( sport = :5000 or dport = :5000 )' > "$out/time-wait.txt"
ss -tano state time-wait '( sport = :5000 or dport = :5000 )' > "$out/time-wait-timers.txt"

{
    cmp scratch/photo.bin scratch/copy.bin
    echo 'cmp source/download: PASS'
    cmp scratch/photo.bin server-files/photo.bin
    echo 'cmp source/server: PASS'
    wc -c scratch/photo.bin server-files/photo.bin scratch/copy.bin
    sha256sum scratch/photo.bin server-files/photo.bin scratch/copy.bin
} > "$out/integrity.txt"

# Give libpcap time to drain its kernel ring before requesting its final stats.
sleep 1
kill -INT "$capture_pid"
wait "$capture_pid"
capture_pid=
kill -TERM "$server_pid"
wait "$server_pid" || test "$?" -eq 143
server_pid=
chmod 644 "$out/pa1-capture.pcap" "$out/time-wait.txt"
python3 tests/evidence/verify.py --evidence "$out"
date -u --iso-8601=ns
