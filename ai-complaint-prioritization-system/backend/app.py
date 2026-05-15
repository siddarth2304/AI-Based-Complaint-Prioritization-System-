import base64
import hashlib
import hmac
import html
import json
import os
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

from services.ai_priority_service import assist_user, classify_complaint, generate_resolution_sop
from services.firestore_service import (
    assign_complaint,
    create_audit_log,
    create_complaint,
    create_security_event,
    create_user,
    delete_sensitive_user_fields,
    get_complaint,
    get_complaint_stats,
    get_user,
    get_user_by_email,
    list_audit_logs,
    list_complaints,
    list_security_events,
    list_users,
    save_complaint_solution,
    update_complaint_rating,
    update_complaint_status,
    update_user,
    visible_complaints,
)
from services.sla_service import calculate_sla_deadline

load_dotenv()

PROJECT_NAME = "Secure AI-Based Complaint Management System"
CLOUD_COMPONENTS = ["Cloud Run", "Firestore", "Vertex AI", "Cloud Functions"]
ROLES = {"STUDENT", "STAFF", "ADMIN"}
STATUSES = {"OPEN", "IN_PROGRESS", "RESOLVED", "REJECTED"}
STATUS_LABELS = {"OPEN": "Pending", "IN_PROGRESS": "In Progress", "RESOLVED": "Resolved", "REJECTED": "Rejected"}
PRIORITIES = {"LOW", "MEDIUM", "HIGH", "URGENT"}
CATEGORIES = {"ACADEMIC", "HOSTEL", "INFRASTRUCTURE", "SAFETY", "SECURITY", "ADMINISTRATION", "IT", "GENERAL"}
DOC_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
RATE_BUCKETS: Dict[str, list] = {}
SAFE_FILE_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
SAFE_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}
BLOCKED_FILE_EXTENSIONS = {".exe", ".js", ".php", ".html", ".htm", ".bat", ".sh", ".cmd", ".svg", ".ps1", ".jar"}
MAX_FILE_BYTES = 2 * 1024 * 1024
SUSPICIOUS_INPUT_MESSAGE = "Suspicious input detected. Request blocked for security reasons."
THREAT_PATTERNS = [
    ("XSS_PAYLOAD", "XSS payload detected", "HIGH", re.compile(r"<\s*/?\s*script\b|on(?:error|load|click|mouseover)\s*=|javascript\s*:|<\s*iframe\b|<\s*img\b[^>]*onerror\s*=|document\.cookie|alert\s*\(", re.IGNORECASE)),
    ("SQL_INJECTION", "SQL injection pattern detected", "HIGH", re.compile(r"('\s*or\s*'?\d+'?\s*=\s*'?\d+'?|\"\s*or\s*\"?\d+\"?\s*=\s*\"?\d+\"?|\bor\s+1\s*=\s*1\b|union\s+select|drop\s+table|insert\s+into|delete\s+from|select\s+\*\s+from|--|/\*|\*/)", re.IGNORECASE)),
    ("NOSQL_INJECTION", "NoSQL object payload detected", "MEDIUM", re.compile(r'"\s*\$(?:ne|gt|where|regex|or|and)\s*"|\$(?:ne|gt|where|regex|or|and)|\{\s*"\$(?:ne|gt|where|regex|or|and)"', re.IGNORECASE)),
]


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", str(1024 * 1024 * 3)))
    configure_security(app)

    @app.get("/api/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "project": PROJECT_NAME,
                "subtitle": "RBAC, Firestore, Google Cloud, AI escalation, and attack prevention",
                "cloud_components_used": CLOUD_COMPONENTS,
                "timestamp": utc_now(),
            }
        )

    @app.post("/api/auth/register")
    @rate_limit("register", 8, 3600)
    def register():
        payload = json_payload()
        name = validate_text(payload.get("name"), "name", 1, 80, source="REGISTER", block_xss=True)
        email = validate_email(payload.get("email"), source="REGISTER")
        password = validate_password(payload.get("password"))
        if get_user_by_email(email):
            audit("REGISTER_REJECTED", target_type="user", safe_details={"reason": "email_exists"})
            return problem("Unable to create account with the supplied details.", 400)

        uid = str(uuid.uuid4())
        now = utc_now()
        user = create_user(
            uid,
            {
                "uid": uid,
                "name": name,
                "email": email,
                "role": "STUDENT",
                "isActive": True,
                "passwordHash": generate_password_hash(password),
                "createdAt": now,
                "updatedAt": now,
            },
        )
        audit("USER_REGISTERED", user_id=uid, user_role="STUDENT", target_type="user", target_id=uid)
        return jsonify({"user": delete_sensitive_user_fields(user), "token": create_token(user)}), 201

    @app.post("/api/auth/login")
    @rate_limit("login", 10, 900)
    def login():
        payload = json_payload()
        try:
            email = validate_email(payload.get("email"), source="LOGIN")
            password = validate_login_password(payload.get("password"))
        except SuspiciousInputError:
            return problem(SUSPICIOUS_INPUT_MESSAGE, 400)
        except ValueError:
            audit("LOGIN_FAILURE", safe_details={"reason": "invalid_shape"})
            return problem("Invalid email or password.", 401)

        user = get_user_by_email(email)
        if not user or not check_password_hash(user.get("passwordHash", ""), password):
            audit("LOGIN_FAILURE", target_type="user", safe_details={"email": mask_email(email), "reason": "bad_credentials"})
            return problem("Invalid email or password.", 401)
        if not user.get("isActive", True):
            audit("LOGIN_FAILURE", user_id=user["id"], user_role=user.get("role"), target_type="user", target_id=user["id"], safe_details={"reason": "disabled"})
            return problem("Account is disabled. Contact an administrator.", 403)

        now = utc_now()
        update_user(user["id"], {"lastLoginAt": now, "updatedAt": now})
        user = get_user(user["id"])
        audit("LOGIN_SUCCESS", user_id=user["id"], user_role=user.get("role"), target_type="user", target_id=user["id"])
        return jsonify({"user": delete_sensitive_user_fields(user), "token": create_token(user)})

    @app.post("/api/auth/logout")
    @auth_required
    def logout():
        audit("LOGOUT", target_type="user", target_id=g.user["id"])
        return jsonify({"ok": True})

    @app.get("/api/auth/me")
    @auth_required
    def me():
        return jsonify({"user": delete_sensitive_user_fields(g.user)})

    @app.get("/api/complaints")
    @auth_required
    def complaints():
        return jsonify(visible_complaints(g.user["role"], g.user["id"]))

    @app.get("/api/complaints/stats")
    @auth_required
    def stats():
        return jsonify(get_complaint_stats(g.user["role"], g.user["id"]))

    @app.post("/api/complaints")
    @auth_required
    @roles_required("STUDENT", "ADMIN")
    @rate_limit("complaint_submit", 20, 3600)
    def submit_complaint():
        payload = json_payload()
        title = validate_text(payload.get("title"), "title", 3, 120, source="COMPLAINT")
        description = validate_text(payload.get("description"), "description", 10, 2000, source="COMPLAINT")
        category = validate_enum(payload.get("category", "GENERAL"), CATEGORIES, "category")
        department = validate_text(payload.get("department", "General"), "department", 1, 80, source="COMPLAINT")
        evidence = validate_evidence(payload.get("evidence"))

        classification = classify_complaint(title, description, None)
        classification = normalize_ai_result(classification)
        now = utc_now()
        priority_label = classification["priorityLabel"]
        complaint = {
            "title": title,
            "description": description,
            "category": category,
            "displayCategory": classification["category"],
            "department": department,
            "status": "OPEN",
            "statusLabel": "Pending",
            "priority": priority_label,
            "priorityLabel": priority_label.title(),
            "priority_score": classification["priority_score"],
            "aiEscalationRequired": classification["aiEscalationRequired"],
            "aiReason": classification["aiReason"],
            "ai_reason": classification["aiReason"],
            "sdg": classification["sdg"],
            "assigned_department": classification["assigned_department"],
            "assignedStaffId": None,
            "studentId": g.user["id"],
            "studentName": g.user.get("name"),
            "studentEmail": g.user.get("email"),
            "sla_deadline": calculate_sla_deadline(classification["legacyPriority"]),
            "createdAt": now,
            "updatedAt": now,
            "created_at": now,
            "updated_at": now,
            **evidence,
        }
        created = create_complaint(complaint)
        audit("COMPLAINT_CREATED", target_type="complaint", target_id=created["id"], safe_details={"priority": priority_label, "aiEscalationRequired": classification["aiEscalationRequired"]})
        audit("AI_ESCALATION_COMPLETED", target_type="complaint", target_id=created["id"], safe_details={"priority": priority_label, "reason": classification["aiReason"][:160]})
        if evidence:
            audit("FILE_UPLOAD_ACCEPTED", target_type="complaint", target_id=created["id"], safe_details={"path": evidence.get("evidenceFilePath"), "mime": evidence.get("evidenceMimeType")})
        return jsonify(created), 201

    @app.get("/api/complaints/<complaint_id>")
    @auth_required
    def complaint_detail(complaint_id):
        complaint = require_complaint_access(complaint_id, allow_staff=True)
        audit("COMPLAINT_VIEWED", target_type="complaint", target_id=complaint_id)
        return jsonify(complaint)

    @app.patch("/api/complaints/<complaint_id>/status")
    @auth_required
    @roles_required("STAFF", "ADMIN")
    @rate_limit("status_update", 50, 3600)
    def patch_status(complaint_id):
        complaint = require_complaint_access(complaint_id, allow_staff=True, admin_all=True)
        if g.user["role"] == "STAFF" and complaint.get("assignedStaffId") != g.user["id"]:
            log_unauthorized("COMPLAINT_STATUS_IDOR", "complaint", complaint_id)
            return problem("Forbidden", 403)
        payload = json_payload()
        status = validate_enum(payload.get("status"), STATUSES, "status")
        staff_note = validate_optional_text(payload.get("staffNote", ""), "staffNote", 0, 500, source="STAFF_NOTE")
        updated = update_complaint_status(complaint_id, status, staff_note)
        audit("COMPLAINT_STATUS_CHANGED", target_type="complaint", target_id=complaint_id, safe_details={"status": status})
        return jsonify(updated)

    @app.patch("/api/complaints/<complaint_id>/assign")
    @auth_required
    @roles_required("ADMIN")
    @rate_limit("admin_action", 60, 3600)
    def patch_assign(complaint_id):
        require_valid_doc_id(complaint_id, "complaint_id")
        if not get_complaint(complaint_id):
            return problem("Complaint not found", 404)
        payload = json_payload()
        staff_uid = validate_doc_id(payload.get("staffId"), "staffId")
        staff = get_user(staff_uid)
        if not staff or staff.get("role") != "STAFF" or not staff.get("isActive", True):
            return problem("Active staff user is required.", 400)
        updated = assign_complaint(complaint_id, staff_uid)
        audit("COMPLAINT_ASSIGNED", target_type="complaint", target_id=complaint_id, safe_details={"assignedStaffId": staff_uid})
        return jsonify(updated)

    @app.patch("/api/complaints/<complaint_id>/rating")
    @auth_required
    @roles_required("STUDENT")
    def patch_rating(complaint_id):
        complaint = require_complaint_access(complaint_id)
        payload = json_payload()
        rating = payload.get("rating")
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return problem("Rating must be an integer between 1 and 5", 400)
        updated = update_complaint_rating(complaint["id"], rating)
        audit("COMPLAINT_RATED", target_type="complaint", target_id=complaint["id"], safe_details={"rating": rating})
        return jsonify(updated)

    @app.post("/api/complaints/<complaint_id>/solution")
    @auth_required
    @roles_required("STAFF", "ADMIN")
    @rate_limit("ai_solution", 30, 3600)
    def generate_solution(complaint_id):
        complaint = require_complaint_access(complaint_id, allow_staff=True, admin_all=True)
        if g.user["role"] == "STAFF" and complaint.get("assignedStaffId") != g.user["id"]:
            log_unauthorized("AI_SOLUTION_IDOR", "complaint", complaint_id)
            return problem("Forbidden", 403)
        if complaint.get("ai_solution"):
            return jsonify(complaint)
        solution_text = sanitize_ai_text(generate_resolution_sop(complaint.get("title", ""), complaint.get("description", ""), complaint.get("displayCategory") or complaint.get("category", "")))
        updated = save_complaint_solution(complaint_id, solution_text)
        audit("AI_RESOLUTION_GENERATED", target_type="complaint", target_id=complaint_id)
        return jsonify(updated)

    @app.post("/api/ai/assist")
    @auth_required
    @rate_limit("ai_assist", 30, 3600)
    def ai_assist():
        payload = json_payload()
        message = validate_text(payload.get("message"), "message", 1, 600, source="AI_HELP", block_xss=True)
        return jsonify({"reply": sanitize_ai_text(assist_user(message))})

    @app.get("/api/users")
    @auth_required
    @roles_required("ADMIN")
    @rate_limit("admin_read", 120, 3600)
    def users():
        return jsonify(list_users())

    @app.patch("/api/users/<uid>")
    @auth_required
    @roles_required("ADMIN")
    @rate_limit("admin_action", 60, 3600)
    def patch_user(uid):
        uid = validate_doc_id(uid, "uid")
        target = get_user(uid)
        if not target:
            return problem("User not found", 404)
        payload = json_payload()
        updates: Dict[str, Any] = {"updatedAt": utc_now()}
        action = None
        if "role" in payload:
            updates["role"] = validate_enum(payload.get("role"), ROLES, "role")
            action = "USER_ROLE_CHANGED"
        if "isActive" in payload:
            if not isinstance(payload.get("isActive"), bool):
                return problem("isActive must be boolean", 400)
            updates["isActive"] = payload["isActive"]
            action = "ACCOUNT_ENABLED" if payload["isActive"] else "ACCOUNT_DISABLED"
        if "name" in payload:
            updates["name"] = validate_text(payload.get("name"), "name", 1, 80, source="ADMIN_USER", block_xss=True)
        updated = update_user(uid, updates)
        audit(action or "USER_UPDATED", target_type="user", target_id=uid, safe_details={k: v for k, v in updates.items() if k != "updatedAt"})
        return jsonify(delete_sensitive_user_fields(updated))

    @app.get("/api/audit-logs")
    @auth_required
    @roles_required("ADMIN")
    @rate_limit("admin_read", 120, 3600)
    def audit_logs():
        return jsonify(list_audit_logs(limit=100))

    @app.get("/api/security-events")
    @auth_required
    @roles_required("ADMIN")
    @rate_limit("admin_read", 120, 3600)
    def security_events():
        return jsonify(list_security_events(limit=100))

    @app.get("/api/admin/dashboard")
    @auth_required
    @roles_required("ADMIN")
    @rate_limit("admin_read", 120, 3600)
    def admin_dashboard():
        return jsonify({"stats": get_complaint_stats("ADMIN", g.user["id"]), "complaints": visible_complaints("ADMIN", g.user["id"])})

    @app.get("/api/admin/users")
    @auth_required
    @roles_required("ADMIN")
    @rate_limit("admin_read", 120, 3600)
    def admin_users():
        return jsonify(list_users())

    @app.patch("/api/admin/users/<uid>")
    @auth_required
    @roles_required("ADMIN")
    @rate_limit("admin_action", 60, 3600)
    def admin_patch_user(uid):
        return patch_user(uid)

    @app.get("/api/admin/audit-logs")
    @auth_required
    @roles_required("ADMIN")
    @rate_limit("admin_read", 120, 3600)
    def admin_audit_logs():
        return jsonify(list_audit_logs(limit=100))

    @app.get("/api/admin/security-events")
    @auth_required
    @roles_required("ADMIN")
    @rate_limit("admin_read", 120, 3600)
    def admin_security_events():
        return jsonify(list_security_events(limit=100))

    @app.get("/api/admin/complaints")
    @auth_required
    @roles_required("ADMIN")
    @rate_limit("admin_read", 120, 3600)
    def admin_complaints():
        return jsonify(visible_complaints("ADMIN", g.user["id"]))

    @app.post("/api/demo/seed")
    @rate_limit("seed", 3, 3600)
    def seed_demo():
        if os.getenv("ENABLE_DEMO_SEED", "").lower() != "true":
            return problem("Demo seeding is disabled.", 403)
        seeded = seed_demo_users()
        return jsonify({"seeded": seeded})

    @app.errorhandler(ValueError)
    def validation_error(error):
        return problem(str(error), 400)

    @app.errorhandler(ForbiddenError)
    def forbidden_error(error):
        return problem(str(error), 403)

    @app.errorhandler(NotFoundError)
    def not_found_error(error):
        return problem(str(error), 404)

    @app.errorhandler(SuspiciousInputError)
    def suspicious_input_error(error):
        return problem(str(error), 400)

    @app.errorhandler(Exception)
    def handle_error(error):
        if isinstance(error, HTTPException):
            return problem(error.description, error.code)
        app.logger.exception("Unhandled request error")
        return problem("Internal server error", 500)

    return app


def configure_security(app: Flask) -> None:
    origins = parse_csv_env("FRONTEND_ORIGINS") or [os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")]
    for local_origin in ("http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"):
        if local_origin not in origins:
            origins.append(local_origin)
    CORS(
        app,
        origins=origins,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    )

    @app.after_request
    def set_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(self), geolocation=()")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'")
        if os.getenv("HTTPS_READY", "true").lower() == "true":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


def parse_csv_env(name: str) -> list:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


def json_payload() -> Dict[str, Any]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValueError("JSON object body is required")
    return payload


def create_token(user: Dict[str, Any]) -> str:
    secret = jwt_secret()
    now = datetime.now(timezone.utc)
    return jwt_encode(
        {
            "sub": user["id"],
            "role": user.get("role"),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=int(os.getenv("JWT_EXPIRES_HOURS", "8")))).timestamp()),
        },
        secret,
    )


def jwt_encode(payload: Dict[str, Any], secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = b64url(hmac.new(secret.encode(), signing_input, hashlib.sha256).digest())
    return f"{header_b64}.{payload_b64}.{signature}"


def jwt_decode(token: str, secret: str) -> Dict[str, Any]:
    try:
        header_b64, payload_b64, signature = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected = b64url(hmac.new(secret.encode(), signing_input, hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        payload = json.loads(b64url_decode(payload_b64))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("token expired")
        return payload
    except Exception as exc:
        raise ValueError("invalid token") from exc


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode())


def strip_html(value: str) -> str:
    without_tags = re.sub(r"<[^>]*>", "", value)
    return html.unescape(without_tags).strip()


def safe_preview(value: Any, limit: int = 80) -> str:
    if isinstance(value, (dict, list)):
        preview = json.dumps(value, separators=(",", ":"), default=str)
    else:
        preview = str(value or "")
    preview = re.sub(r"[\r\n\t]+", " ", preview)
    preview = strip_html(preview)
    preview = html.escape(preview, quote=False)
    return preview[:limit]


def detect_suspicious_input(value: Any) -> Optional[Dict[str, str]]:
    if isinstance(value, dict):
        if any(str(key).startswith("$") for key in value.keys()):
            return {"category": "NOSQL_INJECTION", "label": "NoSQL object payload detected", "severity": "HIGH"}
        return {"category": "OBJECT_IN_TEXT_FIELD", "label": "Object-shaped value where text was expected", "severity": "MEDIUM"}
    if isinstance(value, list):
        return {"category": "OBJECT_IN_TEXT_FIELD", "label": "Array-shaped value where text was expected", "severity": "MEDIUM"}
    if not isinstance(value, str):
        return None
    for category, label, severity, pattern in THREAT_PATTERNS:
        if pattern.search(value):
            return {"category": category, "label": label, "severity": severity}
    return None


def record_suspicious_input(source: str, field: str, value: Any, detection: Dict[str, str], action_taken: str, status: int) -> None:
    actor = getattr(g, "user", None)
    details = {
        "field": field,
        "route": request.path,
        "method": request.method,
        "status": status,
        "detectedPattern": detection["label"],
        "detectedCategory": detection["category"],
        "safePayloadPreview": safe_preview(value),
        "actionTaken": action_taken,
    }
    event = {
        "eventType": "SUSPICIOUS_INPUT_DETECTED",
        "severity": detection.get("severity", "MEDIUM"),
        "source": source,
        "userId": (actor or {}).get("id"),
        "userRole": (actor or {}).get("role"),
        "userEmail": (actor or {}).get("email"),
        "detectedPattern": detection["label"],
        "detectedCategory": detection["category"],
        "safePayloadPreview": details["safePayloadPreview"],
        "ipAddress": request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip(),
        "userAgent": (request.headers.get("User-Agent", "") or "")[:200],
        "route": request.path,
        "method": request.method,
        "actionTaken": action_taken,
        "details": details,
    }
    create_security_event(event)
    audit_action = "SUSPICIOUS_INPUT_SANITIZED" if action_taken == "SANITIZED" else "SUSPICIOUS_INPUT_BLOCKED"
    audit(audit_action, safe_details=details)


def jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret and os.getenv("FLASK_DEBUG") == "1":
        return "local-dev-only-change-me"
    if not secret or len(secret) < 32:
        raise RuntimeError("JWT_SECRET must be configured with at least 32 characters")
    return secret


def auth_required(handler):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            log_unauthorized("MISSING_TOKEN")
            return problem("Authentication required", 401)
        token = header.removeprefix("Bearer ").strip()
        try:
            decoded = jwt_decode(token, jwt_secret())
        except ValueError:
            log_unauthorized("INVALID_TOKEN")
            return problem("Authentication required", 401)
        user = get_user(str(decoded.get("sub", "")))
        if not user or not user.get("isActive", True):
            log_unauthorized("INACTIVE_OR_UNKNOWN_USER", "user", str(decoded.get("sub", "")))
            return problem("Authentication required", 401)
        if user.get("role") not in ROLES:
            log_unauthorized("INVALID_USER_ROLE", "user", user.get("id"))
            return problem("Authentication required", 401)
        g.user = user
        return handler(*args, **kwargs)

    return wrapper


def roles_required(*roles):
    def decorator(handler):
        @wraps(handler)
        def wrapper(*args, **kwargs):
            if g.user.get("role") not in roles:
                log_unauthorized("ROLE_FORBIDDEN")
                return problem("Forbidden", 403)
            return handler(*args, **kwargs)

        return wrapper

    return decorator


def rate_limit(name: str, max_requests: int, window_seconds: int):
    def decorator(handler):
        @wraps(handler)
        def wrapper(*args, **kwargs):
            ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
            user_part = getattr(g, "user", {}).get("id", "anon") if hasattr(g, "user") else "anon"
            key = f"{name}:{user_part}:{ip}"
            now = time.time()
            hits = [hit for hit in RATE_BUCKETS.get(key, []) if now - hit < window_seconds]
            if len(hits) >= max_requests:
                audit("RATE_LIMITED", user_id=getattr(g, "user", {}).get("id"), user_role=getattr(g, "user", {}).get("role"), safe_details={"bucket": name})
                return problem("Too many requests. Please try again later.", 429)
            hits.append(now)
            RATE_BUCKETS[key] = hits
            return handler(*args, **kwargs)

        return wrapper

    return decorator


def require_complaint_access(complaint_id: str, allow_staff: bool = False, admin_all: bool = True) -> Dict[str, Any]:
    complaint_id = validate_doc_id(complaint_id, "complaint_id")
    complaint = get_complaint(complaint_id)
    if not complaint:
        raise NotFoundError("Complaint not found")
    role = g.user.get("role")
    if role == "ADMIN" and admin_all:
        return complaint
    if role == "STUDENT" and complaint.get("studentId") == g.user["id"]:
        return complaint
    if allow_staff and role == "STAFF" and complaint.get("assignedStaffId") == g.user["id"]:
        return complaint
    log_unauthorized("COMPLAINT_IDOR_ATTEMPT", "complaint", complaint_id)
    raise ForbiddenError("Forbidden")


def validate_text(value: Any, field: str, min_len: int, max_len: int, source: str = "INPUT", block_xss: bool = False) -> str:
    if not isinstance(value, str):
        detection = detect_suspicious_input(value)
        if detection:
            record_suspicious_input(source, field, value, detection, "BLOCKED", 400)
            raise SuspiciousInputError(SUSPICIOUS_INPUT_MESSAGE)
        raise ValueError(f"{field} must be text")
    detection = detect_suspicious_input(value)
    if detection:
        if detection["category"] == "XSS_PAYLOAD" and not block_xss:
            record_suspicious_input(source, field, value, detection, "SANITIZED", 200)
        else:
            record_suspicious_input(source, field, value, detection, "BLOCKED", 400)
            raise SuspiciousInputError(SUSPICIOUS_INPUT_MESSAGE)
    cleaned = strip_html(value.strip())
    if len(cleaned) < min_len or len(cleaned) > max_len:
        raise ValueError(f"{field} must be between {min_len} and {max_len} characters")
    return cleaned


def validate_optional_text(value: Any, field: str, min_len: int, max_len: int, source: str = "INPUT", block_xss: bool = False) -> str:
    if value in (None, ""):
        return ""
    return validate_text(value, field, min_len, max_len, source=source, block_xss=block_xss)


def validate_email(value: Any, source: str = "INPUT") -> str:
    detection = detect_suspicious_input(value)
    if detection:
        record_suspicious_input(source, "email", value, detection, "BLOCKED", 400)
        raise SuspiciousInputError(SUSPICIOUS_INPUT_MESSAGE)
    if not isinstance(value, str):
        raise ValueError("email must be text")
    email = value.strip().lower()
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise ValueError("Invalid email")
    return email


def validate_password(value: Any) -> str:
    if not isinstance(value, str) or len(value) < 10 or len(value) > 128:
        raise ValueError("Password must be 10 to 128 characters")
    if not re.search(r"[A-Z]", value) or not re.search(r"[a-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must include uppercase, lowercase, and number")
    return value


def validate_login_password(value: Any) -> str:
    if not isinstance(value, str) or len(value) < 1 or len(value) > 128:
        raise ValueError("Invalid email or password.")
    return value


def validate_enum(value: Any, allowed: set, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} is invalid")
    normalized = value.strip().upper().replace(" ", "_")
    if normalized not in allowed:
        raise ValueError(f"{field} is invalid")
    return normalized


def validate_doc_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not DOC_ID_RE.match(value):
        raise ValueError(f"{field} is invalid")
    return value


def require_valid_doc_id(value: Any, field: str) -> str:
    return validate_doc_id(value, field)


def validate_evidence(value: Any) -> Dict[str, Any]:
    if not value:
        return {}
    if not isinstance(value, dict):
        audit("FILE_UPLOAD_REJECTED", safe_details={"reason": "invalid_payload"})
        raise ValueError("Evidence payload is invalid")
    name = str(value.get("name", ""))
    mime = str(value.get("type", ""))
    data_url = str(value.get("base64", ""))
    detection = detect_suspicious_input(name)
    if detection:
        record_suspicious_input("FILE_UPLOAD", "filename", name, detection, "REJECTED_UPLOAD", 400)
        audit("FILE_UPLOAD_REJECTED", safe_details={"reason": "suspicious_filename", "detectedPattern": detection["label"]})
        raise ValueError("Evidence file type is not allowed")
    extension_parts = [f".{part.lower()}" for part in name.split(".")[1:]]
    final_ext = extension_parts[-1] if extension_parts else ""
    if not name or final_ext not in SAFE_FILE_EXTENSIONS or any(ext in BLOCKED_FILE_EXTENSIONS for ext in extension_parts) or mime not in SAFE_MIME_TYPES:
        upload_detection = {"category": "MALICIOUS_FILE_UPLOAD", "label": "Malicious file upload rejected", "severity": "HIGH"}
        record_suspicious_input("FILE_UPLOAD", "filename", name, upload_detection, "REJECTED_UPLOAD", 400)
        audit("FILE_UPLOAD_REJECTED", safe_details={"reason": "bad_type", "mime": mime, "extension": final_ext})
        raise ValueError("Evidence file type is not allowed")
    try:
        raw = data_url.split(",", 1)[1] if "," in data_url else data_url
        decoded = base64.b64decode(raw, validate=True)
    except Exception:
        audit("FILE_UPLOAD_REJECTED", safe_details={"reason": "bad_base64"})
        raise ValueError("Evidence file content is invalid")
    if len(decoded) > MAX_FILE_BYTES:
        audit("FILE_UPLOAD_REJECTED", safe_details={"reason": "too_large", "size": len(decoded)})
        raise ValueError("Evidence file must be 2 MB or less")
    if not file_signature_matches(decoded, mime):
        upload_detection = {"category": "MALICIOUS_FILE_UPLOAD", "label": "Malicious file upload rejected", "severity": "HIGH"}
        record_suspicious_input("FILE_UPLOAD", "filename", name, upload_detection, "REJECTED_UPLOAD", 400)
        audit("FILE_UPLOAD_REJECTED", safe_details={"reason": "signature_mismatch", "mime": mime})
        raise ValueError("Evidence file signature does not match its type")
    evidence_id = f"{uuid.uuid4()}{final_ext}"
    # Demo-safe storage: metadata/path is stored in Firestore. Content should be placed in private GCS for production.
    return {"evidenceFilePath": f"evidence/{evidence_id}", "evidenceMimeType": mime, "evidenceSize": len(decoded), "evidenceOriginalName": strip_html(name)}


def file_signature_matches(data: bytes, mime: str) -> bool:
    if mime == "application/pdf":
        return data.startswith(b"%PDF")
    if mime == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if mime == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    return False


def normalize_ai_result(raw: Dict[str, Any]) -> Dict[str, Any]:
    legacy_priority = str(raw.get("priority", "Low")).title()
    if legacy_priority not in {"High", "Medium", "Low"}:
        legacy_priority = "Low"
    score = max(0, min(100, int(raw.get("priority_score", 30))))
    priority_label = "URGENT" if bool(raw.get("escalation_required")) and legacy_priority == "High" else legacy_priority.upper()
    if priority_label not in PRIORITIES:
        priority_label = "LOW"
    reason = validate_optional_text(str(raw.get("ai_reason", "Classified using safe AI triage rules.")), "aiReason", 0, 240, source="AI_OUTPUT") or "Classified using safe AI triage rules."
    return {
        "category": validate_optional_text(str(raw.get("category", "General")), "category", 0, 80, source="AI_OUTPUT") or "General",
        "legacyPriority": legacy_priority,
        "priorityLabel": priority_label,
        "priority_score": score,
        "aiReason": reason,
        "sdg": raw.get("sdg") if raw.get("sdg") in {"SDG 9", "SDG 16"} else "SDG 9",
        "aiEscalationRequired": bool(raw.get("escalation_required", False)),
        "assigned_department": validate_optional_text(str(raw.get("assigned_department", "General Services")), "assigned_department", 0, 80, source="AI_OUTPUT") or "General Services",
    }


def sanitize_ai_text(value: str) -> str:
    return strip_html(str(value or "")[:2000])


def audit(action: str, user_id: Optional[str] = None, user_role: Optional[str] = None, target_type: Optional[str] = None, target_id: Optional[str] = None, safe_details: Optional[Dict[str, Any]] = None) -> None:
    actor = getattr(g, "user", None)
    entry = {
        "userId": user_id or (actor or {}).get("id"),
        "userRole": user_role or (actor or {}).get("role"),
        "action": action,
        "targetType": target_type,
        "targetId": target_id,
        "ipAddress": request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip(),
        "userAgent": (request.headers.get("User-Agent", "") or "")[:200],
        "safeDetails": safe_details or {},
    }
    create_audit_log(entry)


def log_unauthorized(event: str, target_type: Optional[str] = None, target_id: Optional[str] = None) -> None:
    audit("UNAUTHORIZED_ACCESS_ATTEMPT", target_type=target_type, target_id=target_id, safe_details={"event": event, "path": request.path})
    create_security_event({"eventType": event, "severity": "HIGH", "source": "backend", "userId": getattr(g, "user", {}).get("id"), "details": {"path": request.path, "method": request.method}})


def problem(message: str, status: int):
    return jsonify({"error": message}), status


def mask_email(email: str) -> str:
    if "@" not in email:
        return "invalid"
    local, domain = email.split("@", 1)
    return f"{local[:2]}***@{domain}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def seed_demo_users():
    demo_password = os.getenv("DEMO_PASSWORD")
    if not demo_password:
        raise ValueError("DEMO_PASSWORD must be configured before demo seeding.")
    validate_password(demo_password)
    rows = [
        ("admin-demo", "Admin User", "admin@example.com", "ADMIN"),
        ("staff-demo", "Staff User", "staff@example.com", "STAFF"),
        ("student1-demo", "Student One", "student1@example.com", "STUDENT"),
        ("student2-demo", "Student Two", "student2@example.com", "STUDENT"),
    ]
    seeded = []
    now = utc_now()
    for uid, name, email, role in rows:
        existing = get_user_by_email(email)
        if existing:
            seeded.append({"email": email, "status": "exists"})
            continue
        create_user(uid, {"uid": uid, "name": name, "email": email, "role": role, "isActive": True, "passwordHash": generate_password_hash(demo_password), "createdAt": now, "updatedAt": now})
        seeded.append({"email": email, "role": role, "status": "created"})
    return seeded


class ForbiddenError(Exception):
    pass


class NotFoundError(Exception):
    pass


class SuspiciousInputError(Exception):
    pass


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG") == "1")
