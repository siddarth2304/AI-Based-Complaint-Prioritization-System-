# Secure AI-Based Complaint Management System

A cybersecurity-focused complaint management system with secure authentication, backend-enforced RBAC, Firestore persistence, Google Cloud/Vertex AI complaint triage, input validation, audit logging, and attack-prevention controls.

## Overview

The original AI complaint prioritization app has been upgraded into a secure course project. Students submit complaints, AI classifies priority/escalation, staff handle assigned complaints, and admins manage users, assignments, audit logs, and security events. Firestore remains the database backend when `USE_IN_MEMORY_DB=false`; local in-memory mode is available for demos.

## Cybersecurity Features

- Password hashing with Werkzeug security hashes; no plaintext passwords are stored.
- Signed bearer-token authentication with backend verification on every protected API.
- Backend-enforced RBAC for `STUDENT`, `STAFF`, and `ADMIN`.
- IDOR protection: students can read only their own complaints; staff can read/update only assigned complaints.
- Strict validation for email, password, names, complaint title/description, category, status, role, user IDs, complaint IDs, and evidence uploads.
- XSS prevention through backend HTML stripping and React plain-text rendering.
- NoSQL injection mitigation by type validation and fixed Firestore collection/query paths.
- CORS restricted by `FRONTEND_ORIGIN` and security headers on API responses.
- Rate limits for login/register, complaint creation, AI calls, and admin actions.
- Audit logs for registration, login success/failure, logout, complaint creation/view/status changes/assignment, AI escalation, user role/status changes, unauthorized attempts, and file uploads.
- Security events collection for high-risk unauthorized access attempts.
- Security Threat Detection and Admin Alerts for common suspicious SQL injection, NoSQL injection, XSS, and malicious upload indicators.
- Safe AI handling: complaint text is validated before AI processing, AI output is sanitized and validated before storage, and fallback classification works without cloud credentials.
- Evidence upload controls: only PDF/JPG/JPEG/PNG, max 2 MB, MIME + extension + signature checks, UUID paths, rejected uploads logged.

## Security Threat Detection and Admin Alerts

The backend detects common suspicious patterns and blocks or sanitizes the request depending on context. It does not claim to detect every possible attack; it implements practical countermeasures and records safe alerts for presentation and review.

| Attack | Detection | Action Taken | Admin Alert |
| --- | --- | --- | --- |
| SQL injection-style login | patterns such as `' OR '1'='1`, `UNION SELECT`, `DROP TABLE`, `--` | blocked with HTTP `400` | Security Events shows SQL injection pattern detected |
| NoSQL object/string payload | object-shaped values or `$ne`, `$gt`, `$where`, `$regex` | blocked with HTTP `400` | Security Events shows NoSQL object payload detected |
| XSS in complaint text | `<script>`, `onerror=`, `javascript:`, `alert(` | sanitized for complaint text and logged | Security Events shows XSS payload detected |
| Malicious upload | blocked extension, suspicious filename, MIME/signature mismatch | upload rejected | Security Events shows malicious file upload rejected |

Admin can review alerts from the `Audit Logs` page under the `Security Events` panel. Events include severity, source, action taken, route/method, user context when authenticated, and a short safe payload preview.

## Tech Stack

- Frontend: React 18, Vite, Tailwind CSS, Recharts, Lucide icons
- Backend: Flask, Flask-CORS, Werkzeug password hashing
- Database: Firestore through `google-cloud-firestore`
- AI: Vertex AI/Gemini when configured, local rule-based fallback for demos
- Google Cloud: Cloud Run-ready backend, Firestore, Vertex AI, Cloud Functions folder preserved

## Firestore Collections

`users`:
- `uid`, `name`, `email`, `role`, `isActive`, `passwordHash`, `createdAt`, `updatedAt`, `lastLoginAt`

`complaints`:
- `title`, `description`, `category`, `status`, `priority`, `priority_score`, `studentId`, `assignedStaffId`, `aiEscalationRequired`, `aiReason`, `evidenceFilePath`, `createdAt`, `updatedAt`

`auditLogs`:
- `userId`, `userRole`, `action`, `targetType`, `targetId`, `ipAddress`, `userAgent`, `createdAt`, `safeDetails`

`securityEvents`:
- `eventType`, `severity`, `source`, `userId`, `userRole`, `userEmail`, `detectedPattern`, `safePayloadPreview`, `route`, `method`, `actionTaken`, `createdAt`, `details`

## Environment Variables

Copy examples before running:

```bash
cp .env.example backend/.env
cp frontend/.env.example frontend/.env
```

Important backend values:

```env
GCP_PROJECT_ID=your-gcp-project-id
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GCP_LOCATION=us-central1
VERTEX_MODEL=gemini-1.5-flash
USE_IN_MEMORY_DB=false
FRONTEND_ORIGIN=http://localhost:5173
JWT_SECRET=replace-with-at-least-32-random-characters
ENABLE_DEMO_SEED=false
DEMO_PASSWORD=DemoPass123!
```

Use `USE_IN_MEMORY_DB=true` for the local cybersecurity demo when GCP credentials are not available. Set it to `false` to use Firestore/GCP credentials for the connected cloud project.

## Run Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Local demo mode:

```bash
cd backend
source venv/bin/activate
export USE_IN_MEMORY_DB=true
export FLASK_DEBUG=1
export ENABLE_DEMO_SEED=true
export JWT_SECRET=local-dev-secret-change-me-32chars
export DEMO_PASSWORD=DemoPass123!
python app.py
```

Seed demo users in the running backend process:

```bash
curl -X POST http://localhost:8080/api/demo/seed
```

For Firestore mode, you can seed persistent demo users with:

```bash
cd backend
source venv/bin/activate
python seed_demo_users.py
```

## Run Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open the Vite URL, usually `http://localhost:5173`.

If port 5173 is busy, Vite may use `http://localhost:5174`. Both origins are allowed by the backend local CORS configuration.

## Demo Users

Local/presentation password: `DemoPass123!`

- `admin@example.com` / `ADMIN`
- `staff@example.com` / `STAFF`
- `student1@example.com` / `STUDENT`
- `student2@example.com` / `STUDENT`

These are demo-only credentials. Change or remove them for production.

## API Summary

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `POST /api/complaints`
- `GET /api/complaints`
- `GET /api/complaints/<id>`
- `PATCH /api/complaints/<id>/status`
- `PATCH /api/complaints/<id>/assign`
- `PATCH /api/complaints/<id>/rating`
- `POST /api/complaints/<id>/solution`
- `GET /api/users`
- `PATCH /api/users/<uid>`
- `GET /api/audit-logs`
- `GET /api/security-events`
- `GET /api/admin/dashboard`
- `GET /api/admin/users`
- `PATCH /api/admin/users/<uid>`
- `GET /api/admin/audit-logs`
- `GET /api/admin/security-events`
- `GET /api/admin/complaints`

All protected routes require `Authorization: Bearer <token>`.

Admin APIs require `ADMIN`. Staff can view/update only assigned complaints. Students can submit complaints and view only their own complaint records.

## Security Testing

See `SECURITY_TESTING.md` for authentication, RBAC, IDOR, injection, XSS, CSRF, file upload, rate limiting, data protection, and security-header tests.

## Presentation Notes

See `PRESENTATION_GUIDE.md` for a video demo sequence mapped to the cybersecurity rubric.

## Troubleshooting

- Browser shows `Failed to fetch`: start the backend first, verify `curl http://localhost:8080/api/health`, and confirm `frontend/.env` contains `VITE_API_BASE_URL=http://localhost:8080`.
- CORS error: keep `FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174` for local Vite demos, or set it to your deployed frontend origins in Cloud Run.
- `401 Authentication required`: login again; bearer token is missing or expired.
- `403 Forbidden`: your role is not allowed; check backend audit logs.
- Empty staff dashboard: admin must assign complaints to that staff user.
- Firestore unavailable locally: keep `USE_IN_MEMORY_DB=true` for local fallback or authenticate with `gcloud auth application-default login` and set `USE_IN_MEMORY_DB=false`.
- Vertex AI unavailable: the backend falls back to rule-based classification in local in-memory mode.
