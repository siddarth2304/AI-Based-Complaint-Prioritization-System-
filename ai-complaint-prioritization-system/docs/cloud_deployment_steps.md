# Google Cloud Deployment Steps

## 1. Login and Configure Project

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud auth application-default login
```

## 2. Enable APIs

```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

## 3. Create Firestore Database

```bash
gcloud firestore databases create --location=nam5
```

## 4. Deploy Backend to Cloud Run

```bash
cd backend
gcloud run deploy ai-complaint-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT_ID=YOUR_PROJECT_ID,GCP_LOCATION=us-central1,VERTEX_MODEL=gemini-1.5-flash
```

## 5. Run Frontend Locally

```bash
cd frontend
npm install
export VITE_API_BASE_URL=https://YOUR_CLOUD_RUN_URL
npm run dev
```

## 6. Deploy Cloud Function

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

## 7. Trigger Cloud Function After Complaint Creation

Call the function with a complaint id:

```bash
curl -X POST CLOUD_FUNCTION_URL \
  -H "Content-Type: application/json" \
  -d '{"complaint_id":"FIRESTORE_DOCUMENT_ID"}'
```
