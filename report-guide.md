# Vulnerability Reports Access
## 1️⃣ Gitleaks

**What it is:** Gitleaks scans repositories for secrets like passwords, tokens, and API keys.

### **Access:**

- GitHub Actions → workflow run → Artifacts → `gitleaks-<run-id>.sarif`

---

## 2️⃣ SonarQube

**What it is:** SonarQube scans code for bugs, code smells, and security vulnerabilities.

### **Access:**

- From **emails sent on issues**.
- Or directly at: http://35.225.57.231:9000/projects with your username and password that was given to you
- Each team has access to its own projects only except for the security team that can access all the projects

---

## 3️⃣ OWASP Dependency Check

**What it is:** Dependency Check scans project dependencies for known CVEs (vulnerabilities).

### **Access:**

- GitHub **Security** → Code scanning alerts →filter results with the branch name
- Or GitHub Actions → workflow run → Artifacts → `dependency-check-report`

---

## 4️⃣ ZAP Scan

**What it is:** ZAP (OWASP Zed Attack Proxy) scans running web applications for security vulnerabilities.

### **Access:**

- GitHub Actions → workflow run → Artifacts → download `zap-report`

---

### Notes

- Artifacts are retained for 90 days.
- If you cannot access artifacts or code scanning results → contact the DevOps Team