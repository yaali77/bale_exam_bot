"""
اجرای یک‌باره برای ساخت اولین حساب Super Admin.
استفاده:
    docker compose exec backend python scripts/create_super_admin.py
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, Base, engine
from app.models.admin import Admin, AdminRole
from app.core.security import hash_password


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        username = input("نام کاربری Super Admin: ").strip()
        if db.query(Admin).filter(Admin.username == username).first():
            print("این نام کاربری قبلاً وجود دارد.")
            return

        full_name = input("نام و نام خانوادگی: ").strip()
        password = input("رمز عبور: ").strip()

        admin = Admin(
            username=username,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=AdminRole.SUPER_ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"✅ حساب Super Admin '{username}' با موفقیت ساخته شد.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
