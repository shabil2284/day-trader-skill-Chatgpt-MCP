# Security Audit

## Findings

### 1. Secret Management and .env Exposure
*   **Risk:** Sensitive credentials (Alpaca keys, OpenAI key) in `.env` are mounted read-only into containers.
*   **Recommendation:** Use Docker Secrets or a managed provider. Ensure `.env` is excluded from source control and has `600` permissions.

### 2. Docker Compose
*   **Observation:** Resource limits (`512M` memory, `0.5` cpus) provide adequate isolation.

### 3. System Hardening
*   **Recommendation:** Transition containers to non-privileged users to follow the principle of least privilege.
