from typing import Optional, Tuple

from sqlalchemy import select

from dto.models import (
    GraphSubmission,
    GraphListResponse,
    IntentListResponse,
    Graph,
    GraphEdge,
)
from service.graph_validator import (
    validate_intent_format,
    validate_graph_schema,
)
from db.models import Intent, Graph as GraphModel
from db.database import get_session_context


class GraphRegistry:
    async def add_graph(self, submission: GraphSubmission) -> Tuple[bool, str]:
        # Validate intent format
        is_valid, error = validate_intent_format(submission.intent)
        if not is_valid:
            return False, error

        try:
            async with await get_session_context() as session:
                # Check if intent already exists
                result = await session.execute(
                    select(Intent).where(Intent.name == submission.intent)
                )
                existing_intent = result.scalar_one_or_none()

                if existing_intent:
                    # Check if there's already a graph for this intent
                    graph_result = await session.execute(
                        select(GraphModel).where(
                            GraphModel.intent_id == existing_intent.id
                        )
                    )
                    existing_graph = graph_result.scalar_one_or_none()
                    if existing_graph:
                        return (
                            False,
                            f"Intent '{submission.intent}' already exists in registry",
                        )

                # Validate graph schema
                is_valid, error = await validate_graph_schema(submission)
                if not is_valid:
                    return False, error

                # Create or get intent
                if not existing_intent:
                    intent = Intent(name=submission.intent)
                    session.add(intent)
                    await session.flush()
                else:
                    intent = existing_intent

                # Create graph record
                graph = GraphModel(
                    intent_id=intent.id,
                    version=submission.graph.version,
                    graph_json=submission.graph.model_dump(mode="json"),
                )
                session.add(graph)
                await session.commit()
                return True, f"Graph '{submission.intent}' registered successfully"
        except Exception:
            raise

    async def get_graph(self, intent: str) -> Optional[GraphSubmission]:
        async with await get_session_context() as session:
            # Get intent
            result = await session.execute(select(Intent).where(Intent.name == intent))
            intent_obj = result.scalar_one_or_none()

            if not intent_obj:
                return None

            # Get the latest graph for this intent
            graph_result = await session.execute(
                select(GraphModel)
                .where(GraphModel.intent_id == intent_obj.id)
                .order_by(GraphModel.created_at.desc())
                .limit(1)
            )
            graph_obj = graph_result.scalar_one_or_none()

            if not graph_obj:
                return None

            # Convert JSON to GraphSubmission
            graph_data = graph_obj.graph_json

            # Safely get edges with default empty list
            edges_data = graph_data.get("edges", [])
            edges = []
            for e in edges_data:
                # Handle both 'from_' and 'from' key names for the source node
                from_value = e.get("from_") or e.get("from")
                to_value = e.get("to")
                if from_value and to_value:
                    edges.append(GraphEdge(from_=from_value, to=to_value))

            graph = Graph(
                version=graph_data.get("version", "1.0"),
                nodes=graph_data.get("nodes", []),
                edges=edges,
            )
            return GraphSubmission(intent=intent, graph=graph)

    async def list_graphs(self) -> GraphListResponse:
        async with await get_session_context() as session:
            # Get all intents with their latest graphs
            result = await session.execute(select(Intent).where(Intent.is_active))
            intents = result.scalars().all()

            graphs_list = []
            for intent in intents:
                # Get latest graph for each intent
                graph_result = await session.execute(
                    select(GraphModel)
                    .where(GraphModel.intent_id == intent.id)
                    .order_by(GraphModel.created_at.desc())
                    .limit(1)
                )
                graph_obj = graph_result.scalar_one_or_none()

                if graph_obj:
                    graph_data = graph_obj.graph_json
                    # Safely construct edges
                    edges_data = graph_data.get("edges", [])
                    edges = []
                    for e in edges_data:
                        # Handle both 'from_' and 'from' key names for the source node
                        from_value = e.get("from_") or e.get("from")
                        to_value = e.get("to")
                        if from_value and to_value:
                            edges.append(GraphEdge(from_=from_value, to=to_value))

                    graph = Graph(
                        version=graph_data.get("version", "1.0"),
                        nodes=graph_data.get("nodes", []),
                        edges=edges,
                    )
                    graphs_list.append(GraphSubmission(intent=intent.name, graph=graph))
            return GraphListResponse(graphs=graphs_list, total_count=len(graphs_list))

    async def list_intents(self) -> IntentListResponse:
        async with await get_session_context() as session:
            result = await session.execute(select(Intent.name).where(Intent.is_active))
            intents_list = result.scalars().all()

            return IntentListResponse(
                intents=intents_list, total_count=len(intents_list)
            )

    async def delete_graph(self, intent: str) -> Tuple[bool, str]:
        async with await get_session_context() as session:
            # Get intent
            result = await session.execute(select(Intent).where(Intent.name == intent))
            intent_obj = result.scalar_one_or_none()

            if not intent_obj:
                return False, f"Graph with intent '{intent}' not found"

            # Soft delete - mark as inactive
            intent_obj.is_active = False

            try:
                await session.commit()
            except Exception as e:
                raise

            return True, f"Graph with intent '{intent}' deleted successfully"

    async def update_graph(
        self, intent: str, submission: GraphSubmission
    ) -> Tuple[bool, str]:
        async with await get_session_context() as session:
            # Get intent
            result = await session.execute(select(Intent).where(Intent.name == intent))
            intent_obj = result.scalar_one_or_none()

            if not intent_obj:
                return False, f"Graph with intent '{intent}' not found"

            # Validate graph schema
            is_valid, error = await validate_graph_schema(submission)
            if not is_valid:
                return False, error

            # Get current graph
            graph_result = await session.execute(
                select(GraphModel)
                .where(GraphModel.intent_id == intent_obj.id)
                .order_by(GraphModel.created_at.desc())
                .limit(1)
            )
            current_graph = graph_result.scalar_one_or_none()

            # Update existing graph record
            if current_graph:
                current_graph.version = submission.graph.version
                current_graph.graph_json = submission.graph.model_dump(mode="json")
            else:
                # Create new graph record if none exists
                graph = GraphModel(
                    intent_id=intent_obj.id,
                    version=submission.graph.version,
                    graph_json=submission.graph.model_dump(mode="json"),
                )
                session.add(graph)
            await session.commit()

            return True, f"Graph '{intent}' updated successfully"
