from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from ..database import Base

class SecurityAuditLog(Base):
    """Audit log entry recording security and data-governance events."""
    __tablename__ = "security_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    action = Column(String(64), nullable=False, index=True)
    status = Column(String(32), default="SUCCESS", nullable=False)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(256), nullable=True)
    details = Column(Text, nullable=True) # JSON or formatted description
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="audit_logs")
