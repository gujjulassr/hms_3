from fastapi import APIRouter, Depends
from pydantic import BaseModel
from config.auth import get_current_user
from services.chat_store import save_message, get_history, clear_history

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


@router.post("/message")
async def chat_message(req: ChatRequest, user: dict = Depends(get_current_user)):
    """Route chat messages to the appropriate LangGraph agent based on role."""
    from agent.graph import get_response

    # Save user message to MongoDB
    save_message(user["email"], "user", req.message)

    response = await get_response(req.message, user)

    # Save assistant response to MongoDB
    save_message(user["email"], "assistant", response)

    return {"response": response}


@router.get("/history")
async def chat_history(user: dict = Depends(get_current_user)):
    """Get chat history from MongoDB."""
    messages = get_history(user["email"])
    return {"messages": [{"role": m["role"], "text": m["text"]} for m in messages]}


@router.delete("/history")
async def delete_chat_history(user: dict = Depends(get_current_user)):
    """Clear chat history."""
    clear_history(user["email"])
    return {"message": "Chat history cleared."}
