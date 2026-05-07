# AI-Based Complaint Prioritization System

## Smart Triage using Cloud & AI

## Abstract

Organizations receive many complaints every day, but traditional complaint systems usually process them in submission order without understanding urgency. This project builds a cloud-native complaint triage system that uses AI/NLP to classify each complaint into High, Medium, or Low priority, assigns a numeric urgency score, explains the decision, maps the complaint to SDG 9 or SDG 16, calculates an SLA deadline, and stores the result in Firestore.

## Problem Statement

Manual complaint handling can delay urgent safety, security, and infrastructure issues because all complaints are treated equally. Administrators need a smart system that can identify critical complaints quickly and provide a dashboard for fast action.

## Objectives

- Submit complaints through a modern web dashboard.
- Classify complaints using Vertex AI Gemini.
- Generate AI priority score from 0 to 100.
- Provide explainable AI reason for every classification.
- Map complaints to SDG 9 or SDG 16.
- Calculate SLA deadline based on priority.
- Store complaint records in Firestore.
- Provide dashboard analytics and filtering.
- Include Cloud Function based escalation post-processing.
- Run locally using fallback rule-based classification when cloud credentials are unavailable.

## Novelty / USP

- AI Priority Score: numeric urgency score from 0 to 100.
- Explainable AI Reason: reason shown in the admin table.
- SDG Mapping: automatic mapping to SDG 9 or SDG 16.
- SLA Countdown: High gets 24 hours, Medium gets 72 hours, Low gets 7 days.
- Smart Dashboard: total, priority counts, status counts, average score, SDG distribution, and escalation count.
- Escalation Flag: serious words such as danger, harassment, accident, security, medical, fire, or urgent are marked as immediate attention.
- Cloud-ready Architecture: backend deploys to Cloud Run, data goes to Firestore, AI uses Vertex AI, and escalation automation is represented by Cloud Functions.

## SDG Relevance

- SDG 9: Industry, Innovation and Infrastructure. Used for complaints related to WiFi, labs, classroom equipment, electricity, systems, and infrastructure.
- SDG 16: Peace, Justice and Strong Institutions. Used for complaints related to safety, harassment, security, emergency, governance, or institutional trust.

## Google Cloud Components Used

- Cloud Run: Hosts the containerized Flask backend API.
- Firestore: Stores complaint documents and dashboard data.
- Vertex AI Gemini: Performs AI/NLP complaint classification.
- Cloud Functions: Performs automated escalation post-processing.

## Architecture Explanation

The React frontend submits complaints to a Flask API. The API builds a structured Gemini prompt and requests classification from Vertex AI. The response includes category, priority, priority score, reason, SDG mapping, and escalation flag. The backend calculates SLA deadline and stores the full document in Firestore. The dashboard fetches complaint records and aggregate statistics. An HTTP Cloud Function can be called after complaint creation to re-check serious terms and update escalation fields in Firestore.

## Local Setup Instructions

### Backend

```bash
cd ai-complaint-prioritization-system/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export USE_IN_MEMORY_DB=true
python app.py
```

### Frontend

```bash
cd ai-complaint-prioritization-system/frontend
npm install
export VITE_API_BASE_URL=http://localhost:8080
npm run dev
```

## Google Cloud Deployment Steps

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com firestore.googleapis.com aiplatform.googleapis.com cloudfunctions.googleapis.com artifactregistry.googleapis.com
gcloud firestore databases create --location=nam5
```

Deploy backend:

```bash
cd backend
gcloud run deploy ai-complaint-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT_ID=YOUR_PROJECT_ID,GCP_LOCATION=us-central1,VERTEX_MODEL=gemini-1.5-flash
```

Deploy Cloud Function:

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

## API Endpoints

- `GET /api/health`: app status and cloud components.
- `POST /api/complaints`: creates complaint, classifies priority, calculates SLA, stores in Firestore.
- `GET /api/complaints`: returns all complaints sorted newest first.
- `GET /api/complaints/stats`: returns dashboard metrics.
- `PATCH /api/complaints/<id>/status`: updates complaint status.

## Demo Flow

1. Start backend locally with `USE_IN_MEMORY_DB=true`.
2. Start frontend with `npm run dev`.
3. Submit “Fire issue in lab” and show High priority, high score, SDG 16, escalation flag, and 24-hour SLA.
4. Submit “WiFi slow in hostel” and show Medium priority, SDG 9, and 72-hour SLA.
5. Submit “Library seating suggestion” and show Low priority.
6. Show dashboard cards and charts updating automatically.
7. Update complaint status from Pending to In Progress to Resolved.
8. Explain Cloud Run, Firestore, Vertex AI, and Cloud Functions deployment path.

## Screenshots

- Home dashboard screenshot
- Complaint submission screenshot
- AI priority result screenshot
- Firestore collection screenshot
- Cloud Run service screenshot
- Cloud Function deployment screenshot

## Team Members

- E. Sahith Siddarth - AM.SC.U4CSE23217
- K. Sanithya - AM.SC.U4CSE23327
- E. Manoj - AM.SC.U4CSE23317
- S. Reshma Sri - AM.SC.U4CSE23250

## Course Details

- Course Code & Title: 23CSE363 - Cloud Computing
- Program: B.Tech CSE
- Semester: 6
- Academic Year: 2025-2026
- Course Instructor: Dr. Divya Udayan J
