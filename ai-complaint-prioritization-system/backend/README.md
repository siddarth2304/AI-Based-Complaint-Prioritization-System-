# Backend - AI Complaint Prioritization System

Flask REST API for complaint submission, AI priority classification, SLA calculation, Firestore persistence, image evidence, Ask AI Assistance, status updates, and satisfaction ratings.

## Local Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export USE_IN_MEMORY_DB=true
python app.py
```

The app runs on `http://localhost:8080`.

## Important Endpoints

- `GET /api/health`
- `POST /api/complaints`
- `GET /api/complaints`
- `GET /api/complaints/stats`
- `PATCH /api/complaints/<id>/status`
- `PATCH /api/complaints/<id>/rating`
- `POST /api/complaints/<id>/solution`
- `POST /api/ai/assist`

## Cloud Notes

- Deploy this folder to Cloud Run using the provided Dockerfile.
- Firestore collection: `complaints`.
- Optional images are stored directly on the complaint document as small Base64 evidence for this academic prototype.
- Vertex AI Gemini is used when Google Cloud credentials and project variables are configured.
- If Vertex AI or Firestore is unavailable, the app remains demo-friendly through fallback classification and optional in-memory storage.
