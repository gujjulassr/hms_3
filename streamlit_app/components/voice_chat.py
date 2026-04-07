"""
Voice input component — uses Web Speech API via custom Streamlit component.
Continuous listening, auto-sends on pause, pauses during TTS playback.
"""
import os
import streamlit.components.v1 as components

_VOICE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_input")
_voice_input = components.declare_component("voice_input", path=_VOICE_DIR)


def voice_input(auto_start=True, resume=True, key="voice_input"):
    """
    Renders the voice input component.
    Returns dict with {"transcript": "...", "ts": timestamp} when speech is detected.
    Returns None when no speech.
    """
    result = _voice_input(
        auto_start=auto_start,
        resume=resume,
        key=key,
        default=None,
    )
    return result
