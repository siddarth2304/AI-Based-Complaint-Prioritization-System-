import os
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

from services.ai_priority_service import classify_complaint, generate_resolution_sop
from services.firestore_service import (
    create_complaint,
    get_complaint_stats,
    list_complaints,
    update_complaint_status,
    update_complaint_rating,
    get_complaint,
    save_complaint_solution,
)
from services.sla_service import calculate_sla_deadline


PROJECT_NAME = "AI-Based Complaint Prioritization System"
CLOUD_COMPONENTS = ["Cloud Run", "Firestore", "Vertex AI", "Cloud Functions"]
ALLOWED_STATUSES = {"Pending", "In Progress", "Resolved"}


def create_app():
    app = Flask(__name__)
    CORS(app)

    @app.get("/api/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "project": PROJECT_NAME,
                "subtitle": "Smart Triage using Cloud & AI",
                "cloud_components_used": CLOUD_COMPONENTS,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    @app.post("/api/complaints")
    def submit_complaint():
        payload = request.get_json(silent=True) or {}
        required = ["name", "email", "department", "title", "description"]
        missing = [field for field in required if not str(payload.get(field, "")).strip()]
        if missing:
            return jsonify({"error": "Missing required fields", "missing": missing}), 400

        classification = classify_complaint(payload["title"], payload["description"], payload.get("image"))
        now = datetime.now(timezone.utc).isoformat()
        sla_deadline = calculate_sla_deadline(classification["priority"])

        complaint = {
            "name": payload["name"].strip(),
            "email": payload["email"].strip(),
            "department": payload["department"].strip(),
            "title": payload["title"].strip(),
            "description": payload["description"].strip(),
            "category": classification["category"],
            "priority": classification["priority"],
            "priority_score": int(classification["priority_score"]),
            "ai_reason": classification["ai_reason"],
            "sdg": classification["sdg"],
            "assigned_department": classification.get("assigned_department", "General Services"),
            "status": "Pending",
            "sla_deadline": sla_deadline,
            "escalation_required": bool(classification["escalation_required"]),
            "created_at": now,
            "updated_at": now,
        }

        created = create_complaint(complaint)
        return jsonify(created), 201

    @app.get("/api/complaints")
    def complaints():
        return jsonify(list_complaints())

    @app.get("/api/complaints/stats")
    def stats():
        return jsonify(get_complaint_stats())

    @app.patch("/api/complaints/<complaint_id>/status")
    def patch_status(complaint_id):
        payload = request.get_json(silent=True) or {}
        status = payload.get("status")
        if status not in ALLOWED_STATUSES:
            return jsonify({"error": "Invalid status", "allowed": sorted(ALLOWED_STATUSES)}), 400

        updated = update_complaint_status(complaint_id, status)
        if not updated:
            return jsonify({"error": "Complaint not found"}), 404
        return jsonify(updated)

    @app.patch("/api/complaints/<complaint_id>/rating")
    def patch_rating(complaint_id):
        payload = request.get_json(silent=True) or {}
        rating = payload.get("rating")
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({"error": "Rating must be an integer between 1 and 5"}), 400

        updated = update_complaint_rating(complaint_id, rating)
        if not updated:
            return jsonify({"error": "Complaint not found"}), 404
        return jsonify(updated)

    @app.post("/api/complaints/<complaint_id>/solution")
    def generate_solution(complaint_id):
        complaint = get_complaint(complaint_id)
        if not complaint:
            return jsonify({"error": "Complaint not found"}), 404

        if complaint.get("ai_solution"):
            return jsonify(complaint)

        solution_text = generate_resolution_sop(
            complaint.get("title", ""),
            complaint.get("description", ""),
            complaint.get("category", "")
        )
        
        updated = save_complaint_solution(complaint_id, solution_text)
        return jsonify(updated)

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG") == "1")
