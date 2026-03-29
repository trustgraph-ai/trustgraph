# Security Policy

TrustGraph is an open-source AI graph processing pipeline. We take security
seriously and appreciate the responsible disclosure of vulnerabilities by the
community.

## Supported Versions

Security updates are only provided for the latest stable release line.
Versions prior to 2.0.0 are end-of-life and will not receive security patches.

| Version   | Supported          |
| --------- | ------------------ |
| >= 2.0.0  | :white_check_mark: |
| < 2.0.0   | :x:                |

If you are running a version older than 2.0.0, we strongly recommend upgrading
to the latest 2.x release before reporting a vulnerability, as the issue may
already be resolved.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues,
pull requests, or discussions.** Doing so could expose users of TrustGraph to
risk before a fix is available.

Instead, report security vulnerabilities by emailing the TrustGraph security
team directly:

📧 **[info@trustgraph.ai](mailto:info@trustgraph.ai)**

Please include as much of the following information as possible to help us
triage and resolve the issue quickly:

- A clear description of the vulnerability and its potential impact
- The affected component(s) and version(s) of TrustGraph
- Step-by-step instructions to reproduce the issue
- Proof-of-concept code or a minimal reproducing example (if applicable)
- Any suggested mitigations or patches (if you have them)

## What to Expect

After submitting a report, you can expect the following process:

1. **Acknowledgement** — We will acknowledge receipt of your report within
   **72 hours**.
2. **Assessment** — We will investigate and assess the severity of the
   vulnerability within **7 days** of acknowledgement.
3. **Updates** — We will keep you informed of our progress. If we need
   additional information, we will reach out to you directly.
4. **Resolution** — Once a fix is developed and validated, we will coordinate
   with you on the disclosure timeline before publishing a patch release.
5. **Credit** — With your permission, we will publicly credit your responsible
   disclosure in the release notes accompanying the fix.

## Severity Assessment

We evaluate vulnerabilities using the
[CVSS v3.1](https://www.first.org/cvss/v3-1/) scoring system as a guide:

| Severity | CVSS Score | Target Response Time |
| -------- | ---------- | -------------------- |
| Critical | 9.0 – 10.0 | 48 hours             |
| High     | 7.0 – 8.9  | 7 days               |
| Medium   | 4.0 – 6.9  | 30 days              |
| Low      | 0.1 – 3.9  | 90 days              |

## Scope

The following are in scope for security reports:

- Core TrustGraph Python packages (`trustgraph`, `trustgraph-base`, etc.)
- The TrustGraph REST/graph gateway and processing pipeline components
- Docker and Kubernetes deployment configurations shipped in this repository
- Authentication, authorization, or data isolation issues

The following are **out of scope**:

- Third-party services or infrastructure not maintained by TrustGraph
- Issues in upstream dependencies (please report those to the respective
  project maintainers)
- Denial-of-service attacks requiring significant resources
- Social engineering attacks

## Preferred Languages

We prefer all security communications in **English**.

## Policy

TrustGraph follows the principle of
[Coordinated Vulnerability Disclosure (CVD)](https://vuls.cert.org/confluence/display/CVD).
We ask that you give us a reasonable amount of time to investigate and address
a reported vulnerability before any public disclosure.

---

_Last reviewed: March 2026_
