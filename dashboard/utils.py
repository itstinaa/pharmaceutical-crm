from .models import AuditLog

# Utility Function: Create Audit Log Entry
def create_audit_log(user, action, model_name, record_id, description, old_values=None, new_values=None):

    # Create a new audit log record in the database
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        record_id=record_id,
        description=description,
        old_values=old_values,
        new_values=new_values
    )