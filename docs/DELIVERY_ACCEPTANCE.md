# Delivery acceptance

Adapted from `yniantongtian-oss/eda-agent`'s 0.5.0 delivery guide for this
fork's current package and CLI. A delivery is tied to an exact `main` commit,
the CI result for that commit, and the bytes of its downloadable artifacts.

## Automated gates

The `tests` workflow must finish successfully on the delivery commit:

1. The `test` matrix runs the full applicable suite on Python 3.11 and 3.12,
   including DelphiScript lint and bundle consistency.
2. `cross-validate` runs the Pascal/Python parity checks with Free Pascal.
3. `python-311` checks source compilation and an installed server import.
4. `package` builds a wheel and sdist, checks their payload and metadata,
   installs the wheel in a clean environment, and builds the EasyEDA `.eext`
   through that installed wheel's `eda-agent easyeda-extension build` command.

The package job uploads `eda-agent-dist-<commit-sha>` with exactly the wheel,
sdist, `eda-agent-bridge.eext`, and `SHA256SUMS.txt`. Its checksum file lists
the SHA-256 of each of the three deliverables. To reproduce the package gate
locally with Python 3.12 and Node.js on `PATH`:

```sh
python -m pip install build
python -m build
python scripts/verify_distribution.py dist
```

Compare the downloaded files against `SHA256SUMS.txt` before using them.
A successful local run proves the local build path; it does not substitute
for a hosted CI result on the exact commit. No completed hosted run is
recorded for this fork at the 2026-10-28 checkpoint.

## Editor acceptance

For Altium delivery, follow the applicable checks in
[`RELEASE_VERIFICATION.md`](RELEASE_VERIFICATION.md) on a disposable project.
Record the Altium version, `app_ping` script version and the commands whose
effects were saved and read back. For KiCad or EasyEDA Pro, exercise the
specific handoff workflow in the target editor using a disposable project;
[`BACKENDS.md`](BACKENDS.md) states each backend's live-verification limits.
Automated package checks do not establish editor behavior.

## Handoff record

Record the repository URL and commit SHA, package version, successful CI run,
artifact name and three checksums, target OS/Python/EDA versions, live checks
performed, and any relevant unverified path. The latest integrated upstream
and direct-child commits are recorded separately in
[`INTEGRATION-BASELINE.md`](INTEGRATION-BASELINE.md).
