# Collect and verify PA1 evidence

Run from the repository root with Docker running:

```bash
docker build -t networkingp1-evidence:local -f tests/evidence/Dockerfile .
docker run --rm --name networkingp1-evidence-capture --network none \
  --mount "type=bind,source=$PWD,target=/workspace" \
  networkingp1-evidence:local bash tests/evidence/collect.sh
```

The container uses an isolated Linux loopback interface. It needs no published
ports, host packet-capture permission, or privileged-container mode. Package
installation happens during the image build; collection has no external network.

The script overwrites its test fixtures at `scratch/photo.bin`,
`scratch/copy.bin`, and `server-files/photo.bin`. It stages a new capture and
logs in `scratch/evidence-run/`; it does not replace submitted evidence.
It exits unsuccessfully if collection, comparisons, or verification fail.

The verifier requires the retained random files, which must stay untracked:

```bash
python3 tests/evidence/verify.py --evidence scratch/evidence-run
```

After reviewing a successful run, copy its files into `evidence/`, record the
image ID with `docker image inspect networkingp1-evidence:local --format '{{.Id}}'`,
and update `evidence/ANALYSIS.md` to the new ports, ISNs, frame numbers, lengths,
hashes, and timestamps. Then run:

```bash
python3 tests/evidence/verify.py --evidence evidence --analysis evidence/ANALYSIS.md
python3 tests/course/etp_selfcheck.py -v
python3 -m unittest discover -s tests
```

`verification.json` is written only after all checks pass. It records both
sessions, complete handshakes, continuous sequence ranges, captured payload
agreement with the actual files, both FINs and final ACKs, zero capture drops,
matching file/PUT hashes, server TIME-WAIT rows and timers, and the snapshot's
delay after GET. Supplying `--analysis` also checks all eight facts.

Snaplen 200 deliberately truncates file contents. Completeness therefore uses
packet length/sequence coverage together with full-file `cmp` and SHA-256
checks. The capture alone does not prove every omitted file byte. Rerunning
collection produces new random data and measurements; retain the matching
fixtures until the evidence has been reviewed.
