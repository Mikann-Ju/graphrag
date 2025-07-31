# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""MCP (Model Context Protocol) tool calling client for GraphRAG."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Protocol, Union
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class MCPToolParameter:
    """MCP tool parameter definition."""
    name: str
    type: str
    description: str
    required: bool = False
    enum: Optional[List[str]] = None
    default: Optional[Any] = None


@dataclass
class MCPTool:
    """MCP tool definition."""
    name: str
    description: str
    parameters: List[MCPToolParameter]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": {
                    param.name: {
                        "type": param.type,
                        "description": param.description,
                        **({"enum": param.enum} if param.enum else {}),
                        **({"default": param.default} if param.default is not None else {})
                    }
                    for param in self.parameters
                },
                "required": [param.name for param in self.parameters if param.required]
            }
        }


@dataclass
class MCPToolCall:
    """MCP tool call request."""
    tool_name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None


@dataclass
class MCPToolResult:
    """MCP tool call result."""
    call_id: Optional[str]
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MCPToolHandler(ABC):
    """Abstract base class for MCP tool handlers."""
    
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> MCPToolResult:
        """Execute the tool with given arguments."""
        pass
    
    @abstractmethod
    def get_tool_definition(self) -> MCPTool:
        """Get the tool definition for MCP registration."""
        pass


class GraphRAGSearchTool(MCPToolHandler):
    """GraphRAG search tool for MCP."""
    
    def __init__(self, search_engine):
        """Initialize with a GraphRAG search engine."""
        self.search_engine = search_engine
    
    async def execute(self, arguments: Dict[str, Any]) -> MCPToolResult:
        """Execute GraphRAG search."""
        try:
            query = arguments.get("query", "")
            search_type = arguments.get("search_type", "local")
            max_results = arguments.get("max_results", 10)
            
            if not query:
                return MCPToolResult(
                    call_id=arguments.get("call_id"),
                    success=False,
                    error="Query parameter is required"
                )
            
            # Execute search based on type
            if search_type == "local":
                result = await self.search_engine.local_search(
                    query=query,
                    k=max_results
                )
            elif search_type == "global":
                result = await self.search_engine.global_search(
                    query=query,
                    k=max_results
                )
            elif search_type == "deep":
                result = await self.search_engine.deep_search(
                    query=query,
                    k=max_results
                )
            else:
                return MCPToolResult(
                    call_id=arguments.get("call_id"),
                    success=False,
                    error=f"Unsupported search type: {search_type}"
                )
            
            return MCPToolResult(
                call_id=arguments.get("call_id"),
                success=True,
                result={
                    "query": query,
                    "search_type": search_type,
                    "response": result.response,
                    "context_data": result.context_data,
                    "completion_time": result.completion_time,
                },
                metadata={
                    "llm_calls": result.llm_calls,
                    "prompt_tokens": result.prompt_tokens,
                    "output_tokens": result.output_tokens,
                }
            )
            
        except Exception as e:
            logger.error(f"Error executing GraphRAG search: {e}")
            return MCPToolResult(
                call_id=arguments.get("call_id"),
                success=False,
                error=str(e)
            )
    
    def get_tool_definition(self) -> MCPTool:
        """Get GraphRAG search tool definition."""
        return MCPTool(
            name="graphrag_search",
            description="Search through GraphRAG knowledge base using different search strategies",
            parameters=[
                MCPToolParameter(
                    name="query",
                    type="string",
                    description="The search query to execute",
                    required=True
                ),
                MCPToolParameter(
                    name="search_type",
                    type="string",
                    description="Type of search to perform",
                    required=False,
                    enum=["local", "global", "deep"],
                    default="local"
                ),
                MCPToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximum number of results to return",
                    required=False,
                    default=10
                )
            ]
        )


class GraphRAGEntityTool(MCPToolHandler):
    """GraphRAG entity extraction tool for MCP."""
    
    def __init__(self, entity_extractor):
        """Initialize with entity extractor."""
        self.entity_extractor = entity_extractor
    
    async def execute(self, arguments: Dict[str, Any]) -> MCPToolResult:
        """Execute entity extraction."""
        try:
            text = arguments.get("text", "")
            entity_types = arguments.get("entity_types", ["person", "organization", "location"])
            
            if not text:
                return MCPToolResult(
                    call_id=arguments.get("call_id"),
                    success=False,
                    error="Text parameter is required"
                )
            
            entities = await self.entity_extractor.extract_entities(
                text=text,
                entity_types=entity_types
            )
            
            return MCPToolResult(
                call_id=arguments.get("call_id"),
                success=True,
                result={
                    "entities": [entity.to_dict() for entity in entities],
                    "entity_count": len(entities),
                }
            )
            
        except Exception as e:
            logger.error(f"Error executing entity extraction: {e}")
            return MCPToolResult(
                call_id=arguments.get("call_id"),
                success=False,
                error=str(e)
            )
    
    def get_tool_definition(self) -> MCPTool:
        """Get entity extraction tool definition."""
        return MCPTool(
            name="graphrag_extract_entities",
            description="Extract entities from text using GraphRAG entity extraction",
            parameters=[
                MCPToolParameter(
                    name="text",
                    type="string",
                    description="The text to extract entities from",
                    required=True
                ),
                MCPToolParameter(
                    name="entity_types",
                    type="array",
                    description="Types of entities to extract",
                    required=False,
                    default=["person", "organization", "location"]
                )
            ]
        )


class MCPClient:
    """MCP client for tool calling integration."""
    
    def __init__(self):
        """Initialize MCP client."""
        self.tools: Dict[str, MCPToolHandler] = {}
        self.tool_definitions: Dict[str, MCPTool] = {}
    
    def register_tool(self, handler: MCPToolHandler) -> None:
        """Register a tool handler."""
        tool_def = handler.get_tool_definition()
        self.tools[tool_def.name] = handler
        self.tool_definitions[tool_def.name] = tool_def
        logger.info(f"Registered MCP tool: {tool_def.name}")
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools in MCP format."""
        return [tool.to_dict() for tool in self.tool_definitions.values()]
    
    async def call_tool(self, tool_call: MCPToolCall) -> MCPToolResult:
        """Execute a tool call."""
        if tool_call.tool_name not in self.tools:
            return MCPToolResult(
                call_id=tool_call.call_id,
                success=False,
                error=f"Tool not found: {tool_call.tool_name}"
            )
        
        handler = self.tools[tool_call.tool_name]
        
        # Add call_id to arguments for tracking
        arguments = tool_call.arguments.copy()
        if tool_call.call_id:
            arguments["call_id"] = tool_call.call_id
        
        try:
            result = await handler.execute(arguments)
            result.call_id = tool_call.call_id
            return result
        except Exception as e:
            logger.error(f"Error calling tool {tool_call.tool_name}: {e}")
            return MCPToolResult(
                call_id=tool_call.call_id,
                success=False,
                error=str(e)
            )
    
    async def call_tools_parallel(self, tool_calls: List[MCPToolCall]) -> List[MCPToolResult]:
        """Execute multiple tool calls in parallel."""
        tasks = [self.call_tool(call) for call in tool_calls]
        return await asyncio.gather(*tasks)
    
    def validate_tool_call(self, tool_call: MCPToolCall) -> Optional[str]:
        """Validate a tool call against the tool definition."""
        if tool_call.tool_name not in self.tool_definitions:
            return f"Tool not found: {tool_call.tool_name}"
        
        tool_def = self.tool_definitions[tool_call.tool_name]
        
        # Check required parameters
        required_params = {p.name for p in tool_def.parameters if p.required}
        provided_params = set(tool_call.arguments.keys())
        
        missing_params = required_params - provided_params
        if missing_params:
            return f"Missing required parameters: {', '.join(missing_params)}"
        
        # Check parameter types (basic validation)
        for param in tool_def.parameters:
            if param.name in tool_call.arguments:
                value = tool_call.arguments[param.name]
                if param.enum and value not in param.enum:
                    return f"Invalid value for {param.name}: {value}. Must be one of {param.enum}"
        
        return None  # No validation errors


# Utility functions for GraphRAG MCP integration
def create_graphrag_mcp_client(search_engine=None, entity_extractor=None) -> MCPClient:
    """Create MCP client with GraphRAG tools."""
    client = MCPClient()
    
    if search_engine:
        client.register_tool(GraphRAGSearchTool(search_engine))
    
    if entity_extractor:
        client.register_tool(GraphRAGEntityTool(entity_extractor))
    
    return client


def parse_tool_calls_from_llm_response(response: str) -> List[MCPToolCall]:
    """Parse tool calls from LLM response."""
    tool_calls = []
    
    try:
        # Try to parse as JSON array
        data = json.loads(response)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "tool_name" in item:
                    tool_calls.append(MCPToolCall(
                        tool_name=item["tool_name"],
                        arguments=item.get("arguments", {}),
                        call_id=item.get("call_id")
                    ))
        elif isinstance(data, dict) and "tool_name" in data:
            tool_calls.append(MCPToolCall(
                tool_name=data["tool_name"],
                arguments=data.get("arguments", {}),
                call_id=data.get("call_id")
            ))
    except json.JSONDecodeError:
        logger.warning("Failed to parse tool calls from LLM response")
    
    return tool_calls 