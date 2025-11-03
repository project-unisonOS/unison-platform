"""
Unison Event Specifications

Defines the universal event schema and event types that all
Unison services must use for communication.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
import uuid


class EventType(str, Enum):
    """Standardized event types across all Unison services"""
    
    # Intent Processing Events
    INTENT_RECEIVED = "intent.received"
    INTENT_PROCESSED = "intent.processed"
    INTENT_DECOMPOSED = "intent.decomposed"
    INTENT_FAILED = "intent.failed"
    
    # Context Management Events
    CONTEXT_UPDATED = "context.updated"
    CONTEXT_QUERY = "context.query"
    CONTEXT_RESPONSE = "context.response"
    CONTEXT_MERGED = "context.merged"
    
    # Goal Management Events
    GOAL_CREATED = "goal.created"
    GOAL_UPDATED = "goal.updated"
    GOAL_COMPLETED = "goal.completed"
    GOAL_FAILED = "goal.failed"
    GOAL_CANCELLED = "goal.cancelled"
    
    # Experience Management Events
    EXPERIENCE_GENERATED = "experience.generated"
    EXPERIENCE_ADAPTED = "experience.adapted"
    EXPERIENCE_INTERACTION = "experience.interaction"
    EXPERIENCE_RENDERED = "experience.rendered"
    
    # Agent VDI Events
    VDI_SESSION_CREATED = "vdi.session.created"
    VDI_SESSION_DESTROYED = "vdi.session.destroyed"
    VDI_DISPLAY_UPDATED = "vdi.display.updated"
    VDI_INTERACTION = "vdi.interaction"
    
    # I/O Events
    SPEECH_PROCESSED = "speech.processed"
    VISION_PROCESSED = "vision.processed"
    IO_REQUEST = "io.request"
    IO_RESPONSE = "io.response"
    
    # Inference Events
    INFERENCE_REQUEST = "inference.request"
    INFERENCE_RESPONSE = "inference.response"
    INFERENCE_COMPLETED = "inference.completed"
    INFERENCE_FAILED = "inference.failed"
    
    # System Events
    SERVICE_HEALTH = "service.health"
    SERVICE_METRICS = "service.metrics"
    SERVICE_STARTED = "service.started"
    SERVICE_STOPPED = "service.stopped"
    SYSTEM_ALERT = "system.alert"
    SYSTEM_ERROR = "system.error"


class EventPriority(str, Enum):
    """Event priority levels for routing and processing"""
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
    URGENT = "urgent"


class EventEnvelope(BaseModel):
    """
    Universal event envelope for all Unison service communication.
    
    This schema ensures consistent event structure across the platform
    and provides metadata for routing, tracing, and processing.
    """
    
    # Event Identification
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique event identifier"
    )
    event_type: EventType = Field(
        ...,
        description="Type of event"
    )
    event_version: str = Field(
        default="1.0",
        description="Event schema version"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Event creation timestamp"
    )
    
    # Source Information
    source_service: str = Field(
        ...,
        description="Service that generated the event"
    )
    source_instance: str = Field(
        default="default",
        description="Instance identifier of the source service"
    )
    correlation_id: Optional[str] = Field(
        default=None,
        description="Request correlation ID for tracing"
    )
    causation_id: Optional[str] = Field(
        default=None,
        description="ID of the event that caused this event"
    )
    
    # Routing and Processing
    topic: str = Field(
        ...,
        description="NATS topic for event routing"
    )
    reply_to: Optional[str] = Field(
        default=None,
        description="Reply topic for request/response patterns"
    )
    priority: EventPriority = Field(
        default=EventPriority.NORMAL,
        description="Event processing priority"
    )
    ttl: Optional[int] = Field(
        default=None,
        description="Time to live in seconds"
    )
    
    # Event Data
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Event payload data"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event metadata"
    )
    
    # Security and Compliance
    auth_token: Optional[str] = Field(
        default=None,
        description="Authentication token for secure events"
    )
    encrypted_fields: List[str] = Field(
        default_factory=list,
        description="List of encrypted field names"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        use_enum_values = True
        
    @validator('correlation_id')
    def generate_correlation_id_if_missing(cls, v):
        """Generate correlation ID if not provided"""
        if v is None:
            return str(uuid.uuid4())
        return v
    
    @validator('topic')
    def validate_topic_format(cls, v, values):
        """Validate topic format based on event type"""
        event_type = values.get('event_type')
        if event_type:
            # Map event types to standard topics
            topic_mapping = {
                EventType.INTENT_RECEIVED: "unison.intent.received",
                EventType.INTENT_PROCESSED: "unison.intent.processed",
                EventType.INTENT_DECOMPOSED: "unison.intent.decomposed",
                EventType.INTENT_FAILED: "unison.intent.failed",
                
                EventType.CONTEXT_UPDATED: "unison.context.updated",
                EventType.CONTEXT_QUERY: "unison.context.query",
                EventType.CONTEXT_RESPONSE: "unison.context.response",
                
                EventType.GOAL_CREATED: "unison.goal.created",
                EventType.GOAL_UPDATED: "unison.goal.updated",
                EventType.GOAL_COMPLETED: "unison.goal.completed",
                EventType.GOAL_FAILED: "unison.goal.failed",
                
                EventType.EXPERIENCE_GENERATED: "unison.experience.generated",
                EventType.EXPERIENCE_ADAPTED: "unison.experience.adapted",
                EventType.EXPERIENCE_INTERACTION: "unison.experience.interaction",
                
                EventType.SERVICE_HEALTH: "unison.service.health",
                EventType.SERVICE_METRICS: "unison.service.metrics",
                EventType.SYSTEM_ALERT: "unison.system.alert",
            }
            
            if event_type in topic_mapping and v == "auto":
                return topic_mapping[event_type]
        
        return v
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the event"""
        self.metadata[key] = value
    
    def add_data(self, key: str, value: Any) -> None:
        """Add data to the event payload"""
        self.data[key] = value
    
    def is_expired(self) -> bool:
        """Check if event has expired based on TTL"""
        if self.ttl is None:
            return False
        
        elapsed = (datetime.utcnow() - self.timestamp).total_seconds()
        return elapsed > self.ttl
    
    def to_routing_key(self) -> str:
        """Generate routing key for message brokers"""
        return f"{self.source_service}.{self.event_type.value}"
    
    def trace_context(self) -> Dict[str, str]:
        """Extract tracing context for distributed tracing"""
        return {
            "event_id": self.event_id,
            "correlation_id": self.correlation_id or self.event_id,
            "causation_id": self.causation_id or "",
            "source_service": self.source_service,
            "source_instance": self.source_instance,
        }


class IntentEvent(EventEnvelope):
    """Specialized event for intent-related operations"""
    
    def __init__(self, **data):
        if 'event_type' not in data:
            data['event_type'] = EventType.INTENT_RECEIVED
        if 'topic' not in data:
            data['topic'] = "auto"
        super().__init__(**data)
    
    person_id: str = Field(
        ...,
        description="ID of the person submitting the intent"
    )
    expression: str = Field(
        ...,
        description="Natural language expression of the intent"
    )
    intent_type: Optional[str] = Field(
        default=None,
        description="Classification of the intent type"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score of intent classification"
    )


class ContextEvent(EventEnvelope):
    """Specialized event for context-related operations"""
    
    def __init__(self, **data):
        if 'event_type' not in data:
            data['event_type'] = EventType.CONTEXT_UPDATED
        if 'topic' not in data:
            data['topic'] = "auto"
        super().__init__(**data)
    
    person_id: str = Field(
        ...,
        description="ID of the person the context belongs to"
    )
    context_type: str = Field(
        ...,
        description="Type of context (user, session, environment)"
    )
    context_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Actual context data"
    )
    merge_strategy: str = Field(
        default="merge",
        description="Strategy for merging context data"
    )


class ExperienceEvent(EventEnvelope):
    """Specialized event for experience-related operations"""
    
    def __init__(self, **data):
        if 'event_type' not in data:
            data['event_type'] = EventType.EXPERIENCE_GENERATED
        if 'topic' not in data:
            data['topic'] = "auto"
        super().__init__(**data)
    
    experience_id: str = Field(
        ...,
        description="Unique identifier for the experience"
    )
    person_id: str = Field(
        ...,
        description="ID of the person the experience is for"
    )
    experience_type: str = Field(
        ...,
        description="Type of experience (ui, voice, ar, etc.)"
    )
    components: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of experience components"
    )
    adaptation_rules: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Rules for experience adaptation"
    )


class GoalEvent(EventEnvelope):
    """Specialized event for goal-related operations"""
    
    def __init__(self, **data):
        if 'event_type' not in data:
            data['event_type'] = EventType.GOAL_CREATED
        if 'topic' not in data:
            data['topic'] = "auto"
        super().__init__(**data)
    
    goal_id: str = Field(
        ...,
        description="Unique identifier for the goal"
    )
    person_id: str = Field(
        ...,
        description="ID of the person the goal belongs to"
    )
    goal_type: str = Field(
        ...,
        description="Type of goal"
    )
    goal_state: str = Field(
        default="pending",
        description="Current state of the goal"
    )
    priority: str = Field(
        default="normal",
        description="Goal priority level"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of goal dependencies"
    )
    
    @validator('goal_state')
    def validate_goal_state(cls, v):
        allowed_states = ['pending', 'active', 'completed', 'failed', 'cancelled']
        if v not in allowed_states:
            raise ValueError(f"Goal state must be one of: {allowed_states}")
        return v
