import os
from datetime import datetime, timezone

from flask import jsonify, Request
from google.cloud import firestore


URGENT_WORDS = {"danger", "harassment", "accident", "security", "medical", "fire", "urgent"}


def escalation_checker(request: Request):
    """HTTP Cloud Function that marks urgent complaints for escalation."""
    payload = request.get_json(silent=True) or {}
    complaint_id = payload.get("complaint_id")
    if not complaint_id:
        return jsonify({"error": "complaint_id is required"}), 400

    project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    db = firestore.Client(project=project_id) if project_id else firestore.Client()
    doc_ref = db.collection("complaints").document(complaint_id)
    snapshot = doc_ref.get()
    if not snapshot.exists:
        return jsonify({"error": "Complaint not found"}), 404

    complaint = snapshot.to_dict()
    text = f"{complaint.get('title', '')} {complaint.get('description', '')}".lower()
    should_escalate = bool(complaint.get("escalation_required")) or any(word in text for word in URGENT_WORDS)

    updates = {
        "escalation_required": should_escalate,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if should_escalate:
        updates["escalation_note"] = "Cloud Function marked this complaint for immediate attention."

    doc_ref.update(updates)
    return jsonify({"complaint_id": complaint_id, **updates})
