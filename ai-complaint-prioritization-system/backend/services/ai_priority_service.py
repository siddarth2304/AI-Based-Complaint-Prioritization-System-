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


def classify_complaint(title, description, image_base64=None):
    prompt = build_gemini_prompt(title, description)
    try:
        result = classify_with_vertex_ai(prompt, image_base64)
        return normalize_classification(result)
    except Exception:
        return fallback_classifier(title, description)


def generate_resolution_sop(title, description, category):
    prompt = build_sop_prompt(title, description, category)
    try:
        project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GCP_LOCATION", "us-central1")
        model = os.getenv("VERTEX_MODEL", "gemini-1.5-flash")
        
        if not project_id:
            raise RuntimeError("GCP project ID is not configured")
            
        try:
            from google import genai
            from google.genai.types import HttpOptions
            client = genai.Client(vertexai=True, project=project_id, location=location, http_options=HttpOptions(api_version="v1"))
            response = client.models.generate_content(model=model, contents=prompt)
            return response.text or "No solution generated."
        except Exception:
            import vertexai
            from vertexai.generative_models import GenerativeModel
            vertexai.init(project=project_id, location=location)
            response = GenerativeModel(model).generate_content(prompt)
            return response.text or "No solution generated."
    except Exception as e:
        # Fallback for local testing without GCP credentials
        return fallback_solution_generator(title, category)

def fallback_solution_generator(title, category):
    title_lower = title.lower()
    if category == "Safety" or "fire" in title_lower or "danger" in title_lower:
        return "### 🚨 Emergency Safety Protocol\n1. **Evacuate the immediate area** and ensure all personnel are at a safe distance.\n2. **Contact Campus Security/Emergency Services** immediately and report the situation.\n3. **Isolate the hazard** (e.g., cut off power, close doors) only if safe to do so.\n\n*Prevention:* Conduct a comprehensive safety audit of the affected zone."
    elif category == "Infrastructure" or "wifi" in title_lower or "network" in title_lower:
        return "### 💻 IT Network Troubleshooting\n1. **Verify the outage** by checking the network monitoring dashboard for the specific zone.\n2. **Restart the local network switch/router** servicing the affected area.\n3. **Dispatch an IT technician** to physically inspect the hardware if remote restart fails.\n\n*Prevention:* Upgrade firmware on all access points during the next maintenance window."
    elif category == "Infrastructure" or "fan" in title_lower or "electric" in title_lower or "water" in title_lower:
        return "### 🔧 Facilities Maintenance Plan\n1. **Send a maintenance technician** to inspect the reported equipment/area.\n2. **Secure the area** if there is an electrical or slipping hazard.\n3. **Repair or replace** the faulty component and log the action in the inventory system.\n\n*Prevention:* Schedule routine preventative maintenance for this equipment class."
    else:
        return "### 📋 General Resolution SOP\n1. **Review the complaint details** and contact the submitter for any necessary clarifications.\n2. **Assign the ticket** to the relevant department lead for assessment.\n3. **Implement the fix** and update the status to 'Resolved' once confirmed.\n\n*Prevention:* Monitor similar complaints to identify systemic issues."


def build_gemini_prompt(title, description):
    return f"""
You are an AI complaint triage engine for a cloud-based university/organization helpdesk.
Classify the complaint urgency using its title and description.

Return only valid JSON with exactly these keys:
category, priority, priority_score, ai_reason, sdg, escalation_required, assigned_department

Rules:
- priority must be one of High, Medium, Low.
- priority_score must be an integer from 0 to 100.
- sdg must be either "SDG 9" for infrastructure, systems, connectivity, lab equipment, electricity, transport, or innovation issues, or "SDG 16" for safety, justice, harassment, security, governance, rights, or institutional trust issues.
- escalation_required must be true when the complaint includes serious risk words or direct safety/security concerns.
- ai_reason must be concise and explain the urgency decision.
- assigned_department must be a short name predicting the department responsible for handling the issue (e.g., "IT Support", "Facilities", "Security", "Hostel").

Examples:
- "Fire in lab" with smoke/fire risk => {{"category":"Safety","priority":"High","priority_score":95,"ai_reason":"The complaint indicates immediate safety risk due to smoke or fire.","sdg":"SDG 16","escalation_required":true,"assigned_department":"Security & Emergency"}}
- "WiFi slow in hostel" => {{"category":"Infrastructure","priority":"Medium","priority_score":58,"ai_reason":"Connectivity is degraded and affects productivity, but no immediate safety threat is present.","sdg":"SDG 9","escalation_required":false,"assigned_department":"IT Support"}}
- "Fan not working in classroom" => Low or Medium depending severity and duration.
- "Harassment/security issue" => High with escalation_required true.
- "General suggestion for library seating" => Low.

Complaint title: {title}
Complaint description: {description}
"""

def build_sop_prompt(title, description, category):
    return f"""
You are an expert Facility Management and IT Support AI Co-Pilot.
An administrator has requested a Standard Operating Procedure (SOP) to resolve the following issue:

Category: {category}
Title: {title}
Description: {description}

Provide a concise, highly actionable 3-step resolution plan. Use markdown formatting.
Do not include any greetings or fluff. Just the steps and a brief concluding recommendation for prevention.
"""


def classify_with_vertex_ai(prompt, image_base64=None):
    project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GCP_LOCATION", "us-central1")
    model = os.getenv("VERTEX_MODEL", "gemini-1.5-flash")
    if not project_id:
        raise RuntimeError("GCP project ID is not configured")

    try:
        from google import genai
        from google.genai.types import HttpOptions, Part

        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
            http_options=HttpOptions(api_version="v1"),
        )
        
        contents = [prompt]
        if image_base64:
            import base64
            try:
                mime_type = "image/jpeg"
                if "data:" in image_base64 and ";base64," in image_base64:
                    mime_type = image_base64.split(";base64,")[0].replace("data:", "")
                    image_base64 = image_base64.split(";base64,")[1]
                data = base64.b64decode(image_base64)
                contents.append(Part.from_bytes(data=data, mime_type=mime_type))
            except Exception as e:
                print(f"Error processing image for genai: {e}")

        response = client.models.generate_content(model=model, contents=contents)
        text = response.text or ""
    except Exception:
        import vertexai
        from vertexai.generative_models import GenerativeModel, Part

        vertexai.init(project=project_id, location=location)
        
        contents = [prompt]
        if image_base64:
            import base64
            try:
                mime_type = "image/jpeg"
                if "data:" in image_base64 and ";base64," in image_base64:
                    mime_type = image_base64.split(";base64,")[0].replace("data:", "")
                    image_base64 = image_base64.split(";base64,")[1]
                data = base64.b64decode(image_base64)
                contents.append(Part.from_data(data=data, mime_type=mime_type))
            except Exception as e:
                print(f"Error processing image for vertexai: {e}")

        response = GenerativeModel(model).generate_content(contents)
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
        "assigned_department": str(raw.get("assigned_department", "General Services")),
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
        "assigned_department": infer_department(text, category),
    }

def infer_department(text, category):
    if category == "Safety" or category == "Security":
        return "Security & Emergency"
    if "wifi" in text or "network" in text or "computer" in text or "server" in text:
        return "IT Support"
    if "lab" in text or "electric" in text or "fan" in text or "water" in text:
        return "Facilities Maintenance"
    if "hostel" in text or "room" in text or "mess" in text:
        return "Hostel Management"
    return "General Services"


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
