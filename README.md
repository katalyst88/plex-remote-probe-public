# plex-remote-probe-public

An external uptime probe for a personal Plex server, run from GitHub Actions.

## Why this exists

A media server cannot answer the one question that matters most about itself:
**can people outside the house actually watch?** Plex treats loopback and LAN as
local, and a home router hairpins its own public IP, so every test run *on the
box* passes while remote users stare at a spinner. The only honest test comes
from a machine out on the public internet — which is what an Actions runner is.

This repo is public purely so those runs are free. It contains nothing but the
probe workflows.

## Security

The Plex URL and token are GitHub encrypted secrets. They are never committed,
never printed, and never written to a job summary or output.

**GitHub masks a secret only when it appears verbatim in a log.** It cannot mask
a value *derived* from one — a parsed hostname, a substring, a hash. `probe.yml`
derives the bare hostname from the URL for DNS timing and deliberately never
prints it.

> **Never echo, print, or otherwise emit any value derived from `PLEX_URL` or
> `PLEX_TOKEN`.** On a public repo that publishes the endpoint permanently.

## Workflows

| Workflow | Purpose |
|---|---|
| `check.yml` | The health check. Connects, opens a movie, streams real video and verifies the MPEG-TS sync byte — a black screen still returns HTTP 200, so status codes alone would call a broken server healthy. Emits one `VERDICT_JSON` line. Runs every 3 hours and on demand. |
| `probe.yml` | Lower-level DNS / TCP / TLS / first-byte timing, for diagnosing *where* in the path a slowdown lives. |

## Interpreting a failure

Measure the connect time first. If TCP connect is slow but first-byte is fast,
the problem is the network path, not Plex — don't go tuning the media server.

This probe measures **capacity, not the speed of a single download**. The runner
sits in a US datacentre roughly 310 ms away, and one TCP stream over a path that
long is capped by `window / RTT` no matter how healthy the uplink is. It pulls
segments in parallel and reports headroom for that reason.
