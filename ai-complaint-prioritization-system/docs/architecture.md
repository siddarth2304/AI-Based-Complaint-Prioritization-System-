# Architecture

## Overview

The AI-Based Complaint Prioritization System is a cloud-native complaint triage application. Users submit complaints through a React dashboard. A Flask REST API deployed on Cloud Run classifies complaints with Vertex AI Gemini, calculates SLA deadlines, stores the result in Firestore, and exposes analytics for the dashboard. A Cloud Function provides automated post-processing for escalation checks.

## Flow

1. User submits a complaint from the React + Vite frontend.
2. Frontend calls `POST /api/complaints` on the Cloud Run backend.
3. Backend sends title and description to Vertex AI Gemini.
4. Gemini returns category, priority, priority score, explainable reason, SDG mapping, and escalation flag.
5. Backend calculates SLA deadline based on priority.
6. Full complaint document is stored in Firestore collection `complaints`.
7. Admin dashboard fetches complaint list and aggregate stats.
8. Cloud Function can be triggered after creation to re-check urgent keywords and update `escalation_required`.

## Google Cloud Components

- Cloud Run: Hosts the containerized Flask API.
- Firestore: Stores complaint records and AI classification output.
- Vertex AI: Runs Gemini-based complaint classification.
- Cloud Functions: Performs automated escalation post-processing.
