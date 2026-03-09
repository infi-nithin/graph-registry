from typing import Dict, Optional, Tuple

from dto.models import GraphSubmission, GraphListResponse, IntentListResponse
from service.graph_validator import (
    validate_intent_format,
    validate_graph_schema,
)


class GraphRegistry:
    """In-memory graph registry storage and management."""
    
    def __init__(self):
        """Initialize the graph registry."""
        self.graphs: Dict[str, GraphSubmission] = {}
    
    async def add_graph(
        self, 
        submission: GraphSubmission
    ) -> Tuple[bool, str]:
        """
        Add a new graph to the registry.
        
        Args:
            submission: The graph submission containing intent and graph
            base_url: Base URL (kept for API compatibility, not used)
            
        Returns:
            Tuple of (success, message)
        """
        # Validate intent format
        is_valid, error = validate_intent_format(submission.intent)
        if not is_valid:
            return False, error
        
        # Check if intent already exists
        if submission.intent in self.graphs:
            return False, f"Intent '{submission.intent}' already exists in registry"
        
        # Validate graph schema
        is_valid, error = await validate_graph_schema(submission)
        if not is_valid:
            return False, error
        
        # Store the graph
        self.graphs[submission.intent] = submission
        return True, f"Graph '{submission.intent}' registered successfully"
    
    def get_graph(self, intent: str) -> Optional[GraphSubmission]:
        """
        Get a graph by intent.
        
        Args:
            intent: The intent identifier
            
        Returns:
            GraphSubmission if found, None otherwise
        """
        return self.graphs.get(intent)
    
    def list_graphs(self) -> GraphListResponse:
        """
        List all registered graphs.
        
        Returns:
            GraphListResponse containing all graphs
        """
        graphs_list = list(self.graphs.values())
        return GraphListResponse(
            graphs=graphs_list,
            total_count=len(graphs_list)
        )
    
    def list_intents(self) -> IntentListResponse:
        """
        List all registered intents.
        
        Returns:
            IntentListResponse containing all intent names
        """
        intents_list = list(self.graphs.keys())
        return IntentListResponse(
            intents=intents_list,
            total_count=len(intents_list)
        )
    
    def delete_graph(self, intent: str) -> Tuple[bool, str]:
        """
        Delete a graph from the registry.
        
        Args:
            intent: The intent identifier
            
        Returns:
            Tuple of (success, message)
        """
        if intent not in self.graphs:
            return False, f"Graph with intent '{intent}' not found"
        
        del self.graphs[intent]
        return True, f"Graph with intent '{intent}' deleted successfully"
    
    async def update_graph(
        self,
        intent: str,
        submission: GraphSubmission
    ) -> Tuple[bool, str]:
        """
        Update an existing graph in the registry.
        
        Args:
            intent: The intent identifier
            submission: The new graph submission
            
        Returns:
            Tuple of (success, message)
        """
        # Check if intent exists
        if intent not in self.graphs:
            return False, f"Graph with intent '{intent}' not found"
        
        # Validate graph schema
        is_valid, error = await validate_graph_schema(submission)
        if not is_valid:
            return False, error
        
        # Store the updated graph
        self.graphs[intent] = submission
        return True, f"Graph '{intent}' updated successfully"


# Singleton instance
_registry: Optional[GraphRegistry] = None


def get_graph_registry() -> GraphRegistry:
    """Get the singleton graph registry instance."""
    global _registry
    if _registry is None:
        _registry = GraphRegistry()
    return _registry
