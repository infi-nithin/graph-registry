from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


class GraphEdge(BaseModel):
    """Edge definition connecting two nodes."""

    from_: str = Field(..., alias="from", description="Source node ID")
    to: str = Field(..., description="Target node ID")

    class Config:
        populate_by_name = True


class GraphNode(BaseModel):
    """Base graph node with common fields."""

    id: str = Field(..., description="Unique node identifier", pattern=r"^[a-z0-9_]+$")
    type: str = Field(..., description="Node type: mcp_tool, llm, or sub_agent")


class MCPToolNode(GraphNode):
    """MCP Tool node - requires tool_name field."""

    type: Literal["mcp_tool"] = "mcp_tool"
    tool_name: str = Field(..., description="Name of the MCP tool to invoke")


class LLMNode(GraphNode):
    """LLM node - requires prompt_template field."""

    type: Literal["llm"] = "llm"
    prompt_template: str = Field(..., description="Prompt template for the LLM")


class SubAgentNode(GraphNode):
    """Sub-agent node - requires agent_name field."""

    type: Literal["sub_agent"] = "sub_agent"
    agent_name: str = Field(..., description="Name of the sub-agent to invoke")


# Type union for all node types
GraphNodeModel = MCPToolNode | LLMNode | SubAgentNode


class Graph(BaseModel):
    """Graph structure containing version, nodes, and edges."""

    version: str = Field(..., description="Graph version identifier")
    nodes: List[GraphNodeModel] = Field(..., description="List of graph nodes")
    edges: List[GraphEdge] = Field(..., description="List of graph edges")


class GraphSubmission(BaseModel):
    """Full graph submission payload with intent and graph."""

    intent: str = Field(
        ..., description="Intent identifier (1-4 words, lowercase with underscores)"
    )
    graph: Graph = Field(..., description="Graph structure")


class GraphResponse(BaseModel):
    """Response after successful graph submission."""

    intent: str
    message: str = Field(default="Graph registered successfully")


class GraphListResponse(BaseModel):
    """Response for listing all graphs."""

    graphs: List[GraphSubmission]
    total_count: int
