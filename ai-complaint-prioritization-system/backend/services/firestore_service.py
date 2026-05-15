import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

_memory_store: Dict[str, Dict[str, Any]] = {}
_user_store: Dict[str, Dict[str, Any]] = {}
_audit_store: Dict[str, Dict[str, Any]] = {}
_security_event_store: Dict[str, Dict[str, Any]] = {}
_firestore_client = None

USERS = "users"
COMPLAINTS = "complaints"
AUDIT_LOGS = "auditLogs"
SECURITY_EVENTS = "securityEvents"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def server_timestamp():
    try:
        from google.cloud import firestore

        return firestore.SERVER_TIMESTAMP
    except Exception:
        return utc_now_iso()


def get_firestore_client():
    global _firestore_client
    if os.getenv("USE_IN_MEMORY_DB", "").lower() == "true":
        return None
    if _firestore_client is not None:
        return _firestore_client
    try:
        from google.cloud import firestore

        project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        _firestore_client = firestore.Client(project=project_id) if project_id else firestore.Client()
        return _firestore_client
    except Exception:
        return None


def _collection_store(name: str) -> Dict[str, Dict[str, Any]]:
    if name == USERS:
        return _user_store
    if name == AUDIT_LOGS:
        return _audit_store
    if name == SECURITY_EVENTS:
        return _security_event_store
    return _memory_store


def _doc(collection: str, document_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {"id": document_id, **(data or {})}


def create_document(collection: str, data: Dict[str, Any], document_id: Optional[str] = None) -> Dict[str, Any]:
    db = get_firestore_client()
    if db:
        doc_ref = db.collection(collection).document(document_id) if document_id else db.collection(collection).document()
        doc_ref.set(data)
        return _doc(collection, doc_ref.id, data)

    doc_id = document_id or str(uuid.uuid4())
    _collection_store(collection)[doc_id] = dict(data)
    return _doc(collection, doc_id, data)


def get_document(collection: str, document_id: str) -> Optional[Dict[str, Any]]:
    db = get_firestore_client()
    if db:
        snap = db.collection(collection).document(document_id).get()
        return _doc(collection, snap.id, snap.to_dict()) if snap.exists else None
    data = _collection_store(collection).get(document_id)
    return _doc(collection, document_id, data) if data else None


def update_document(collection: str, document_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = get_firestore_client()
    if db:
        doc_ref = db.collection(collection).document(document_id)
        if not doc_ref.get().exists:
            return None
        doc_ref.update(updates)
        snap = doc_ref.get()
        return _doc(collection, document_id, snap.to_dict())

    store = _collection_store(collection)
    if document_id not in store:
        return None
    store[document_id].update(updates)
    return _doc(collection, document_id, store[document_id])


def delete_sensitive_user_fields(user: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not user:
        return None
    cleaned = dict(user)
    cleaned.pop("passwordHash", None)
    return cleaned


def create_user(uid: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return create_document(USERS, data, uid)


def get_user(uid: str) -> Optional[Dict[str, Any]]:
    return get_document(USERS, uid)


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    normalized = email.strip().lower()
    db = get_firestore_client()
    if db:
        docs = db.collection(USERS).where("email", "==", normalized).limit(1).stream()
        for doc in docs:
            return _doc(USERS, doc.id, doc.to_dict())
        return None
    for uid, data in _user_store.items():
        if data.get("email") == normalized:
            return _doc(USERS, uid, data)
    return None


def list_users() -> List[Dict[str, Any]]:
    db = get_firestore_client()
    if db:
        docs = db.collection(USERS).order_by("createdAt", direction="DESCENDING").stream()
        return [delete_sensitive_user_fields(_doc(USERS, doc.id, doc.to_dict())) for doc in docs]
    return [delete_sensitive_user_fields(_doc(USERS, uid, data)) for uid, data in sorted(_user_store.items())]


def update_user(uid: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return update_document(USERS, uid, updates)


def create_complaint(data: Dict[str, Any]) -> Dict[str, Any]:
    return create_document(COMPLAINTS, data)


def get_complaint(complaint_id: str) -> Optional[Dict[str, Any]]:
    return get_document(COMPLAINTS, complaint_id)


def list_complaints(filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    filters = filters or {}
    db = get_firestore_client()
    if db:
        query = db.collection(COMPLAINTS)
        for field, value in filters.items():
            if value is not None:
                query = query.where(field, "==", value)
        docs = query.stream()
        return sort_complaints([_doc(COMPLAINTS, doc.id, doc.to_dict()) for doc in docs])

    rows = []
    for complaint_id, data in _memory_store.items():
        if all(data.get(field) == value for field, value in filters.items() if value is not None):
            rows.append(_doc(COMPLAINTS, complaint_id, data))
    return sort_complaints(rows)


def update_complaint(complaint_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return update_document(COMPLAINTS, complaint_id, updates)


def update_complaint_status(complaint_id: str, status: str, staff_note: str = "") -> Optional[Dict[str, Any]]:
    updates = {"status": status, "updatedAt": utc_now_iso(), "updated_at": utc_now_iso()}
    if staff_note:
        updates["staffNote"] = staff_note
    return update_complaint(complaint_id, updates)


def update_complaint_rating(complaint_id: str, rating: int) -> Optional[Dict[str, Any]]:
    now = utc_now_iso()
    return update_complaint(
        complaint_id,
        {"satisfaction_rating": rating, "rating_submitted_at": now, "updatedAt": now, "updated_at": now},
    )


def save_complaint_solution(complaint_id: str, solution: str) -> Optional[Dict[str, Any]]:
    now = utc_now_iso()
    return update_complaint(complaint_id, {"ai_solution": solution, "updatedAt": now, "updated_at": now})


def assign_complaint(complaint_id: str, staff_uid: str) -> Optional[Dict[str, Any]]:
    now = utc_now_iso()
    return update_complaint(complaint_id, {"assignedStaffId": staff_uid, "updatedAt": now, "updated_at": now})


def get_complaint_stats(role: str = "ADMIN", user_id: Optional[str] = None) -> Dict[str, Any]:
    complaints = visible_complaints(role, user_id)
    users = list_users() if role == "ADMIN" else []
    total = len(complaints)
    score_sum = sum(int(item.get("priority_score", 0)) for item in complaints)
    rated = [item for item in complaints if item.get("status") in {"Resolved", "RESOLVED"} and item.get("satisfaction_rating") is not None]
    rating_sum = sum(int(item.get("satisfaction_rating", 0)) for item in rated)

    return {
        "total": total,
        "totalUsers": len(users),
        "high": count_priority(complaints, "High", "HIGH"),
        "medium": count_priority(complaints, "Medium", "MEDIUM"),
        "low": count_priority(complaints, "Low", "LOW"),
        "urgent": count_priority(complaints, "Urgent", "URGENT"),
        "pending": count_status(complaints, "Pending", "OPEN"),
        "in_progress": count_status(complaints, "In Progress", "IN_PROGRESS"),
        "resolved": count_status(complaints, "Resolved", "RESOLVED"),
        "rejected": count_status(complaints, "Rejected", "REJECTED"),
        "average_priority_score": round(score_sum / total, 2) if total else 0,
        "average_satisfaction_rating": round(rating_sum / len(rated), 1) if rated else 0,
        "sdg_9_count": count_by(complaints, "sdg", "SDG 9"),
        "sdg_16_count": count_by(complaints, "sdg", "SDG 16"),
        "escalation_count": sum(1 for item in complaints if item.get("aiEscalationRequired") or item.get("escalation_required")),
        "image_complaint_count": sum(1 for item in complaints if item.get("evidenceFilePath") or item.get("image_uploaded")),
    }


def visible_complaints(role: str, user_id: Optional[str]) -> List[Dict[str, Any]]:
    if role == "ADMIN":
        return list_complaints()
    if role == "STAFF":
        return list_complaints({"assignedStaffId": user_id})
    return list_complaints({"studentId": user_id})


def create_audit_log(entry: Dict[str, Any]) -> Dict[str, Any]:
    safe = dict(entry)
    safe.setdefault("createdAt", utc_now_iso())
    return create_document(AUDIT_LOGS, safe)


def list_audit_logs(limit: int = 100) -> List[Dict[str, Any]]:
    db = get_firestore_client()
    if db:
        docs = db.collection(AUDIT_LOGS).order_by("createdAt", direction="DESCENDING").limit(limit).stream()
        return [_doc(AUDIT_LOGS, doc.id, doc.to_dict()) for doc in docs]
    rows = [_doc(AUDIT_LOGS, log_id, data) for log_id, data in _audit_store.items()]
    return sorted(rows, key=lambda item: str(item.get("createdAt", "")), reverse=True)[:limit]


def create_security_event(entry: Dict[str, Any]) -> Dict[str, Any]:
    safe = dict(entry)
    safe.setdefault("createdAt", utc_now_iso())
    return create_document(SECURITY_EVENTS, safe)


def list_security_events(limit: int = 100) -> List[Dict[str, Any]]:
    db = get_firestore_client()
    if db:
        docs = db.collection(SECURITY_EVENTS).order_by("createdAt", direction="DESCENDING").limit(limit).stream()
        return [_doc(SECURITY_EVENTS, doc.id, doc.to_dict()) for doc in docs]
    rows = [_doc(SECURITY_EVENTS, event_id, data) for event_id, data in _security_event_store.items()]
    return sorted(rows, key=lambda item: str(item.get("createdAt", "")), reverse=True)[:limit]


def count_by(items: Iterable[Dict[str, Any]], field: str, value: Any) -> int:
    return sum(1 for item in items if item.get(field) == value)


def count_status(items: Iterable[Dict[str, Any]], *values: str) -> int:
    allowed = set(values)
    return sum(1 for item in items if item.get("status") in allowed)


def count_priority(items: Iterable[Dict[str, Any]], *values: str) -> int:
    allowed = set(values)
    return sum(1 for item in items if item.get("priority") in allowed)


def sort_complaints(complaints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    priority_rank = {"Urgent": 0, "URGENT": 0, "High": 1, "HIGH": 1, "Medium": 2, "MEDIUM": 2, "Low": 3, "LOW": 3}
    return sorted(
        complaints,
        key=lambda item: (
            0 if item.get("aiEscalationRequired") or item.get("escalation_required") else 1,
            priority_rank.get(item.get("priority"), 4),
            -timestamp_value(item.get("createdAt") or item.get("created_at") or ""),
        ),
    )


def timestamp_value(value: Any) -> float:
    if hasattr(value, "timestamp"):
        return value.timestamp()
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0
