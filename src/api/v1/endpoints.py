from fastapi import APIRouter, HTTPException, status

from src.dto.models import (
    ErrorResponse,
    GraphSubmission,
    GraphResponse,
    GraphListResponse,
)
from src.service.graph_registry import get_graph_registry

router = APIRouter()


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
    registry = get_graph_registry()
    
    # Get the base URL from the request context
    # We'll use a default since we don't have direct access to scheme/host
    base_url = "http://localhost:8000"
    
    success, message = await registry.add_graph(request, base_url)
    
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
    registry = get_graph_registry()
    return registry.list_graphs()


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
    registry = get_graph_registry()
    graph = registry.get_graph(intent)
    
    if graph is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "GRAPH_NOT_FOUND", "message": f"Graph with intent '{intent}' not found"},
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
    registry = get_graph_registry()
    success, message = registry.delete_graph(intent)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "GRAPH_NOT_FOUND", "message": message},
        )
    
    return GraphResponse(
        intent=intent,
        message=message,
    )
