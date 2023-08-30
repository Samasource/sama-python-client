from enum import Enum

class TaskStates(Enum):
    NEW = "new"
    IN_PROGRESS = "in progress"
    COMPLETED = "completed"
    APPROVED = "approved"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"