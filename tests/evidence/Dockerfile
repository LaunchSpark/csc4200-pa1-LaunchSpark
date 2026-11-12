# Pin the Linux userspace used for evidence collection. Exact installed package
# versions and the host Linux kernel are recorded in environment.txt each run.
FROM alpine@sha256:294b683cb724975bec92580e1e685676bd4b50bda910ddb8c51d4cabeaec77e6
RUN apk add --no-cache python3 tcpdump iproute2 make git bash coreutils
WORKDIR /workspace
ENV TZ=UTC
RUN git config --global --add safe.directory /workspace
