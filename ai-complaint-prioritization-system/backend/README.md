# Backend - AI Complaint Prioritization System

Flask REST API for complaint submission, AI priority classification, SLA calculation, Firestore persistence, and status updates.

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

## Cloud Notes

- Deploy this folder to Cloud Run using the provided Dockerfile.
- Firestore collection: `complaints`.
- Vertex AI Gemini is used when Google Cloud credentials and project variables are configured.
- If Vertex AI or Firestore is unavailable, the app remains demo-friendly through fallback classification and optional in-memory storage.
