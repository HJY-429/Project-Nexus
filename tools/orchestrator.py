"""
Pipeline Orchestrator for dynamic tool sequencing.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import uuid

from tools.base import ToolResult
from tools.base import TOOL_REGISTRY
from setting.db import SessionLocal


class PipelineOrchestrator:
    """
    Orchestrates tool execution into dynamic pipelines.
    
    Supports three main scenarios:
    1. Adding single document to existing topic
    2. Adding batch documents to existing topic  
    3. Creating new topic with batch documents
    """
    
    def __init__(self, session_factory=None):
        self.session_factory = session_factory or SessionLocal
        self.logger = logging.getLogger(__name__)
        
        # Define standard pipelines
        self.standard_pipelines = {
            "single_doc_existing_topic": ["DocumentETLTool", "GraphBuildTool"],
            "batch_doc_existing_topic": ["DocumentETLTool", "BlueprintGenerationTool", "GraphBuildTool"],
            "new_topic_batch": ["DocumentETLTool", "BlueprintGenerationTool", "GraphBuildTool"]
        }
    
    def execute_pipeline(self, pipeline_name: str, context: Dict[str, Any], execution_id: Optional[str] = None) -> ToolResult:
        """
        Execute a predefined pipeline.
        
        Args:
            pipeline_name: Name of the predefined pipeline
            context: Context data for pipeline execution
            execution_id: Optional execution ID for tracking
            
        Returns:
            ToolResult with pipeline execution results
        """
        execution_id = execution_id or str(uuid.uuid4())
        
        if pipeline_name not in self.standard_pipelines:
            return ToolResult(
                success=False,
                error_message=f"Pipeline '{pipeline_name}' not found"
            )
        
        tools = self.standard_pipelines[pipeline_name]
        return self.execute_custom_pipeline(tools, context, execution_id)
    
    def execute_custom_pipeline(self, tools: List[str], context: Dict[str, Any], execution_id: Optional[str] = None) -> ToolResult:
        """
        Execute a custom pipeline with specific tool sequence.
        
        Args:
            tools: List of tool names to execute in sequence
            context: Context data for pipeline execution
            execution_id: Optional execution ID for tracking
            
        Returns:
            ToolResult with pipeline execution results
        """
        execution_id = execution_id or str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        
        self.logger.info(f"Starting pipeline execution: {execution_id} - {tools}")
        
        results = {}
        pipeline_context = context.copy()
        
        try:
            for tool_name in tools:
                tool = TOOL_REGISTRY.get_tool(tool_name)
                if not tool:
                    return ToolResult(
                        success=False,
                        error_message=f"Tool '{tool_name}' not found"
                    )
                
                # Prepare input for this tool
                tool_input = self._prepare_tool_input(tool_name, pipeline_context, results)
                
                # Execute tool
                self.logger.info(f"Executing tool: {tool_name}")
                result = tool.execute_with_tracking(tool_input, f"{execution_id}_{tool_name}")
                
                if not result.success:
                    return ToolResult(
                        success=False,
                        error_message=f"Tool '{tool_name}' failed: {result.error_message}",
                        execution_id=execution_id,
                        data={"failed_tool": tool_name, "previous_results": results}
                    )
                
                results[tool_name] = result
                pipeline_context = self._update_context(tool_name, pipeline_context, result)
                
                self.logger.info(f"Tool completed: {tool_name}")
            
            # Calculate duration
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            self.logger.info(f"Pipeline execution completed: {execution_id} in {duration:.2f}s")
            
            return ToolResult(
                success=True,
                data={
                    "results": results,
                    "pipeline": tools,
                    "duration_seconds": duration
                },
                execution_id=execution_id,
                duration_seconds=duration
            )
            
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            self.logger.error(f"Pipeline execution failed: {execution_id} - {e}")
            
            return ToolResult(
                success=False,
                error_message=str(e),
                execution_id=execution_id,
                duration_seconds=duration
            )
    
    def select_default_pipeline(self, target_type: str, topic_name: str, file_count: int, is_new_topic: bool) -> str:
        """
        Select appropriate default pipeline based on context.
        
        Args:
            target_type: Target type (knowledge_graph, etc.)
            topic_name: Topic name
            file_count: Number of files to process
            is_new_topic: Whether this is a new topic
            
        Returns:
            Name of the default pipeline to use
        """
        if target_type != "knowledge_graph":
            return "single_doc_existing_topic"  # Default fallback
        
        if file_count == 1 and not is_new_topic:
            return "single_doc_existing_topic"
        elif file_count > 1 and not is_new_topic:
            return "batch_doc_existing_topic"
        else:  # New topic or single file for new topic
            return "new_topic_batch"
    
    def _prepare_tool_input(self, tool_name: str, context: Dict[str, Any], 
                           previous_results: Dict[str, ToolResult]) -> Dict[str, Any]:
        """Prepare input for a specific tool based on context and previous results."""
        
        if tool_name == "DocumentETLTool":
            return {
                "file_path": context.get("file_path"),
                "topic_name": context.get("topic_name"),
                "metadata": context.get("metadata", {}),
                "force_reprocess": context.get("force_reprocess", False),
                "link": context.get("link"),
                "original_filename": context.get("original_filename")
            }
        
        elif tool_name == "BlueprintGenerationTool":
            return {
                "topic_name": context.get("topic_name"),
                "source_data_ids": context.get("source_data_ids"),
                "force_regenerate": context.get("force_regenerate", False),
                "llm_client": context.get("llm_client"),
                "embedding_func": context.get("embedding_func")
            }
        
        elif tool_name == "GraphBuildTool":
            # Use results from previous tools
            if "DocumentETLTool" in previous_results:
                etl_result = previous_results["DocumentETLTool"]
                source_data_id = etl_result.data.get("source_data_id")
            else:
                source_data_id = context.get("source_data_id")
            
            if "BlueprintGenerationTool" in previous_results:
                blueprint_result = previous_results["BlueprintGenerationTool"]
                blueprint_id = blueprint_result.data.get("blueprint_id")
            else:
                blueprint_id = context.get("blueprint_id")
            
            return {
                "source_data_id": source_data_id,
                "blueprint_id": blueprint_id,
                "force_reprocess": context.get("force_reprocess", False),
                "llm_client": context.get("llm_client"),
                "embedding_func": context.get("embedding_func")
            }
        
        return context.copy()
    
    def _update_context(self, tool_name: str, context: Dict[str, Any], result: ToolResult) -> Dict[str, Any]:
        """Update context with results from a tool."""
        updated_context = context.copy()
        
        if tool_name == "DocumentETLTool" and result.success:
            updated_context["source_data_id"] = result.data.get("source_data_id")
            updated_context["topic_name"] = result.metadata.get("topic_name")
        
        elif tool_name == "BlueprintGenerationTool" and result.success:
            updated_context["blueprint_id"] = result.data.get("blueprint_id")
            updated_context["topic_name"] = result.metadata.get("topic_name")
        
        return updated_context
    
    def execute_scenario(self, scenario: str, context: Dict[str, Any], execution_id: Optional[str] = None) -> ToolResult:
        """
        Execute a specific scenario with appropriate pipeline.
        
        Args:
            scenario: One of 'single_doc_existing', 'batch_doc_existing', 'new_topic'
            context: Context data for the scenario
            execution_id: Optional execution ID
            
        Returns:
            ToolResult with scenario execution results
        """
        scenario_to_pipeline = {
            "single_doc_existing": "single_doc_existing_topic",
            "batch_doc_existing": "batch_doc_existing_topic", 
            "new_topic": "new_topic_batch"
        }
        
        if scenario not in scenario_to_pipeline:
            return ToolResult(
                success=False,
                error_message=f"Scenario '{scenario}' not supported"
            )
        
        return self.execute_pipeline(
            scenario_to_pipeline[scenario], 
            context, 
            execution_id
        )