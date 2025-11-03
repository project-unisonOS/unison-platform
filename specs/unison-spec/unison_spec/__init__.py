"""
Unison Specification Package

Shared contracts, schemas, and interfaces for all Unison services.
This package ensures consistency across the platform and provides
hard interfaces that all services must implement.

Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Unison Platform Team"
__email__ = "team@project-unisonos.org"

# Core exports
from .events import EventEnvelope, EventType
from .contracts import ServiceContract, HealthResponse
from .config import UnisonConfig
from .exceptions import UnisonError, ContractError

# Domain-specific exports
from .domains import (
    IntentEvent,
    ContextEvent,
    ExperienceEvent,
    GoalEvent,
)

# Utility exports
from .utils import (
    create_correlation_id,
    validate_event_schema,
    get_service_info,
)

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    
    # Core components
    "EventEnvelope",
    "EventType", 
    "ServiceContract",
    "HealthResponse",
    "UnisonConfig",
    
    # Exceptions
    "UnisonError",
    "ContractError",
    
    # Domain events
    "IntentEvent",
    "ContextEvent", 
    "ExperienceEvent",
    "GoalEvent",
    
    # Utilities
    "create_correlation_id",
    "validate_event_schema",
    "get_service_info",
]
