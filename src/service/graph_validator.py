import os
import re
from typing import List, Tuple, Set, Dict, Optional

import httpx
from dotenv import load_dotenv
from dto.models import GraphSubmission, GraphEdge, GraphNodeModel, MCPToolNode

load_dotenv()

# Validation constants
MAX_NODES = 50
MAX_EDGES = 200
INTENT_PATTERN = re.compile(r"^[a-z]+(_[a-z]+){0,3}$")
NODE_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")

# Tool registry configuration
TOOL_REGISTRY_BASE_URL = os.getenv("TOOL_REGISTRY_URL", "http://localhost:8001")
TOOL_REGISTRY_API_PREFIX = "/api/v1"

class ValidationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def get_tool_registry_url() -> str:
    return f"{TOOL_REGISTRY_BASE_URL}{TOOL_REGISTRY_API_PREFIX}"


async def check_tool_exists(tool_name: str) -> Tuple[bool, Optional[str]]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{get_tool_registry_url()}/mcp/tools/{tool_name}"
            response = await client.get(url)

            if response.status_code == 200:
                return True, None
            elif response.status_code == 404:
                return False, f"Tool '{tool_name}' not found in tool registry"
            else:
                return (
                    False,
                    f"Failed to verify tool '{tool_name}': tool registry returned status {response.status_code}",
                )
    except httpx.ConnectError:
        return (
            False,
            f"Cannot connect to tool registry at {TOOL_REGISTRY_BASE_URL}. Is the service running?",
        )
    except httpx.TimeoutException:
        return (
            False,
            f"Timeout while verifying tool '{tool_name}' - tool registry took too long to respond",
        )
    except Exception as e:
        return False, f"Error verifying tool '{tool_name}': {str(e)}"


def validate_intent_format(intent: str) -> Tuple[bool, str]:
    if not intent:
        return False, "Intent cannot be empty"

    if not INTENT_PATTERN.match(intent):
        return False, (
            "Intent must be 1-4 lowercase words separated by underscores "
            "(e.g., 'corporate_actions_summary'). "
            "Only lowercase letters a-z allowed."
        )

    return True, ""


def validate_node_uniqueness(nodes: List[GraphNodeModel]) -> Tuple[bool, str]:
    node_ids = [node.id for node in nodes]
    unique_ids = set(node_ids)

    if len(node_ids) != len(unique_ids):
        # Find duplicates
        seen = set()
        duplicates = set()
        for node_id in node_ids:
            if node_id in seen:
                duplicates.add(node_id)
            seen.add(node_id)

        return False, f"Duplicate node IDs found: {', '.join(duplicates)}"

    return True, ""


def validate_node_id_format(nodes: List[GraphNodeModel]) -> Tuple[bool, str]:
    for node in nodes:
        if not NODE_ID_PATTERN.match(node.id):
            return False, (
                f"Node ID '{node.id}' must contain only lowercase letters, "
                "numbers, and underscores"
            )

    return True, ""


def validate_limits(
    nodes: List[GraphNodeModel], edges: List[GraphEdge]
) -> Tuple[bool, str]:
    if len(nodes) > MAX_NODES:
        return (
            False,
            f"Graph exceeds maximum node limit of {MAX_NODES} (has {len(nodes)})",
        )

    if len(edges) > MAX_EDGES:
        return (
            False,
            f"Graph exceeds maximum edge limit of {MAX_EDGES} (has {len(edges)})",
        )

    return True, ""


def validate_edge_structure(
    nodes: List[GraphNodeModel], edges: List[GraphEdge]
) -> Tuple[bool, str]:
    node_ids = set()
    for node in nodes:
        node_ids.add(node.id)

    for edge in edges:
        if edge.from_ not in node_ids:
            return False, f"Edge source node '{edge.from_}' does not exist"
        if edge.to not in node_ids:
            return False, f"Edge target node '{edge.to}' does not exist"

    return True, ""


def validate_dag_integrity(
    nodes: List[GraphNodeModel], edges: List[GraphEdge]
) -> Tuple[bool, str]:
    # Build adjacency list
    adjacency: Dict[str, List[str]] = {node.id: [] for node in nodes}

    for edge in edges:
        adjacency[edge.from_].append(edge.to)

    # DFS for cycle detection
    visited: Set[str] = set()
    rec_stack: Set[str] = set()

    def has_cycle(node_id: str) -> bool:
        visited.add(node_id)
        rec_stack.add(node_id)

        for neighbor in adjacency.get(node_id, []):
            if neighbor not in visited:
                if has_cycle(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node_id)
        return False

    # Check all nodes including END
    all_nodes = list(adjacency.keys())
    for node_id in all_nodes:
        if node_id not in visited:
            if has_cycle(node_id):
                return False, "Graph contains cycles - must be a DAG"

    return True, ""


def validate_reachable_nodes(
    nodes: List[GraphNodeModel], edges: List[GraphEdge]
) -> Tuple[bool, str]:
    if not nodes:
        return True, ""  # Empty graph is valid

    # Build adjacency list
    adjacency: Dict[str, List[str]] = {node.id: [] for node in nodes}

    for edge in edges:
        if edge.from_ in adjacency:
            adjacency[edge.from_].append(edge.to)

    # BFS from entry node
    entry_node = nodes[0].id
    reachable: Set[str] = set()
    queue = [entry_node]

    while queue:
        node_id = queue.pop(0)
        if node_id in reachable:
            continue
        reachable.add(node_id)

        for neighbor in adjacency.get(node_id, []):
            if neighbor not in reachable:
                queue.append(neighbor)

    # Check all nodes are reachable
    all_node_ids = {node.id for node in nodes}
    unreachable = all_node_ids - reachable

    if unreachable:
        return False, f"Unreachable nodes found: {', '.join(unreachable)}"

    return True, ""


async def validate_mcp_tools(nodes: List[GraphNodeModel]) -> Tuple[bool, str]:
    # Collect all MCP tool nodes
    mcp_tool_nodes = [node for node in nodes if isinstance(node, MCPToolNode)]

    if not mcp_tool_nodes:
        return True, ""  # No MCP tools to validate

    # Check each tool
    for node in mcp_tool_nodes:
        tool_name = node.tool_name
        exists, error = await check_tool_exists(tool_name)

        if not exists:
            return False, (
                f"Node '{node.id}' references tool '{tool_name}' which is not registered "
                f"in the tool registry. Error: {error}"
            )

    return True, ""


async def validate_graph_schema(submission: GraphSubmission) -> Tuple[bool, str]:
    graph = submission.graph
    nodes = graph.nodes
    edges = graph.edges

    # Validate node uniqueness
    is_valid, error = validate_node_uniqueness(nodes)
    if not is_valid:
        return is_valid, error

    # Validate node ID format
    is_valid, error = validate_node_id_format(nodes)
    if not is_valid:
        return is_valid, error

    # Validate limits
    is_valid, error = validate_limits(nodes, edges)
    if not is_valid:
        return is_valid, error

    # Validate edge structure
    is_valid, error = validate_edge_structure(nodes, edges)
    if not is_valid:
        return is_valid, error

    # Validate DAG integrity (no cycles)
    is_valid, error = validate_dag_integrity(nodes, edges)
    if not is_valid:
        return is_valid, error

    # Validate all nodes are reachable
    is_valid, error = validate_reachable_nodes(nodes, edges)
    if not is_valid:
        return is_valid, error

    # Validate MCP tools exist in tool registry
    is_valid, error = await validate_mcp_tools(nodes)
    if not is_valid:
        return is_valid, error

    return True, ""
