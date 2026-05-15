# Presentation Guide

## 5-Minute Script

1. Introduction
Say: "This is a secure AI-based complaint management system. It supports students, staff, and admins, uses backend-enforced RBAC, Firestore or local demo storage, AI triage, validation, rate limiting, and audit logs."

2. Authentication and password hashing
Attack -> wrong password login for `admin@example.com`.
Risk -> account enumeration and credential guessing.
Countermeasure -> generic login error, hashed password storage, signed bearer tokens.
Demo result -> login fails with `Invalid email or password.`
Say: "The system never says whether the email exists, and the database stores password hashes instead of plaintext passwords."

3. RBAC / broken access control test
Attack -> login as `student1@example.com`, browse to `/admin`, `/admin/users`, `/audit-logs`, then call `/api/admin/users` with the student token.
Risk -> a student could manage users or read audit logs.
Countermeasure -> frontend route guard plus backend role check from the trusted user record.
Demo result -> UI shows Access Denied and backend returns `403 Forbidden`.
Say: "The important part is not hidden navigation. The backend reloads the user from storage and enforces ADMIN on every admin API."

4. IDOR test
Attack -> student1 creates a complaint, opens `View Details`, copies `/complaints/COMPLAINT_ID`, then student2 logs in and pastes the same URL.
Risk -> users could change IDs and read another student's data.
Countermeasure -> the detail page fetches `GET /api/complaints/COMPLAINT_ID`, and the backend compares `complaint.studentId` to the authenticated user ID before returning data.
Demo result -> student1 sees the details; student2 gets Access Denied / `403 Forbidden`; admin can view the same URL.
Say: "The complaint ID alone is not authorization. Student2 can paste the same URL, but the backend blocks the response because ownership is checked server-side."

5. XSS test
Attack -> submit `<script>alert('xss')</script>` and `<img src=x onerror=alert('xss')>`.
Risk -> stored script execution in other users' browsers.
Countermeasure -> backend strips HTML and React renders values as text, with no raw HTML APIs.
Demo result -> no alert executes.
Say: "Complaint text and AI text are treated as untrusted data, not executable HTML."

6. Injection / NoSQL injection test
Attack -> login with email `' OR '1'='1` and curl `{"email":{"$ne":null},"password":"anything"}`.
Risk -> bypassing authentication through dynamic query operators.
Countermeasure -> strict type validation, common suspicious-pattern detection, fixed Firestore query fields, and Admin Security Event alerting.
Demo result -> login is blocked or fails safely with no token, and Admin can see the detection alert.
Say: "Object-shaped payloads and SQL injection-style strings are rejected, so they cannot become query logic. The attempt is also visible to Admin as a security event."

7. File upload test
Attack -> upload `test.js`, `malware.php`, and `malware.php.png`.
Risk -> script/webshell upload or disguised unsafe content.
Countermeasure -> allowed extensions, blocked intermediate extensions, MIME checks, signature checks, 2 MB limit, UUID path.
Demo result -> unsafe uploads rejected; valid PNG/PDF accepted.
Say: "The server does not trust the original filename. It validates content and stores only a safe generated path."

8. Rate limiting and missing token test
Attack -> call admin API without token and repeat wrong login attempts.
Risk -> unauthenticated data access and brute-force guessing.
Countermeasure -> bearer-token requirement and per-bucket rate limits.
Demo result -> missing token returns `401`; repeated failures return `429 Too Many Requests`.
Say: "Rate limiting is used to reduce brute-force attacks. After repeated failed login attempts, the server temporarily blocks further requests and returns 429."

9. Audit logs and data protection
Attack -> wrong login, unauthorized admin attempt, rejected upload.
Risk -> attacks go unnoticed.
Countermeasure -> audit logs, Security Threat Detection and Admin Alerts, safe metadata only, no passwords or tokens in logs, secrets in `.env`.
Demo result -> admin can see unauthorized attempts and suspicious SQL/XSS/NoSQL/upload events.
Say: "The system detects common suspicious patterns and records security-relevant events so administrators can investigate attempted abuse."

10. Conclusion
Say: "This project demonstrates authentication, password hashing, backend RBAC, IDOR prevention, XSS and injection defenses, upload validation, rate limiting, audit logging, and Firestore/GCP-ready architecture with AI triage preserved."

## Security Threat Detection and Admin Alerts

Attack -> SQL injection, NoSQL object payload, XSS payload, or malicious upload.
Detection -> common suspicious strings, object-shaped values where text is expected, blocked upload extensions, and signature mismatches.
Action Taken -> request blocked, XSS sanitized where safe, or upload rejected.
Admin Alert -> Security Events shows severity, source, action, route/method, user context, and a short safe preview.

Say: "This detector is designed to catch common suspicious patterns for demonstration and monitoring. It reduces risk, but it is not a claim that every possible attack can be detected."

## Demo Accounts

Seed demo users with `DEMO_PASSWORD=DemoPass123!` in `backend/.env`.

- `admin@example.com` / `ADMIN`
- `staff@example.com` / `STAFF`
- `student1@example.com` / `STUDENT`
- `student2@example.com` / `STUDENT`

## Useful Payloads

```text
Wrong password: wrongpassword
SQL-style email: ' OR '1'='1
XSS title: Broken projector <script>alert('xss')</script>
XSS description: There is a lab issue. <img src=x onerror=alert('xss')> Students cannot access computers during class.
NoSQL JSON: {"email":{"$ne":null},"password":"anything"}
```
