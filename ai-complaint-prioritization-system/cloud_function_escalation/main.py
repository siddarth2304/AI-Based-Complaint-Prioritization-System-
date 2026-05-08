import os
from datetime import datetime, timezone
from flask import jsonify, Request
from google.cloud import firestore

URGENT_KEYWORDS = [
    "urgent", "emergency", "fire", "accident", "danger", "harassment",
    "security", "medical", "violence", "threat", "unsafe", "smoke"
]


def escalate_complaint(request: Request):
    """
    HTTP Cloud Function for complaint escalation.
    This checks complaint text and marks serious complaints as escalation_required.
    """

    if request.method == "GET":
        return jsonify({
            "status": "ok",
            "function": "complaint-escalation-function",
            "message": "Cloud Function is running"
        }), 200

    try:
        data = request.get_json(silent=True) or {}

        complaint_id = data.get("complaint_id") or data.get("id")
        title = data.get("title", "")
        description = data.get("description", "")
        priority = data.get("priority", "")

        combined_text = f"{title} {description} {priority}".lower()

        escalation_required = (
            priority.lower() == "high"
            or any(keyword in combined_text for keyword in URGENT_KEYWORDS)
        )

        result = {
            "complaint_id": complaint_id,
            "escalation_required": escalation_required,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "reason": "Urgent keyword or High priority detected."
            if escalation_required
            else "No urgent escalation keyword detected."
        }

        # Optional Firestore update if complaint_id exists
        if complaint_id:
            try:
                db = firestore.Client(project=os.getenv("GCP_PROJECT_ID"))
                db.collection("complaints").document(complaint_id).set(
                    {
                        "escalation_required": escalation_required,
                        "escalation_checked_at": result["checked_at"],
                        "escalation_reason": result["reason"],
                    },
                    merge=True,
                )
                result["firestore_updated"] = True
            except Exception as firestore_error:
                result["firestore_updated"] = False
                result["firestore_error"] = str(firestore_error)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "failed"
        }), 500