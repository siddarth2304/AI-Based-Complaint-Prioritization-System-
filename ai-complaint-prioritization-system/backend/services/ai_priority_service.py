import json
import os
import re


HIGH_KEYWORDS = {
    "urgent",
    "emergency",
    "fire",
    "accident",
    "danger",
    "harassment",
    "security",
    "medical",
    "violence",
    "threat",
    "unsafe",
}
MEDIUM_KEYWORDS = {
    "delay",
    "not working",
    "broken",
    "issue",
    "problem",
    "slow",
    "unavailable",
    "failed",
}
LOW_KEYWORDS = {"suggestion", "request", "improvement", "feedback", "general"}


def classify_complaint(title, description):
    prompt = build_gemini_prompt(title, description)
    try:
        result = classify_with_vertex_ai(prompt)
        return normalize_classification(result)
    except Exception:
        return fallback_classifier(title, description)


def build_gemini_prompt(title, description):
    return f"""
You are an AI complaint triage engine for a cloud-based university/organization helpdesk.
Classify the complaint urgency using its title and description.

Return only valid JSON with exactly these keys:
category, priority, priority_score, ai_reason, sdg, escalation_required

Rules:
- priority must be one of High, Medium, Low.
- priority_score must be an integer from 0 to 100.
- sdg must be either "SDG 9" for infrastructure, systems, connectivity, lab equipment, electricity, transport, or innovation issues, or "SDG 16" for safety, justice, harassment, security, governance, rights, or institutional trust issues.
- escalation_required must be true when the complaint includes serious risk words or direct safety/security concerns.
- ai_reason must be concise and explain the urgency decision.

Examples:
- "Fire in lab" with smoke/fire risk => {{"category":"Safety","priority":"High","priority_score":95,"ai_reason":"The complaint indicates immediate safety risk due to smoke or fire.","sdg":"SDG 16","escalation_required":true}}
- "WiFi slow in hostel" => {{"category":"Infrastructure","priority":"Medium","priority_score":58,"ai_reason":"Connectivity is degraded and affects productivity, but no immediate safety threat is present.","sdg":"SDG 9","escalation_required":false}}
- "Fan not working in classroom" => Low or Medium depending severity and duration.
- "Harassment/security issue" => High with escalation_required true.
- "General suggestion for library seating" => Low.

Complaint title: {title}
Complaint description: {description}
"""


def classify_with_vertex_ai(prompt):
    project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GCP_LOCATION", "us-central1")
    model = os.getenv("VERTEX_MODEL", "gemini-1.5-flash")
    if not project_id:
        raise RuntimeError("GCP project ID is not configured")

    try:
        from google import genai
        from google.genai.types import HttpOptions

        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
            http_options=HttpOptions(api_version="v1"),
        )
        response = client.models.generate_content(model=model, contents=prompt)
        text = response.text or ""
    except Exception:
        import vertexai
        from vertexai.generative_models import GenerativeModel

        vertexai.init(project=project_id, location=location)
        response = GenerativeModel(model).generate_content(prompt)
        text = response.text or ""

    return parse_json_response(text)


def parse_json_response(text):
    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(0)
    return json.loads(cleaned)


def normalize_classification(raw):
    priority = str(raw.get("priority", "Low")).title()
    if priority not in {"High", "Medium", "Low"}:
        priority = "Low"

    score = int(raw.get("priority_score", 30))
    score = max(0, min(100, score))

    sdg = raw.get("sdg", "SDG 9")
    if sdg not in {"SDG 9", "SDG 16"}:
        sdg = "SDG 9"

    return {
        "category": str(raw.get("category", "General")),
        "priority": priority,
        "priority_score": score,
        "ai_reason": str(raw.get("ai_reason", "Classified using AI triage rules.")),
        "sdg": sdg,
        "escalation_required": bool(raw.get("escalation_required", False)),
    }


def fallback_classifier(title, description):
    text = f"{title} {description}".lower()
    escalation = any(keyword in text for keyword in HIGH_KEYWORDS)

    if escalation:
        priority = "High"
        score = 90
        reason = "Rule-based fallback detected urgent safety, security, or emergency keywords."
    elif any(keyword in text for keyword in MEDIUM_KEYWORDS):
        priority = "Medium"
        score = 60
        reason = "Rule-based fallback detected a service disruption or operational issue."
    elif any(keyword in text for keyword in LOW_KEYWORDS):
        priority = "Low"
        score = 25
        reason = "Rule-based fallback detected a general request, suggestion, or feedback item."
    else:
        priority = "Medium"
        score = 50
        reason = "Rule-based fallback assigned moderate priority due to insufficient severity signals."

    category = infer_category(text)
    return {
        "category": category,
        "priority": priority,
        "priority_score": score,
        "ai_reason": reason,
        "sdg": infer_sdg(text, category),
        "escalation_required": escalation,
    }


def infer_category(text):
    if any(word in text for word in ["fire", "accident", "medical", "unsafe", "danger"]):
        return "Safety"
    if any(word in text for word in ["harassment", "security", "violence", "threat"]):
        return "Security"
    if any(word in text for word in ["wifi", "network", "lab", "computer", "server", "electric", "fan"]):
        return "Infrastructure"
    if any(word in text for word in ["delay", "approval", "document", "certificate"]):
        return "Administration"
    return "General"


def infer_sdg(text, category):
    sdg16_terms = ["safety", "security", "harassment", "violence", "threat", "medical", "fire", "danger"]
    if category in {"Safety", "Security"} or any(term in text for term in sdg16_terms):
        return "SDG 16"
    return "SDG 9"
