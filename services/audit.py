import uuid
from models.audit_log import AuditLog


async def log_action(db, user_id, action: str, target_type: str = None, target_id=None, details: dict = None):
    """Log an action to the audit trail."""
    entry = AuditLog(
        id=uuid.uuid4(),
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details
    )
    db.add(entry)
