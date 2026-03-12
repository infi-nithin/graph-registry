from fastapi import APIRouter, HTTPException, status
import logging

from dto.models import (
    ErrorResponse,
    GraphSubmission,
    GraphResponse,
    GraphListResponse,
    IntentListResponse,
)
from service.graph_registry import GraphRegistry

router = APIRouter()

# Create a singleton instance
_registry: GraphRegistry = None


def get_registry() -> GraphRegistry:
    """Get the graph registry instance."""
    global _registry
    if _registry is None:
        _registry = GraphRegistry()
    return _registry


@router.get("/ping", tags=["health"])
async def ping():
    return {"ping": "pong"}


@router.post(
    "/graphs",
    response_model=GraphResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["graphs"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid graph or intent"},
        409: {"model": ErrorResponse, "description": "Intent already exists"},
    },
)
async def add_graph(request: GraphSubmission):
    """Add a new graph to the registry.

    The intent must be unique within the registry. Each intent can have
    only one graph mapped to it.
    """
    logger = logging.getLogger(__name__)
    registry = get_registry()
    try:
        success, message = await registry.add_graph(request)
    except Exception as e:
        logger.exception("Error adding graph: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "INTERNAL_ERROR", "message": str(e)},
        )

    if not success:
        if "already exists" in message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "INTENT_EXISTS", "message": message},
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "VALIDATION_ERROR", "message": message},
        )

    return GraphResponse(
        intent=request.intent,
        message=message,
    )


@router.get(
    "/graphs",
    response_model=GraphListResponse,
    tags=["graphs"],
)
async def list_graphs():
    """List all registered graphs."""
    registry = get_registry()
    return await registry.list_graphs()


@router.get(
    "/intents",
    response_model=IntentListResponse,
    tags=["intents"],
)
async def list_intents():
    """List all registered intents."""
    registry = get_registry()
    return await registry.list_intents()


@router.get(
    "/graphs/{intent}",
    response_model=GraphSubmission,
    tags=["graphs"],
    responses={
        404: {"model": ErrorResponse, "description": "Graph not found"},
    },
)
async def get_graph(intent: str):
    """Get a specific graph by intent."""
    registry = get_registry()
    graph = await registry.get_graph(intent)

    if graph is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "GRAPH_NOT_FOUND",
                "message": f"Graph with intent '{intent}' not found",
            },
        )

    return graph


@router.delete(
    "/graphs/{intent}",
    response_model=GraphResponse,
    tags=["graphs"],
    responses={
        404: {"model": ErrorResponse, "description": "Graph not found"},
    },
)
async def delete_graph(intent: str):
    """Delete a graph from the registry."""
    registry = get_registry()
    success, message = await registry.delete_graph(intent)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "GRAPH_NOT_FOUND", "message": message},
        )

    return GraphResponse(
        intent=intent,
        message=message,
    )


@router.put(
    "/graphs/{intent}",
    response_model=GraphResponse,
    tags=["graphs"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid graph or intent"},
        404: {"model": ErrorResponse, "description": "Graph not found"},
    },
)
async def update_graph(intent: str, request: GraphSubmission):
    """Update an existing graph in the registry.

    The intent in the path must match the intent in the request body.
    """
    registry = get_registry()

    # Verify intent matches
    if request.intent != intent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INTENT_MISMATCH",
                "message": f"Intent in path '{intent}' does not match intent in body '{request.intent}'",
            },
        )

    success, message = await registry.update_graph(intent, request)

    if not success:
        if "not found" in message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "GRAPH_NOT_FOUND", "message": message},
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "VALIDATION_ERROR", "message": message},
        )

    return GraphResponse(
        intent=intent,
        message=message,
    )
