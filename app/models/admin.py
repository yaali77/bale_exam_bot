import enum
import uuid

from sqlalchemy import Column, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db_types import GUID
from app.database import Base


class AdminRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    SYSTEM_MANAGER = "system_manager"
    EXAM_MANAGER = "exam_manager"
    SCORE_OPERATOR = "score_operator"
    USER_OPERATOR = "user_operator"
    SUPPORT = "support"
    OBSERVER = "observer"


class Admin(Base):
    """کاربران پنل مدیریت با دسترسی‌های نقش‌محور (RBAC)"""
    __tablename__ = "admins"

    id = Column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4
    )

    username = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )

    full_name = Column(
        String(150),
        nullable=False
    )

    hashed_password = Column(
        String(255),
        nullable=False
    )

    role = Column(
        Enum(AdminRole),
        nullable=False,
        default=AdminRole.OBSERVER
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    last_login_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    # ============================================================
    # ORM RELATIONSHIPS
    # ============================================================

    recorded_results = relationship(
        "Result",
        foreign_keys="Result.recorded_by_admin_id",
        back_populates="recorded_by_admin",
    )

    published_results = relationship(
        "Result",
        foreign_keys="Result.published_by_admin_id",
        back_populates="published_by_admin",
    )

    result_histories = relationship(
        "ResultHistory",
        foreign_keys="ResultHistory.changed_by_admin_id",
        back_populates="changed_by_admin",
    )

    def __repr__(self):
        return f"<Admin {self.username} - {self.role}>"


# ================================================================
# ROLE PERMISSIONS
# ================================================================

ROLE_PERMISSIONS = {
    AdminRole.SUPER_ADMIN: {
        "view",
        "create",
        "edit",
        "delete",
        "publish",
        "report",
        "settings",
    },

    AdminRole.SYSTEM_MANAGER: {
        "view",
        "create",
        "edit",
        "delete",
        "publish",
        "report",
        "settings",
    },

    AdminRole.EXAM_MANAGER: {
        "view",
        "create",
        "edit",
        "publish",
        "report",
    },

    AdminRole.SCORE_OPERATOR: {
        "view",
        "create",
        "edit",
    },

    AdminRole.USER_OPERATOR: {
        "view",
        "create",
        "edit",
    },

    AdminRole.SUPPORT: {
        "view",
        "report",
    },

    AdminRole.OBSERVER: {
        "view",
    },
}


def has_permission(role: AdminRole, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
