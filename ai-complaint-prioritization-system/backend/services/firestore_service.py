import os
import uuid
from datetime import datetime, timezone


_memory_store = {}
_firestore_client = None


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


def create_complaint(data):
    db = get_firestore_client()
    if db:
        doc_ref = db.collection("complaints").document()
        doc_ref.set(data)
        return {"id": doc_ref.id, **data}

    complaint_id = str(uuid.uuid4())
    _memory_store[complaint_id] = data
    return {"id": complaint_id, **data}


def list_complaints():
    db = get_firestore_client()
    if db:
        docs = db.collection("complaints").order_by("created_at", direction="DESCENDING").stream()
        return sort_complaints([{"id": doc.id, **doc.to_dict()} for doc in docs])

    return sort_complaints([{"id": complaint_id, **data} for complaint_id, data in _memory_store.items()])


def update_complaint_status(complaint_id, status):
    now = datetime.now(timezone.utc).isoformat()
    db = get_firestore_client()
    if db:
        doc_ref = db.collection("complaints").document(complaint_id)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            return None
        doc_ref.update({"status": status, "updated_at": now})
        updated = doc_ref.get().to_dict()
        return {"id": complaint_id, **updated}

    if complaint_id not in _memory_store:
        return None
    _memory_store[complaint_id]["status"] = status
    _memory_store[complaint_id]["updated_at"] = now
    return {"id": complaint_id, **_memory_store[complaint_id]}


def get_complaint(complaint_id):
    db = get_firestore_client()
    if db:
        doc = db.collection("complaints").document(complaint_id).get()
        return {"id": doc.id, **doc.to_dict()} if doc.exists else None
    
    data = _memory_store.get(complaint_id)
    return {"id": complaint_id, **data} if data else None


def save_complaint_solution(complaint_id, solution):
    now = datetime.now(timezone.utc).isoformat()
    db = get_firestore_client()
    if db:
        doc_ref = db.collection("complaints").document(complaint_id)
        if doc_ref.get().exists:
            doc_ref.update({"ai_solution": solution, "updated_at": now})
            return {"id": complaint_id, **doc_ref.get().to_dict()}
        return None

    if complaint_id in _memory_store:
        _memory_store[complaint_id]["ai_solution"] = solution
        _memory_store[complaint_id]["updated_at"] = now
        return {"id": complaint_id, **_memory_store[complaint_id]}
    return None


def update_complaint_rating(complaint_id, rating):
    now = datetime.now(timezone.utc).isoformat()
    db = get_firestore_client()
    if db:
        doc_ref = db.collection("complaints").document(complaint_id)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            return None
        doc_ref.update({"satisfaction_rating": rating, "rating_submitted_at": now, "updated_at": now})
        updated = doc_ref.get().to_dict()
        return {"id": complaint_id, **updated}

    if complaint_id not in _memory_store:
        return None
    _memory_store[complaint_id]["satisfaction_rating"] = rating
    _memory_store[complaint_id]["rating_submitted_at"] = now
    _memory_store[complaint_id]["updated_at"] = now
    return {"id": complaint_id, **_memory_store[complaint_id]}


def get_complaint_stats():
    complaints = list_complaints()
    total = len(complaints)
    score_sum = sum(int(item.get("priority_score", 0)) for item in complaints)
    
    rated_complaints = [
        item for item in complaints
        if item.get("status") == "Resolved" and item.get("satisfaction_rating") is not None
    ]
    rating_sum = sum(int(item.get("satisfaction_rating", 0)) for item in rated_complaints)
    average_rating = round(rating_sum / len(rated_complaints), 1) if rated_complaints else 0

    return {
        "total": total,
        "high": count_by(complaints, "priority", "High"),
        "medium": count_by(complaints, "priority", "Medium"),
        "low": count_by(complaints, "priority", "Low"),
        "pending": count_by(complaints, "status", "Pending"),
        "in_progress": count_by(complaints, "status", "In Progress"),
        "resolved": count_by(complaints, "status", "Resolved"),
        "average_priority_score": round(score_sum / total, 2) if total else 0,
        "average_satisfaction_rating": average_rating,
        "sdg_9_count": count_by(complaints, "sdg", "SDG 9"),
        "sdg_16_count": count_by(complaints, "sdg", "SDG 16"),
        "escalation_count": sum(1 for item in complaints if item.get("escalation_required")),
        "image_complaint_count": sum(1 for item in complaints if item.get("image_uploaded")),
    }


def count_by(items, field, value):
    return sum(1 for item in items if item.get(field) == value)


def sort_complaints(complaints):
    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(
        complaints,
        key=lambda item: (
            0 if item.get("escalation_required") else 1,
            priority_rank.get(item.get("priority"), 3),
            -timestamp_value(item.get("created_at", "")),
        ),
    )


def timestamp_value(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0
