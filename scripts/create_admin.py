from getpass import getpass
from app.database import SessionLocal
from app.models.admin import Admin, AdminRole
from app.core.security import hash_password

username = input("Admin username: ").strip()
full_name = input("Admin full name: ").strip()
password = getpass("Admin password: ")
password2 = getpass("Confirm password: ")

if not username or not full_name or not password:
    raise SystemExit("Username, full name and password are required.")

if password != password2:
    raise SystemExit("Passwords do not match.")

db = SessionLocal()

try:
    existing = db.query(Admin).filter(Admin.username == username).first()

    if existing:
        raise SystemExit(f"Admin '{username}' already exists.")

    admin = Admin(
        username=username,
        full_name=full_name,
        hashed_password=hash_password(password),
        role=AdminRole.SUPER_ADMIN,
        is_active=True,
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    print()
    print("===================================")
    print("ADMIN CREATED SUCCESSFULLY")
    print("===================================")
    print("Username:", admin.username)
    print("Full name:", admin.full_name)
    print("Role:", admin.role.value)
    print("Active:", admin.is_active)
    print("===================================")

except Exception:
    db.rollback()
    raise

finally:
    db.close()
