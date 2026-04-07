"""
Speech service — ASR (Whisper) + TTS (OpenAI) for end-to-end speech chat.
"""
import os
import tempfile
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def speech_to_text(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    """Convert speech to text using OpenAI Whisper."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        f.flush()
        with open(f.name, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        os.unlink(f.name)
    return transcript.strip()


def text_to_speech(text: str, voice: str = "alloy") -> bytes:
    """Convert text to speech using OpenAI TTS. Returns audio bytes (mp3).
    Voices: alloy, echo, fable, onyx, nova, shimmer
    """
    response = client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text
    )
    return response.content
