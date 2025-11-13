# models

from dataclasses import dataclass, field

from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class JobState(Enum):
    
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"

    FAILED = "failed"
    DEAD = "dead"


@dataclass
class Job:
    # job structure
    jid: str
    command: str
    state: JobState = JobState.PENDING

    attempts: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)

    updated_at: datetime = field(default_factory=datetime.now)

    output: Optional[str] = None
    error: Optional[str] = None
    exit_code: Optional[int] = None
    next_retry_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Job':
        
        return cls(
            jid=data['id'],  # Database uses 'id', Python uses 'jid'
            command=data['command'],
            state=JobState(data.get('state', 'pending')),

            attempts=data.get('attempts', 0),
            max_retries=data.get('max_retries', 3),

            created_at=datetime.fromisoformat(data['created_at']) if isinstance(data.get('created_at'), str) else data.get('created_at', datetime.now()),
            updated_at=datetime.fromisoformat(data['updated_at']) if isinstance(data.get('updated_at'), str) else data.get('updated_at', datetime.now()),
            output=data.get('output'),

            error=data.get('error'),

            exit_code=data.get('exit_code'),
            next_retry_at=datetime.fromisoformat(data['next_retry_at']) if data.get('next_retry_at') and isinstance(data['next_retry_at'], str) else data.get('next_retry_at')
        )
    
    def to_dict(self) -> dict:
        
        return {
            'id': self.jid,  # Database uses 'id', Python uses 'jid'
            'command': self.command,

            'state': self.state.value,
            'attempts': self.attempts,
            'max_retries': self.max_retries,

            'created_at': self.created_at.isoformat(),

            'updated_at': self.updated_at.isoformat(),
            'output': self.output,
            'error': self.error,
            'exit_code': self.exit_code,

            'next_retry_at': self.next_retry_at.isoformat() if self.next_retry_at else None
        }
    
    @staticmethod
    def generate_jid() -> str:
        
        return str(uuid.uuid4())[:8]
