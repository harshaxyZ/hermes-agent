# Security Hardening Features

This document outlines the security hardening features introduced to Hermes Agent. These protections are **opt-in via configuration**, **secure by default**, and designed to be **backward-compatible** so that existing setups continue to function without interruption.

---

## 1. Container Approval Policy

By default, containerized execution backends (Docker, Singularity, Modal, and Daytona) bypass interactive command approvals because the container itself acts as the primary execution sandbox. However, operators who require defense-in-depth within containers can progressive-tighten approvals.

### Configuration
In `config.yaml` (under the `approvals` namespace):

```yaml
approvals:
  container_mode: skip # Options: skip (default), warn, enforce
```

### Modes
- **`skip` (Default):** Bypasses all approval prompts inside container environments. Matches the legacy project behavior.
- **`warn`:** Bypasses standard warning prompts for dangerous command patterns, but strictly blocks unconditional security floors (hardline patterns, the operator-configured denylist, and sudo stdin attacks).
- **`enforce`:** Treats container environments identically to local/SSH execution backends. Requires full interactive user or gateway confirmation for any dangerous command execution.

---

## 2. Command Execution Denylist

Operators can define a custom list of command patterns that the agent is unconditionally prohibited from running. This is enforced at the same priority level as hardline patterns (survives yolo mode, container bypass modes, and disabled approvals).

### Configuration
In `config.yaml` (under the `security` namespace):

```yaml
security:
  command_denylist:
    - "docker run *"
    - "kubectl delete *"
    - "aws s3api *"
```

- Matches match-style globs (`*`, `?`, etc.) or exact command strings.
- Checked before all yolo, smart-approval, or container bypass flows.

---

## 3. File Read Denylist & Windows Device Blocking

Hermes Agent already prevents the reading of sensitive configuration files (e.g. `.env`, SSH keys) and UNIX system files. This feature adds Windows reserved device path blocking and supports custom file glob denylists.

### Windows Device Protection
Attempts to read or reference reserved Windows device names (e.g., `CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`) will be blocked in any path context, avoiding Windows-specific resource hangs.

### Custom File Read Denylist
In `config.yaml` (under the `security` namespace):

```yaml
security:
  file_read_deny_patterns:
    - "**/secrets/*"
    - "C:/Users/*/private_data/**"
```

- Checks paths against a custom list of globs.
- Rejects matching file read requests prior to execution.

---

## 4. Skill Integrity Verification

Skills persist across agent runs and sessions. To prevent "skill injection" attacks (where a malicious process or agent action silently modifies a skill file out-of-band to run arbitrary code in future sessions), Hermes can enforce cryptographic verification.

### How it Works
When enabled, Hermes writes a `.integrity.json` sidecar alongside the skill package directory on creation or update containing a SHA-256 digest of the files. On loading or modification, it verifies the digest. If out-of-band tampering is detected, execution/modification is refused.

### Configuration
In `config.yaml` (under the `skills` namespace):

```yaml
skills:
  require_frontmatter_hash: true # Default: false (for backward compatibility)
```
