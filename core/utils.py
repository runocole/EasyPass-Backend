from .models import SystemLog

def log_event(user,action,description=None, severity="info",ip_address=None):
   
   SystemLog.objects.create(
    user=user,
    action=action,
    description=description,
    severity=severity,
    ip_address=ip_address
)
