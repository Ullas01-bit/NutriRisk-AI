# NutriRisk AI — Defensive Security Audit Report
**Framework**: Cloudflare `security-audit-skill`  
**Audit Target**: `d:\MAJOR PROJECT` (NutriRisk AI Clinical Decision Support System)  
**Audit Date**: October 23, 2026  
**Audit Status**: **COMPLETED & VALIDATED** (`validate-findings: PASS`, `validate-coverage-ledger: PASS`)

---

## 1. Executive Summary

This security audit was conducted using the **Cloudflare `security-audit-skill`** defensive assessment framework. The review comprehensively examined the full stack of **NutriRisk AI**, an AI-driven clinical malnutrition triaging and risk-stratification application.

The assessment covered:
- **Authentication & Authorization**: Scrypt password hashing, session cookies, Face ID biometric authentication, and 6-digit OTP passwordless verification.
- **Database & Persistence Layer**: SQLite parameterization, multi-tenant isolation, cascade rules, and administrative audit trails.
- **Defensive HTTP Middleware**: Cryptographic CSRF token validation and defense-in-depth HTTP security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Permissions-Policy).
- **Machine Learning & Deserialization**: Joblib model ingestion, canonical path traversal prevention (`validate_safe_model_path`), and feature parsing bounds.
- **Administrative Governance**: Role promotion/demotion guards, sole-admin protection, and self-demotion prevention.

### Audit Outcome Summary
- **Total Attack Surfaces Audited**: 6
- **Coverage Units Validated**: 6 (`coverage-ledger.json` PASS)
- **Confirmed Vulnerability Candidates Discovered**: 2
- **Candidates Remediated & Verified**: 2 (100% resolved)
- **Automated Regression Test Suite**: 17 / 17 passed (`tests/test_otp_verification.py`, `tests/test_security.py`)

---

## 2. Threat Model & Architecture Overview

NutriRisk AI operates across three distinct privilege tiers:

### Principals & Trust Boundaries:
1. **Anonymous**: Can access `/`, `/model`, `/login`, `/register`, `/reset`, and `/otp-login`. Cannot access any patient screening data or administrative tools.
2. **Clinician (`user`)**: Authenticated via Scrypt password, Biometric Face ID, or 6-digit OTP code. Can submit patient metrics, run batch screenings, inspect their own assessment history, and export clinical PDF reports. Isolated by `user_id` in all queries.
3. **Administrator (`admin`)**: Can access `/admin`, manage the user directory, review system telemetry, view global risk distributions, and audit immutable administrative actions. Protected by self-demotion safeguards.

---

## 3. Audited Coverage Units

The following units were formally reviewed, tracked, and validated via `coverage-ledger.json` in accordance with Cloudflare's audit methodology:

| Coverage ID | Attack Surface | Subsystem | Attack Class | Status |
| :--- | :--- | :--- | :--- | :---: |
| `admin-control-panel::clinician-to-admin::authorization::privilege-escalation` | Administrative Console | Authorization | Privilege Escalation | **Covered** |
| `database-query-interface::application-to-sqlite::persistence::sql-injection` | SQLite Queries | Data Layer | SQL Injection | **Covered** |
| `http-assessment-forms::client-to-server::clinical-triaging::input-validation-and-injection` | Risk Assessment Form | Inference Pipeline | Input Validation | **Covered** |
| `http-auth-endpoints::client-to-server::authentication::credential-and-session-hijacking` | Auth Endpoints (`/send-otp`, `/verify-otp`) | Authentication | Credential Exposure | **Candidate → Remediated** |
| `http-response-headers::server-to-client::security-middleware::security-header-misconfiguration` | Response Headers | Security Middleware | Header Misconfiguration | **Candidate → Remediated** |
| `local-model-filesystem::application-to-disk::ml-inference-engine::deserialization-and-path-traversal` | Serialized Joblib Bundle | ML Engine | Path Traversal / LFI | **Covered** |

---

## 4. Findings & Remediations

### Finding 1: Permissions-Policy Header Blocked Camera Access for Face ID Biometrics
- **Fingerprint**: `NUTRI-SEC-001-PERMISSIONS-POLICY-CAMERA`
- **Severity**: **Medium** (Likelihood: High, Impact: Medium)
- **Vulnerability Category**: HTTP Header Misconfiguration / Feature Denial
- **Location**: `nutririsk/security.py:102`
- **Root Cause**: The defensive header middleware was enforcing `Permissions-Policy: geolocation=(), camera=(), microphone=()`. While restricting geolocation and microphone is standard practice, `camera=()` completely revoked camera permissions across all execution contexts, causing `navigator.mediaDevices.getUserMedia()` in the Face ID biometric modal to fail with a `NotAllowedError`.
- **Remediation Implemented**:
  ```python
  # nutririsk/security.py
  # Allow camera permissions strictly on 'self' origin for Face ID authentication
  response.headers["Permissions-Policy"] = "geolocation=(), camera=(self), microphone=()"
  ```
- **Verification**: Face ID camera stream initializes properly on application origin; cross-origin camera access and microphone/geolocation remain blocked.

---

### Finding 2: Unconditional One-Time Password Code Preview in API JSON Response
- **Fingerprint**: `NUTRI-SEC-002-OTP-DEMO-PREVIEW-EXPOSURE`
- **Severity**: **High** (Likelihood: Medium, Impact: High)
- **Vulnerability Category**: Sensitive Data Exposure / Authentication Bypass Risk
- **Location**: `nutririsk/auth/routes.py:150-155`
- **Root Cause**: When adding the OTP passwordless sign-in feature for academic viva demonstration, `/send-otp` included `otp_preview: otp_code` in the JSON response payload. If deployed into a live production environment without explicit gating, an attacker could request an OTP for any clinician's email and extract the valid code directly from the HTTP response.
- **Remediation Implemented**:
  ```python
  # nutririsk/config.py
  # DEMO_MODE defaults to True only in development/testing; disabled in production
  DEMO_MODE = os.environ.get("DEMO_MODE", "1" if (DEBUG or TESTING or ENV != "production") else "0") == "1"

  # nutririsk/auth/routes.py
  is_demo = current_app.config.get("DEMO_MODE", False) or current_app.config.get("TESTING", False)
  return jsonify({
      "status": "success",
      "message": f"Verification code sent to {email}.",
      "otp_preview": otp_code if is_demo else None,
      "expires_in": 600
  })
  ```
- **Verification**: In production (`FLASK_ENV=production`), `otp_preview` is strictly `null`. In local academic testing / evaluation mode, the demo badge remains available.

---

## 5. Verified Defensive Controls

| Security Control | Implementation Location | Verification Status |
| :--- | :--- | :---: |
| **Password Hashing** | Scrypt with 16-byte cryptographic salt (`nutririsk/auth/utils.py`) | **Verified Secure** |
| **CSRF Defense** | Constant-time HMAC token comparison on all POST/PUT/DELETE requests (`nutririsk/security.py`) | **Verified Secure** |
| **SQL Injection Prevention** | 100% parameterized SQLite statements (`?` parameters, zero raw SQL strings) | **Verified Secure** |
| **Multi-Tenant Data Isolation** | Queries enforce `user_id = session['uid']` (`nutririsk/db.py`, `nutririsk/routes/assessment.py`) | **Verified Secure** |
| **Model Ingestion Safety** | Realpath canonicalization & extension check (`validate_safe_model_path`) | **Verified Secure** |
| **Session Security** | `HttpOnly=True`, `SameSite=Lax`, 8-hour lifetime, Scrypt password re-verification | **Verified Secure** |
| **Administrative Safeguards** | Privilege escalation blocked, self-demotion blocked, sole admin deletion blocked | **Verified Secure** |
| **Audit Logging** | Immutable logging of admin actions, role changes, and OTP generations | **Verified Secure** |

---

## 6. Schema & Ledger Validation Results

Using Cloudflare's native schema validation tools:

```bash
node .agents/skills/security-audit/validate-findings.cjs security-audit/findings.json
PASS: 2 findings valid

node .agents/skills/security-audit/validate-coverage-ledger.cjs security-audit/coverage-ledger.json
PASS: 6 coverage units valid
```

**Automated Test Suite Execution:**
```bash
pytest tests/test_otp_verification.py tests/test_security.py -q
17 passed in 36.68s
```
