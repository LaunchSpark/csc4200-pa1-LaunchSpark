# Course checker

`etp_selfcheck.py` is the unmodified course checker formerly stored at
`project/etp_selfcheck.py`. Its SHA-256 is
`b60b91acb03a81b6df12b666e247ffd48d08cd69a4e5dce8b146a7fc4cc2eea9`.

It lives under `tests/` because its scripted peers intentionally use sockets;
the course transport-seam scanner excludes test directories. Application
socket calls remain confined to `src/transport_tcp.py`.

Run from the repository root with `python3 tests/course/etp_selfcheck.py -v`
or `make check`. The Makefile still prefers a course-installed checker at
`~/csc4200-course/project/etp_selfcheck.py` when available, and accepts a
`SELFCHECK` override.
