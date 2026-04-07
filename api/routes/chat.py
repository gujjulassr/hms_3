from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import Response
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


@router.post("/voice")
async def voice_chat(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """End-to-end speech: Audio in → Whisper ASR → LLM → TTS → Audio out."""
    from services.speech import speech_to_text, text_to_speech
    from agent.graph import get_response

    # ASR: Speech → Text
    audio_bytes = await file.read()
    user_text = speech_to_text(audio_bytes)

    if not user_text:
        return {"error": "Could not understand audio."}

    # Save to MongoDB
    save_message(user["email"], "user", f"[Voice] {user_text}")

    # LLM: Text → Response
    response_text = await get_response(user_text, user)
    save_message(user["email"], "assistant", response_text)

    # TTS: Text → Speech
    audio_response = text_to_speech(response_text)

    return Response(
        content=audio_response,
        media_type="audio/mpeg",
        headers={
            "X-Transcript": user_text,
            "X-Response": response_text[:200],
        }
    )


@router.post("/speak")
async def text_to_speech_endpoint(req: ChatRequest, user: dict = Depends(get_current_user)):
    """Convert text to speech. Send text, get audio back."""
    from services.speech import text_to_speech
    audio = text_to_speech(req.message)
    return Response(content=audio, media_type="audio/mpeg")


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Transcribe audio to text using Whisper."""
    from services.speech import speech_to_text
    audio_bytes = await file.read()
    text = speech_to_text(audio_bytes)
    return {"text": text}


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
