"""
Integration Tests for Intent Orchestration Flow

Tests the complete end-to-end flow from intent submission
through processing, context management, and experience generation.
"""

import pytest
import asyncio
import httpx
from typing import Dict, Any, List
from datetime import datetime

from unison_spec.events import EventType, IntentEvent, ContextEvent, ExperienceEvent


class TestIntentOrchestrationFlow:
    """Test complete intent orchestration pipeline"""
    
    @pytest.mark.asyncio
    async def test_complete_intent_processing_flow(self, unison_stack, client):
        """
        Test the complete flow:
        1. Submit intent to orchestrator
        2. Intent graph processes and decomposes
        3. Context graph updates context
        4. Experience renderer generates interface
        5. Agent VDI can interact if needed
        """
        
        # Step 1: Submit intent to orchestrator
        intent_request = {
            "person_id": "test-user-001",
            "expression": "Schedule a team meeting for tomorrow at 2pm with the engineering team",
            "context": {
                "timezone": "UTC",
                "preferred_duration": "1hour",
                "current_location": "home_office"
            }
        }
        
        response = await client.post(
            "http://localhost:8090/intent/process",
            json=intent_request,
            timeout=30.0
        )
        assert response.status_code == 200
        
        intent_result = response.json()
        assert "intent_id" in intent_result
        assert "status" in intent_result
        
        intent_id = intent_result["intent_id"]
        assert intent_result["status"] in ["received", "processing"]
        
        # Step 2: Verify intent graph processing
        await asyncio.sleep(2)  # Allow processing time
        
        response = await client.get(
            f"http://localhost:8080/intent/status/{intent_id}",
            timeout=10.0
        )
        assert response.status_code == 200
        
        intent_status = response.json()
        assert intent_status["status"] in ["processing", "decomposed"]
        
        if intent_status["status"] == "decomposed":
            assert "goals" in intent_status
            assert len(intent_status["goals"]) > 0
            
            # Verify goal structure
            goal = intent_status["goals"][0]
            assert "goal_id" in goal
            assert "goal_type" in goal
            assert "priority" in goal
        
        # Step 3: Verify context graph updates
        response = await client.get(
            f"http://localhost:8091/context/current/test-user-001",
            timeout=10.0
        )
        assert response.status_code == 200
        
        context_result = response.json()
        assert "context_data" in context_result
        assert "last_updated" in context_result
        
        # Check if intent was recorded in context
        if "active_intents" in context_result["context_data"]:
            assert intent_id in context_result["context_data"]["active_intents"]
        
        # Step 4: Verify experience generation
        response = await client.get(
            f"http://localhost:8092/experience/status/{intent_id}",
            timeout=10.0
        )
        assert response.status_code == 200
        
        experience_result = response.json()
        assert "status" in experience_result
        assert experience_result["status"] in ["generating", "generated"]
        
        if experience_result["status"] == "generated":
            assert "experience_id" in experience_result
            assert "components" in experience_result
            assert len(experience_result["components"]) > 0
            
            # Verify experience components
            components = experience_result["components"]
            has_ui_component = any(
                comp.get("type") == "ui_interface" 
                for comp in components
            )
            assert has_ui_component, "Experience should include UI component"
        
        # Step 5: Verify final intent completion
        await asyncio.sleep(5)  # Allow full processing
        
        response = await client.get(
            f"http://localhost:8080/intent/status/{intent_id}",
            timeout=10.0
        )
        assert response.status_code == 200
        
        final_status = response.json()
        assert final_status["status"] == "completed"
        
        # Verify completion data
        if "completion_data" in final_status:
            completion = final_status["completion_data"]
            assert "completed_goals" in completion
            assert "generated_experiences" in completion
    
    @pytest.mark.asyncio
    async def test_context_updates_during_processing(self, unison_stack, client):
        """Test that context is properly updated during intent processing"""
        
        person_id = "test-user-context-001"
        
        # Initial context
        initial_context = {
            "user_preferences": {
                "meeting_duration": "30min",
                "notification_level": "normal"
            },
            "current_state": {
                "available": True,
                "focus_mode": False
            }
        }
        
        # Set initial context
        response = await client.post(
            f"http://localhost:8091/context/update/{person_id}",
            json={
                "context_type": "user",
                "context_data": initial_context,
                "merge_strategy": "replace"
            },
            timeout=10.0
        )
        assert response.status_code == 200
        
        # Submit intent
        intent_response = await client.post(
            "http://localhost:8090/intent/process",
            json={
                "person_id": person_id,
                "expression": "Start focus mode for 2 hours",
                "context": {}
            },
            timeout=30.0
        )
        assert intent_response.status_code == 200
        
        intent_id = intent_response.json()["intent_id"]
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Check context updates
        response = await client.get(
            f"http://localhost:8091/context/current/{person_id}",
            timeout=10.0
        )
        assert response.status_code == 200
        
        context_result = response.json()
        context_data = context_result["context_data"]
        
        # Verify context was updated
        assert "current_state" in context_data
        assert context_data["current_state"].get("focus_mode") is True
        
        # Verify intent tracking
        assert "active_intents" in context_data
        assert intent_id in context_data["active_intents"]
    
    @pytest.mark.asyncio
    async def test_experience_adaptation_based_on_context(self, unison_stack, client):
        """Test that experiences adapt based on user context"""
        
        person_id = "test-user-adapt-001"
        
        # Set up user context with accessibility preferences
        accessibility_context = {
            "accessibility": {
                "high_contrast": True,
                "font_size": "large",
                "screen_reader": True
            },
            "device_info": {
                "type": "mobile",
                "screen_size": "small"
            }
        }
        
        # Update context
        response = await client.post(
            f"http://localhost:8091/context/update/{person_id}",
            json={
                "context_type": "user",
                "context_data": accessibility_context
            },
            timeout=10.0
        )
        assert response.status_code == 200
        
        # Submit intent
        intent_response = await client.post(
            "http://localhost:8090/intent/process",
            json={
                "person_id": person_id,
                "expression": "Show me my calendar",
                "context": {}
            },
            timeout=30.0
        )
        assert intent_response.status_code == 200
        
        intent_id = intent_response.json()["intent_id"]
        
        # Wait for experience generation
        await asyncio.sleep(4)
        
        # Get generated experience
        response = await client.get(
            f"http://localhost:8092/experience/status/{intent_id}",
            timeout=10.0
        )
        assert response.status_code == 200
        
        experience_result = response.json()
        assert experience_result["status"] == "generated"
        
        # Verify adaptation
        components = experience_result["components"]
        ui_component = next(
            (comp for comp in components if comp.get("type") == "ui_interface"),
            None
        )
        
        assert ui_component is not None, "UI component should be generated"
        
        # Check accessibility adaptations
        ui_config = ui_component.get("config", {})
        assert ui_config.get("high_contrast") is True
        assert ui_config.get("font_size") == "large"
        assert ui_config.get("screen_reader_support") is True
        
        # Check mobile adaptations
        assert ui_config.get("responsive") is True
        assert "mobile_layout" in ui_config
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, unison_stack, client):
        """Test error handling in the orchestration flow"""
        
        # Submit malformed intent
        response = await client.post(
            "http://localhost:8090/intent/process",
            json={
                "person_id": "",  # Invalid empty person_id
                "expression": "",  # Invalid empty expression
                "context": {}
            },
            timeout=10.0
        )
        
        # Should return validation error
        assert response.status_code == 400
        error_data = response.json()
        assert "error" in error_data
        assert "validation_failed" in error_data["error"]["type"]
        
        # Submit intent with invalid context reference
        response = await client.post(
            "http://localhost:8090/intent/process",
            json={
                "person_id": "test-user-error-001",
                "expression": "Process this complex request",
                "context": {
                    "invalid_context": "should_not_exist"
                }
            },
            timeout=30.0
        )
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 500]
        
        if response.status_code == 200:
            intent_id = response.json()["intent_id"]
            
            # Check if error was recorded
            await asyncio.sleep(2)
            
            response = await client.get(
                f"http://localhost:8080/intent/status/{intent_id}",
                timeout=10.0
            )
            
            if response.status_code == 200:
                status = response.json()
                # Should either complete with warnings or fail gracefully
                assert status["status"] in ["completed", "failed", "degraded"]
    
    @pytest.mark.asyncio
    async def test_concurrent_intent_processing(self, unison_stack, client):
        """Test handling multiple concurrent intents"""
        
        person_id = "test-user-concurrent-001"
        
        # Submit multiple intents concurrently
        intents = [
            "Schedule a meeting with team A",
            "Send email to manager about project status",
            "Generate weekly report",
            "Book conference room for tomorrow",
            "Order lunch for team meeting"
        ]
        
        # Submit all intents concurrently
        tasks = []
        for i, expression in enumerate(intents):
            task = client.post(
                "http://localhost:8090/intent/process",
                json={
                    "person_id": f"{person_id}-{i}",
                    "expression": expression,
                    "context": {}
                },
                timeout=30.0
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed
        intent_ids = []
        for response in responses:
            assert isinstance(response, httpx.Response)
            assert response.status_code == 200
            intent_ids.append(response.json()["intent_id"])
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Check all intents were processed
        for intent_id in intent_ids:
            response = await client.get(
                f"http://localhost:8080/intent/status/{intent_id}",
                timeout=10.0
            )
            assert response.status_code == 200
            status = response.json()
            assert status["status"] in ["completed", "processing"]
    
    @pytest.mark.asyncio
    async def test_service_health_and_dependencies(self, unison_stack, client):
        """Test service health and dependency checking"""
        
        # Check orchestrator health
        response = await client.get("http://localhost:8090/health", timeout=10.0)
        assert response.status_code == 200
        orchestrator_health = response.json()
        assert orchestrator_health["status"] == "healthy"
        
        # Check intent graph health
        response = await client.get("http://localhost:8080/health", timeout=10.0)
        assert response.status_code == 200
        intent_graph_health = response.json()
        assert intent_graph_health["status"] == "healthy"
        
        # Check context graph health
        response = await client.get("http://localhost:8091/health", timeout=10.0)
        assert response.status_code == 200
        context_graph_health = response.json()
        assert context_graph_health["status"] == "healthy"
        
        # Check experience renderer health
        response = await client.get("http://localhost:8092/health", timeout=10.0)
        assert response.status_code == 200
        experience_health = response.json()
        assert experience_health["status"] == "healthy"
        
        # Verify dependency health in orchestrator
        dependencies = orchestrator_health.get("dependencies", {})
        assert "intent_graph" in dependencies
        assert "context_graph" in dependencies
        assert "experience_renderer" in dependencies
        
        # All dependencies should be healthy
        for dep_name, dep_status in dependencies.items():
            assert dep_status == "connected", f"Dependency {dep_name} should be connected"


@pytest.mark.asyncio
async def test_event_flow_between_services(unison_stack):
    """Test event flow and message passing between services"""
    
    # This test would require NATS/JetStream setup to test
    # actual event publishing and subscription
    
    # For now, we'll test the HTTP endpoints that would
    # be triggered by events
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test intent event processing
        intent_event = {
            "event_type": "intent.received",
            "source_service": "orchestrator",
            "person_id": "test-user-event-001",
            "expression": "Test event flow"
        }
        
        response = await client.post(
            "http://localhost:8080/events/intent",
            json=intent_event
        )
        assert response.status_code == 200
        
        # Test context event processing
        context_event = {
            "event_type": "context.updated",
            "source_service": "context-graph",
            "person_id": "test-user-event-001",
            "context_data": {"test": "data"}
        }
        
        response = await client.post(
            "http://localhost:8091/events/context",
            json=context_event
        )
        assert response.status_code == 200
        
        # Test experience event processing
        experience_event = {
            "event_type": "experience.generated",
            "source_service": "experience-renderer",
            "person_id": "test-user-event-001",
            "experience_data": {"type": "ui", "components": []}
        }
        
        response = await client.post(
            "http://localhost:8092/events/experience",
            json=experience_event
        )
        assert response.status_code == 200
