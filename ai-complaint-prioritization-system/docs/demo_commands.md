# Demo Commands

## Google Cloud Login

```bash
gcloud auth login
gcloud auth application-default login
```

## Project Creation or Selection

```bash
gcloud projects create YOUR_PROJECT_ID --name="AI Complaint Prioritization"
gcloud config set project YOUR_PROJECT_ID
```

If the project already exists:

```bash
gcloud config set project YOUR_PROJECT_ID
```

## Enable Required APIs

```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

## Firestore Setup

```bash
gcloud firestore databases create --location=nam5
```

## Backend Local Run

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export USE_IN_MEMORY_DB=true
python app.py
```

## Backend Deployment to Cloud Run

```bash
cd backend
gcloud run deploy ai-complaint-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT_ID=YOUR_PROJECT_ID,GCP_LOCATION=us-central1,VERTEX_MODEL=gemini-1.5-flash
```

## Frontend Local Run

```bash
cd frontend
npm install
export VITE_API_BASE_URL=http://localhost:8080
npm run dev
```

For Cloud Run backend:

```bash
export VITE_API_BASE_URL=https://YOUR_CLOUD_RUN_URL
npm run dev
```

## Cloud Function Deployment

```bash
cd cloud_function_escalation
gcloud functions deploy escalation_checker \
  --gen2 \
  --runtime python311 \
  --region us-central1 \
  --source . \
  --entry-point escalation_checker \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT_ID=YOUR_PROJECT_ID
```

## API Tests with curl

```bash
curl http://localhost:8080/api/health
```

```bash
curl -X POST http://localhost:8080/api/complaints \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sahith",
    "email": "student@example.com",
    "department": "CSE",
    "title": "Fire issue in lab",
    "description": "There is smoke and fire smell near the computer lab."
  }'
```

```bash
curl http://localhost:8080/api/complaints
curl http://localhost:8080/api/complaints/stats
```

```bash
curl -X PATCH http://localhost:8080/api/complaints/COMPLAINT_ID/status \
  -H "Content-Type: application/json" \
  -d '{"status":"Resolved"}'
```

```bash
curl -X POST CLOUD_FUNCTION_URL \
  -H "Content-Type: application/json" \
  -d '{"complaint_id":"COMPLAINT_ID"}'
```
