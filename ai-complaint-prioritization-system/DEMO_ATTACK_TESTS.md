# Demo Attack Tests

Use these local-only tests for the 5-minute presentation. Backend URL: `http://localhost:8080`. Frontend URL: `http://localhost:5173` or `http://localhost:5174`.

## A. Authentication Failure Test

Where: Login page.

Payload:
- email: `admin@example.com`
- password: `wrongpassword`

Expected: Login fails with generic `Invalid email or password.`

Countermeasure: Generic errors prevent account enumeration and password guessing feedback.

Say: "The system does not reveal whether the email exists. It gives the same safe error for bad credentials."

## B. Missing Token Test

Command:

```bash
curl -i http://localhost:8080/api/admin/users
```

Expected: `401 Unauthorized`.

Countermeasure: Protected APIs require authentication.

Say: "Without a bearer token, the backend blocks the admin API before any data is returned."

## C. RBAC Bypass Test With Student

Steps:
1. Login as `student1@example.com` / `DemoPass123!`.
2. Manually open `http://localhost:5174/admin`, `http://localhost:5174/admin/users`, and `http://localhost:5174/audit-logs`.
3. Test backend with a student token:

```bash
curl -i http://localhost:8080/api/admin/users -H "Authorization: Bearer STUDENT_TOKEN"
```

Expected: UI shows Access Denied and API returns `403 Forbidden`.

Countermeasure: Backend RBAC blocks authenticated but unauthorized users.

Say: "The frontend hides admin links, but the real control is backend RBAC. A student token still gets 403."

## D. RBAC Bypass Test With Staff

Steps:
1. Login as `staff@example.com` / `DemoPass123!`.
2. Try admin/manage users in the UI or direct URL.
3. Test backend admin API with staff token.

Expected: `403 Forbidden`.

Countermeasure: Staff cannot perform admin-only actions.

Say: "Staff users can work on assigned complaints, but cannot manage users or view audit logs."

## E. IDOR Test

Steps:
1. Login as student1.
2. Create a complaint.
3. Open My Complaints.
4. Click `View Details` on the complaint.
5. Copy the browser URL, for example `http://localhost:5174/complaints/COMPLAINT_ID`.
6. Logout.
7. Login as student2.
8. Paste the copied `/complaints/COMPLAINT_ID` URL in the browser.
9. Also test the API with student2 token:

```bash
curl -i http://localhost:8080/api/complaints/COMPLAINT_ID \
  -H "Authorization: Bearer STUDENT2_TOKEN"
```

Expected: UI shows Access Denied and API returns `403 Forbidden`.

Countermeasure: Backend checks complaint ownership before returning complaint data.

Say: "This is an IDOR attack. Student2 knows a valid complaint ID, but the backend checks that the complaint belongs to the authenticated student before sending any details."

## F. Staff Assignment Authorization Test

Steps:
1. Login as staff.
2. Try opening or updating a complaint not assigned to that staff user.
3. Login as admin and assign the complaint to staff.
4. Login as staff again and view/update the assigned complaint.

Expected: Unassigned access returns `403 Forbidden`; assigned access works.

Countermeasure: Staff access is restricted by assignment.

Say: "Staff authorization is not just role-based; it also checks assignment."

## G. XSS Test In Complaint Form

Where: Submit Complaint page.

Title payload:

```html
Broken projector <script>alert('xss')</script>
```

Description payload:

```html
There is a lab issue. <img src=x onerror=alert('xss')> Students cannot access computers during class.
```

Expected: No alert executes. Complaint text is sanitized or blocked safely, and Admin Security Events records an XSS payload alert.

Countermeasure: Suspicious payload detection, input sanitization, safe React rendering, and Admin alerting mitigate stored XSS risk.

Say: "The backend detects the XSS pattern, sanitizes the complaint text, and the Admin Security Events page records the attempt."

## H. AI Output XSS Safety Test

Where: AI complaint writing help.

Payload:

```text
Please write this complaint: <script>alert('ai-xss')</script>
```

Expected: AI output is displayed safely as text; no script executes.

Countermeasure: AI output is treated as untrusted and not rendered as raw HTML.

Say: "AI output is also untrusted input. The backend sanitizes it and the frontend renders text only."

## I. Injection-Style Login Test

Where: Login page.

Payload:
- email: `' OR '1'='1`
- password: `anything`

Expected: Request is blocked or fails safely with `Suspicious input detected. Request blocked for security reasons.`

Countermeasure: Input validation, suspicious pattern detection, fixed backend authentication logic, and Admin Security Event alerting.

Say: "The backend detects a SQL injection-style login payload, blocks it, and creates a safe admin security alert without logging passwords."

## J. NoSQL Object Injection Test

Command:

```bash
curl -i -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":{"$ne":null},"password":"anything"}'
```

Expected: `400`, `401`, or validation error. Must not login.

Countermeasure: Backend rejects object-shaped payloads, records a NoSQL-style security event, and does not use unsafe dynamic queries.

Say: "The login endpoint requires strings. An object cannot become a Firestore operator, and the attempt is visible to Admin."

## K. Malformed JSON Test

Command:

```bash
curl -i -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com",'
```

Expected: `400 Bad Request` or safe validation response; no stack trace.

Countermeasure: Server handles malformed input safely.

Say: "Bad JSON is rejected safely without leaking internals."

## L. File Upload Attack Test

Create files:

```bash
echo "alert('bad')" > test.js
echo "<?php echo 'hack'; ?>" > malware.php
cp malware.php malware.php.png
```

Upload through the complaint evidence field.

Expected: Unsafe files are rejected. A valid PNG/JPG/PDF under 2 MB is accepted.

Countermeasure: Extension, MIME, signature, size validation, and security-event alerting reject unsafe uploads.

Say: "The backend does not trust the filename. It checks MIME type, blocked extensions, file size, and file signature, then logs a malicious upload alert."

## M. Brute-Force / Rate-Limit Test

Where: Login page or curl.

Payload:
- email: `admin@example.com`
- password: `wrongpassword`

Command:

```bash
for i in {1..10}; do
  curl -i -X POST http://localhost:8080/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@example.com","password":"wrongpassword"}'
done
```

Expected: Some attempts fail with `401`, then later attempts return `429 Too Many Requests`.

Countermeasure: Rate limiting reduces brute-force attacks.

Say: "Rate limiting is used to reduce brute-force attacks. After repeated failed login attempts, the server temporarily blocks further requests and returns 429."

## N. Audit Log Verification

Steps:
1. Perform wrong login.
2. Perform student admin access attempt.
3. Perform file upload rejection.
4. Login as admin.
5. Open Audit Logs.

Expected: Events are recorded.

Countermeasure: Audit logging improves accountability and incident monitoring.

Say: "Security events are visible to admins, so attempted attacks are not silent."

## Q. Security Threat Detection and Admin Alerts

Where: Website UI and Admin Audit Logs page.

Demo flow:
1. On Login, enter email `' OR '1'='1` and password `anything`.
2. Login as student and submit the XSS complaint payload from section G.
3. Upload `test.js` or `malware.php.png`.
4. Login as admin.
5. Open `Audit Logs` and inspect the `Security Events` panel.

Expected:
- SQL injection-style login is blocked with safe message.
- XSS does not execute and is sanitized or blocked.
- Malicious upload is rejected.
- Admin Security Events shows severity, source, action taken, route/method, and a safe preview.

Countermeasure:
The system detects common suspicious patterns and blocks/logs them without claiming complete attack coverage.

Say: "This feature gives administrators visibility into suspicious input attempts. It records safe metadata, not passwords, tokens, or full dangerous payloads."

## O. Password Storage Check

Where: Database or backend storage inspection.

Expected: No plaintext passwords are stored. Only password hashes exist.

Countermeasure: Password hashing protects credentials even if database is exposed.

Say: "The database stores password hashes, not raw passwords."

## P. Security Headers Test

Command:

```bash
curl -i http://localhost:8080/api/health
```

Expected: Security headers such as `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and `Content-Security-Policy`.

Countermeasure: Headers reduce browser-based risks.

Say: "Security headers provide browser-side hardening in addition to backend authorization."
