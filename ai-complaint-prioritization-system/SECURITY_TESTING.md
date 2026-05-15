# SECURITY_TESTING.md

## Authoritative Demo Attack Checklist

Use backend `http://localhost:8080` and frontend `http://localhost:5173` or `http://localhost:5174`.

| Test | Payload or Command | Expected status/UI | Audit check |
| --- | --- | --- | --- |
| Missing token | `curl -i http://localhost:8080/api/admin/users` | `401 Unauthorized` | `UNAUTHORIZED_ACCESS_ATTEMPT` |
| Student RBAC bypass | `curl -i http://localhost:8080/api/admin/users -H "Authorization: Bearer STUDENT_TOKEN"` | `403 Forbidden`; UI `/admin`, `/admin/users`, `/audit-logs` shows Access Denied | `ROLE_FORBIDDEN` |
| Staff RBAC bypass | same command with `STAFF_TOKEN` | `403 Forbidden` | `ROLE_FORBIDDEN` |
| Admin access | same command with `ADMIN_TOKEN` | `200 OK` | normal admin read allowed |
| IDOR | student2 requests `/api/complaints/STUDENT1_COMPLAINT_ID` | `403 Forbidden` or Access Denied | `COMPLAINT_IDOR_ATTEMPT` |
| Staff assignment | staff requests unassigned complaint | `403 Forbidden`; works after admin assignment | `COMPLAINT_IDOR_ATTEMPT` |
| XSS | `Broken projector <script>alert('xss')</script>` and `<img src=x onerror=alert('xss')>` | no popup; sanitized or blocked | `SUSPICIOUS_INPUT_DETECTED` with XSS pattern |
| AI XSS | `Please write this complaint: <script>alert('ai-xss')</script>` | no popup; AI output displayed as text | AI call allowed only with token |
| Injection login | email `' OR '1'='1`, password `anything` | `400`; no token | `SUSPICIOUS_INPUT_DETECTED` with SQL pattern |
| NoSQL object injection | `{"email":{"$ne":null},"password":"anything"}` | `400`; no token | `SUSPICIOUS_INPUT_DETECTED` with NoSQL pattern |
| Malformed JSON | `-d '{"email":"admin@example.com",'` | safe `400`/`401`; no stack trace | optional failure log |
| Unsafe upload | `test.js`, `malware.php`, `malware.php.png` | rejected | `SUSPICIOUS_INPUT_DETECTED` and `FILE_UPLOAD_REJECTED` |
| Rate limit | repeated wrong login for `admin@example.com` | initial `401`, then `429 Too Many Requests` | `RATE_LIMITED` |
| Security headers | `curl -i http://localhost:8080/api/health` | `200 OK` with hardening headers | not applicable |

Rate limit demo command:

```bash
for i in {1..10}; do
  curl -i -X POST http://localhost:8080/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@example.com","password":"wrongpassword"}'
done
```

Expected: Some attempts return `401`, then later attempts return `429 Too Many Requests` with `Too many requests. Please try again later.`

## Security Threat Detection and Admin Alerts

The system detects common suspicious patterns and blocks/logs them. It does not claim to detect every possible attack.

| Attack | Detection | Action Taken | Admin Alert |
| --- | --- | --- | --- |
| SQL injection-style login | `' OR '1'='1`, `UNION SELECT`, `DROP TABLE`, `--` | request blocked with `400` | Security Events shows SQL injection pattern detected |
| NoSQL injection-style payload | object-shaped email or `$ne`, `$gt`, `$where`, `$regex` | request blocked with `400` | Security Events shows NoSQL object payload detected |
| XSS complaint payload | `<script>`, `onerror=`, `javascript:`, `alert(` | complaint text sanitized or blocked | Security Events shows XSS payload detected |
| Malicious upload | blocked extension or signature mismatch | upload rejected | Security Events shows malicious file upload rejected |

Admin verification:
1. Perform the suspicious login, XSS complaint, NoSQL payload, or file upload test.
2. Login as `admin@example.com`.
3. Open `Audit Logs`.
4. Review the `Security Events` panel for severity, source, action taken, route/method, user context, and safe payload preview.

## Test Environment

Run the backend and frontend locally, then seed demo users only for local presentation:

```bash
cd backend
source venv/bin/activate
cp .env.example .env
# Set USE_IN_MEMORY_DB=true, FLASK_DEBUG=1, ENABLE_DEMO_SEED=true, and a strong JWT_SECRET in .env
python app.py
```

In another terminal:

```bash
curl -X POST http://localhost:8080/api/demo/seed
cd frontend
npm install
npm run dev
```

Demo password for seeded local accounts: `DemoPass123!`. Do not use demo credentials in production.

## 1. Authentication Test

Steps:
- Register a valid student account from the Register page.
- Try a weak password such as `password`.
- Try logging in with the wrong password.
- Disable an account as admin and try logging in again.

Expected result:
- Valid registration and login work.
- Weak password is rejected by backend validation.
- Invalid login returns a generic `Invalid email or password.` message.
- Disabled account is blocked.
- Firestore `users` documents contain `passwordHash`, never plaintext passwords.

## 2. RBAC Test

Steps:
- Login as `student1@example.com` and try to open admin users/audit APIs directly.
- Login as student and try staff status APIs.
- Login as `staff@example.com` and try `/api/users` or `/api/audit-logs`.

Direct API check without a token:

```bash
curl -i http://localhost:8080/api/admin/users
```

Expected result:
- Missing token returns `401 Unauthorized`.
- Student or staff token returns `403 Forbidden`.
- UI shows Access Denied or hides unauthorized navigation.
- `auditLogs` receives `UNAUTHORIZED_ACCESS_ATTEMPT` entries.

## 3. IDOR Test

Steps:
- Login as Student A and create a complaint.
- Login as Student B and request Student A's complaint ID with `GET /api/complaints/<id>`.
- Login as staff before assignment and request that complaint.

Expected result:
- Backend returns `403 Forbidden` or not found where appropriate.
- Unauthorized attempt is logged in `auditLogs` and `securityEvents`.

## 4. NoSQL Injection Style Test

Payloads:

```json
{"email":{"$ne":null}}
"' || '1'=='1"
"' OR '1'='1"
```

Direct API check:

```bash
curl -i -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  --data '{"email":{"$ne":null},"password":"anything"}'
```

Expected result:
- Login rejects non-string email shapes.
- Strings are treated as strings, not query operators.
- Firestore queries use fixed collections and validated fields only.

## 5. XSS Test

Submit complaint title/description:

```html
<script>alert('xss')</script>
<img src=x onerror=alert(1)>
```

Expected result:
- Backend strips HTML tags during validation.
- React renders complaint and AI output as plain text.
- No `dangerouslySetInnerHTML` is present in frontend source.

Source scan:

```bash
rg -n "dangerouslySetInnerHTML|innerHTML|eval\\(|localStorage|sessionStorage|document\\.write|Function\\(" frontend/src backend
```

## 6. CSRF Test

This project uses `Authorization: Bearer <token>` headers with a session-scoped frontend token, not cookie authentication. Cross-site forms cannot attach that bearer header automatically, so CSRF risk is reduced. CORS is still restricted by `FRONTEND_ORIGIN`.

Expected result:
- Cross-site form POSTs are unauthenticated.
- Requests without bearer token return `401 Authentication required`.
- Browser requests from unapproved origins fail CORS checks.

## 7. File Upload Test

Try uploading:
- Valid `.png`
- Valid `.jpg`
- Valid `.pdf`
- `.exe`
- `.js`
- `.php`
- `malware.php.png`

Expected result:
- Only PDF/JPG/JPEG/PNG are accepted.
- Size over 2 MB is rejected.
- MIME type, final extension, blocked intermediate extensions, and file signature are checked.
- Rejected attempts produce `FILE_UPLOAD_REJECTED` audit entries.
- Accepted evidence is renamed with UUID metadata; original names are not trusted.

## 8. Rate Limiting Test

Steps:
- Attempt many failed logins quickly.

Example:

```bash
for i in $(seq 1 12); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8080/api/auth/login \
    -H "Content-Type: application/json" \
    --data '{"email":"admin@example.com","password":"wrong-password"}'
done
```

Expected result:
- Backend returns `401 Invalid email or password.` for early attempts, then `429 Too Many Requests` after the configured login threshold.
- Audit log records `RATE_LIMITED`.

## 9. Data Protection Test

Steps:
- Inspect Firestore `users`, `complaints`, and `auditLogs`.

Expected result:
- No plaintext passwords.
- No service account keys or API secrets in Firestore.
- Audit logs contain safe metadata only, no tokens or passwords.
- `.env`, service account keys, build outputs, and logs are ignored by git.

## 10. Security Headers Test

Run:

```bash
curl -i http://localhost:8080/api/health
```

Expected result:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Content-Security-Policy` present
- `Strict-Transport-Security` present when `HTTPS_READY=true`
