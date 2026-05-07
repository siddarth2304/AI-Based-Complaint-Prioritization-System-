from datetime import datetime, timedelta, timezone


SLA_HOURS = {
    "High": 24,
    "Medium": 72,
    "Low": 24 * 7,
}


def calculate_sla_deadline(priority):
    hours = SLA_HOURS.get(priority, 72)
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
