"""
Unison Service Contracts

Defines the hard interfaces that all Unison services must implement.
These contracts ensure consistency and reliability across the platform.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from pydantic import BaseModel, Field
from .events import EventEnvelope


class HealthStatus(str):
    """Health status enumeration"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    STARTING = "starting"
    STOPPING = "stopping"


class HealthResponse(BaseModel):
    """Standard health check response"""
    
    status: str = Field(
        ...,
        description="Service health status"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Health check timestamp"
    )
    service: str = Field(
        ...,
        description="Service name"
    )
    version: str = Field(
        ...,
        description="Service version"
    )
    instance: str = Field(
        default="default",
        description="Service instance ID"
    )
    uptime_seconds: float = Field(
        default=0.0,
        description="Service uptime in seconds"
    )
    dependencies: Dict[str, str] = Field(
        default_factory=dict,
        description="Status of service dependencies"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional health metadata"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ServiceInfo(BaseModel):
    """Service metadata and capabilities"""
    
    name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    description: str = Field(..., description="Service description")
    domain: str = Field(..., description="Service domain")
    capabilities: List[str] = Field(
        default_factory=list,
        description="List of service capabilities"
    )
    endpoints: List[str] = Field(
        default_factory=list,
        description="List of service endpoints"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of service dependencies"
    )
    supported_events: List[str] = Field(
        default_factory=list,
        description="List of supported event types"
    )
    configuration: Dict[str, Any] = Field(
        default_factory=dict,
        description="Service configuration schema"
    )


class ServiceMetrics(BaseModel):
    """Service performance metrics"""
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Metrics timestamp"
    )
    request_count: int = Field(
        default=0,
        description="Total request count"
    )
    error_count: int = Field(
        default=0,
        description="Total error count"
    )
    average_response_time: float = Field(
        default=0.0,
        description="Average response time in milliseconds"
    )
    memory_usage_mb: float = Field(
        default=0.0,
        description="Memory usage in MB"
    )
    cpu_usage_percent: float = Field(
        default=0.0,
        description="CPU usage percentage"
    )
    active_connections: int = Field(
        default=0,
        description="Number of active connections"
    )
    queue_depth: int = Field(
        default=0,
        description="Message queue depth"
    )


class ServiceContract(ABC):
    """
    Base contract that all Unison services must implement.
    
    This contract defines the minimal interface that every service
    must provide to ensure platform consistency and reliability.
    """
    
    @abstractmethod
    async def health(self) -> HealthResponse:
        """
        Return the current health status of the service.
        
        Returns:
            HealthResponse: Current health status including
                          service status, dependencies, and metadata
        """
        pass
    
    @abstractmethod
    async def handle_event(self, envelope: EventEnvelope) -> Optional[EventEnvelope]:
        """
        Handle incoming events from other services.
        
        Args:
            envelope: The event envelope to process
            
        Returns:
            Optional[EventEnvelope]: Response event if applicable,
                                   None if no response needed
        """
        pass
    
    @abstractmethod
    def get_service_info(self) -> ServiceInfo:
        """
        Return service metadata and capabilities.
        
        Returns:
            ServiceInfo: Service information including capabilities,
                        endpoints, and dependencies
        """
        pass
    
    @abstractmethod
    async def get_metrics(self) -> ServiceMetrics:
        """
        Return current service performance metrics.
        
        Returns:
            ServiceMetrics: Current performance metrics
        """
        pass
    
    @abstractmethod
    async def start(self) -> None:
        """
        Start the service and initialize all components.
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """
        Stop the service and cleanup resources.
        """
        pass
    
    @abstractmethod
    async def validate_configuration(self) -> bool:
        """
        Validate service configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        pass


class IntentProcessingContract(ABC):
    """
    Contract for intent processing services.
    
    Services that process user intents must implement this contract
    to ensure consistent intent handling across the platform.
    """
    
    @abstractmethod
    async def process_intent(
        self,
        person_id: str,
        expression: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user intent expression.
        
        Args:
            person_id: ID of the person submitting the intent
            expression: Natural language expression of the intent
            context: Optional context information
            
        Returns:
            Dict containing processed intent information
        """
        pass
    
    @abstractmethod
    async def decompose_intent(
        self,
        intent_id: str
    ) -> List[Dict[str, Any]]:
        """
        Decompose an intent into actionable goals.
        
        Args:
            intent_id: ID of the intent to decompose
            
        Returns:
            List of goals derived from the intent
        """
        pass
    
    @abstractmethod
    async def get_intent_status(
        self,
        intent_id: str
    ) -> Dict[str, Any]:
        """
        Get the current status of an intent.
        
        Args:
            intent_id: ID of the intent
            
        Returns:
            Current intent status and progress
        """
        pass


class ContextManagementContract(ABC):
    """
    Contract for context management services.
    
    Services that manage user or system context must implement
    this contract to ensure consistent context operations.
    """
    
    @abstractmethod
    async def update_context(
        self,
        person_id: str,
        context_type: str,
        context_data: Dict[str, Any],
        merge_strategy: str = "merge"
    ) -> Dict[str, Any]:
        """
        Update context for a person or system.
        
        Args:
            person_id: ID of the person
            context_type: Type of context (user, session, environment)
            context_data: Context data to update
            merge_strategy: Strategy for merging context data
            
        Returns:
            Updated context information
        """
        pass
    
    @abstractmethod
    async def get_context(
        self,
        person_id: str,
        context_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve context for a person or system.
        
        Args:
            person_id: ID of the person
            context_type: Optional specific context type
            
        Returns:
            Context data
        """
        pass
    
    @abstractmethod
    async def query_context(
        self,
        query: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query context data based on criteria.
        
        Args:
            query: Query parameters
            filters: Optional filters
            
        Returns:
            List of matching context records
        """
        pass


class ExperienceGenerationContract(ABC):
    """
    Contract for experience generation services.
    
    Services that generate user experiences must implement this
    contract to ensure consistent experience creation.
    """
    
    @abstractmethod
    async def generate_experience(
        self,
        person_id: str,
        intent_data: Dict[str, Any],
        context_data: Dict[str, Any],
        experience_type: str = "ui"
    ) -> Dict[str, Any]:
        """
        Generate a user experience based on intent and context.
        
        Args:
            person_id: ID of the person
            intent_data: Processed intent information
            context_data: User context information
            experience_type: Type of experience to generate
            
        Returns:
            Generated experience data
        """
        pass
    
    @abstractmethod
    async def adapt_experience(
        self,
        experience_id: str,
        adaptation_triggers: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Adapt an existing experience based on triggers.
        
        Args:
            experience_id: ID of the experience to adapt
            adaptation_triggers: Triggers for adaptation
            
        Returns:
            Adapted experience data
        """
        pass
    
    @abstractmethod
    async def get_experience_status(
        self,
        experience_id: str
    ) -> Dict[str, Any]:
        """
        Get the current status of an experience.
        
        Args:
            experience_id: ID of the experience
            
        Returns:
            Current experience status
        """
        pass


class AgentVDIContract(ABC):
    """
    Contract for Agent VDI services.
    
    Services that provide virtual display interfaces must implement
    this contract to ensure consistent VDI operations.
    """
    
    @abstractmethod
    async def create_virtual_display(
        self,
        session_id: str,
        display_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a virtual display session.
        
        Args:
            session_id: Unique session identifier
            display_config: Display configuration
            
        Returns:
            Virtual display session information
        """
        pass
    
    @abstractmethod
    async def interact_with_display(
        self,
        session_id: str,
        interaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Interact with a virtual display.
        
        Args:
            session_id: Session identifier
            interaction_data: Interaction parameters
            
        Returns:
            Interaction results
        """
        pass
    
    @abstractmethod
    async def capture_display_state(
        self,
        session_id: str,
        capture_format: str = "screenshot"
    ) -> Dict[str, Any]:
        """
        Capture the current state of a virtual display.
        
        Args:
            session_id: Session identifier
            capture_format: Format for capture (screenshot, dom, etc.)
            
        Returns:
            Captured display state
        """
        pass


class InferenceContract(ABC):
    """
    Contract for inference services.
    
    Services that provide ML inference capabilities must implement
    this contract to ensure consistent inference operations.
    """
    
    @abstractmethod
    async def run_inference(
        self,
        model_name: str,
        input_data: Dict[str, Any],
        inference_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run inference on a specific model.
        
        Args:
            model_name: Name of the model to use
            input_data: Input data for inference
            inference_config: Optional inference configuration
            
        Returns:
            Inference results
        """
        pass
    
    @abstractmethod
    async def list_available_models(self) -> List[Dict[str, Any]]:
        """
        List all available inference models.
        
        Returns:
            List of available models with metadata
        """
        pass
    
    @abstractmethod
    async def get_model_info(
        self,
        model_name: str
    ) -> Dict[str, Any]:
        """
        Get information about a specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Model information and capabilities
        """
        pass
