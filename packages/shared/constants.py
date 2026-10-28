from enum import Enum

class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class EmailStatus(str, Enum):
    PENDING = "PENDING"
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    BOUNCED = "BOUNCED"
    INACTIVE = "INACTIVE"

class DispatchChannel(str, Enum):
    FAKE_SMTP = "FAKE_SMTP"
    APPS_SCRIPT_RELAY = "APPS_SCRIPT_RELAY"
    DIRECT_SMTP = "DIRECT_SMTP"
