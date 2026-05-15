import os

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from services.firestore_service import create_user, get_user_by_email, utc_now_iso

load_dotenv()
USERS = [
    ("admin-demo", "Admin User", "admin@example.com", "ADMIN"),
    ("staff-demo", "Staff User", "staff@example.com", "STAFF"),
    ("student1-demo", "Student One", "student1@example.com", "STUDENT"),
    ("student2-demo", "Student Two", "student2@example.com", "STUDENT"),
]


def main():
    demo_password = os.getenv("DEMO_PASSWORD")
    if not demo_password:
        raise SystemExit("DEMO_PASSWORD must be set in backend/.env before seeding demo users.")
    now = utc_now_iso()
    for uid, name, email, role in USERS:
        if get_user_by_email(email):
            print(f"exists {email}")
            continue
        create_user(
            uid,
            {
                "uid": uid,
                "name": name,
                "email": email,
                "role": role,
                "isActive": True,
                "passwordHash": generate_password_hash(demo_password),
                "createdAt": now,
                "updatedAt": now,
            },
        )
        print(f"created {email} role={role}")


if __name__ == "__main__":
    main()
