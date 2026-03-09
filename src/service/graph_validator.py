import re
from typing import List, Tuple, Set, Dict

from dto.models import GraphSubmission, GraphEdge, GraphNodeModel

# Validation constants
MAX_NODES = 50
MAX_EDGES = 200
INTENT_PATTERN = re.compile(r"^[a-z]+(_[a-z]+){0,3}$")
NODE_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")

class ValidationError(Exception):
    """Custom exception for validation errors."""
    
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def validate_intent_format(intent: str) -> Tuple[bool, str]:
    """
    Validate intent format.
    
    Rules:
    - Must be 1-4 words separated by underscores
    - Only lowercase letters allowed
    - Regex: ^[a-z]+(_[a-z]+){0,3}$
    
    Returns:
        Tuple of (is_valid, error_message)
    """
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
    """
    Validate that all node IDs are unique.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
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
    """
    Validate that all node IDs match the required pattern.
    
    Rules:
    - Regex: ^[a-z0-9_]+$
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    for node in nodes:
        if not NODE_ID_PATTERN.match(node.id):
            return False, (
                f"Node ID '{node.id}' must contain only lowercase letters, "
                "numbers, and underscores"
            )
    
    return True, ""


def validate_limits(nodes: List[GraphNodeModel], edges: List[GraphEdge]) -> Tuple[bool, str]:
    """
    Validate node and edge count limits.
    
    Rules:
    - Maximum 50 nodes
    - Maximum 200 edges
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(nodes) > MAX_NODES:
        return False, f"Graph exceeds maximum node limit of {MAX_NODES} (has {len(nodes)})"
    
    if len(edges) > MAX_EDGES:
        return False, f"Graph exceeds maximum edge limit of {MAX_EDGES} (has {len(edges)})"
    
    return True, ""


def validate_edge_structure(
    nodes: List[GraphNodeModel], 
    edges: List[GraphEdge]
) -> Tuple[bool, str]:
    """
    Validate edge structure - all edge endpoints must exist as nodes.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
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
    nodes: List[GraphNodeModel], 
    edges: List[GraphEdge]
) -> Tuple[bool, str]:
    """
    Validate that the graph is a Directed Acyclic Graph (DAG).
    
    Uses DFS-based cycle detection.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
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
    nodes: List[GraphNodeModel], 
    edges: List[GraphEdge]
) -> Tuple[bool, str]:
    """
    Validate that all nodes are reachable from the entry node.
    
    Entry node is the first node in the nodes list.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
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


async def validate_graph_schema(submission: GraphSubmission) -> Tuple[bool, str]:
    """
    Validate the complete graph schema.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
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
    
    return True, ""
