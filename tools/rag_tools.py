from langchain_core.tools import tool


@tool
async def query_feedback_rag(query: str, doctor_name: str = "") -> str:
    """Search and analyze patient feedback using RAG. Ask questions like:
    'What do patients say about Dr. Sharma?', 'Any complaints about wait times?',
    'Overall patient satisfaction', 'Common feedback themes'.
    Optionally filter by doctor name."""
    from services.rag_feedback import generate_rag_response
    try:
        return generate_rag_response(query, doctor_name)
    except Exception as e:
        return f"Could not search feedback: {e}"


@tool
async def sync_feedback_store() -> str:
    """Sync all patient feedback from database to the RAG vector store. Run this to update the feedback search index."""
    from services.rag_feedback import sync_feedback_to_vectorstore
    try:
        count = await sync_feedback_to_vectorstore()
        return f"Synced {count} feedback entries to vector store."
    except Exception as e:
        return f"Sync failed: {e}"
