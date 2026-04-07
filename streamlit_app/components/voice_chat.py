"""
Voice chat component using browser's Web Speech API for continuous ASR
and OpenAI TTS for response audio.
"""
import streamlit as st
import streamlit.components.v1 as components


def voice_chat_component(key="voice_chat"):
    """Renders a voice chat interface with continuous speech recognition."""

    html_code = """
    <div id="voice-container" style="padding: 10px; font-family: sans-serif;">
        <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 10px;">
            <button id="startBtn" onclick="startListening()"
                style="padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px;">
                Start Listening
            </button>
            <button id="stopBtn" onclick="stopListening()" disabled
                style="padding: 10px 20px; background: #f44336; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px;">
                Stop
            </button>
            <span id="status" style="color: #666; font-size: 14px;">Click Start to begin</span>
        </div>
        <div id="interim" style="color: #999; font-style: italic; min-height: 24px; margin-bottom: 5px;"></div>
        <div id="final-text" style="display: none;"></div>
    </div>

    <script>
    let recognition = null;
    let finalTranscript = '';

    function startListening() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            document.getElementById('status').textContent = 'Speech recognition not supported in this browser.';
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            document.getElementById('status').textContent = 'Listening...';
            document.getElementById('status').style.color = '#4CAF50';
            finalTranscript = '';
        };

        recognition.onresult = (event) => {
            let interim = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript + ' ';
                } else {
                    interim += event.results[i][0].transcript;
                }
            }
            document.getElementById('interim').textContent = interim;
            if (finalTranscript.trim()) {
                document.getElementById('final-text').textContent = finalTranscript.trim();
            }
        };

        recognition.onend = () => {
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
            document.getElementById('status').textContent = 'Stopped';
            document.getElementById('status').style.color = '#666';
            document.getElementById('interim').textContent = '';

            // Send final transcript to Streamlit
            if (finalTranscript.trim()) {
                const textEl = document.getElementById('final-text');
                textEl.textContent = finalTranscript.trim();
                textEl.style.display = 'block';

                // Use Streamlit's setComponentValue
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: finalTranscript.trim()
                }, '*');
            }
        };

        recognition.onerror = (event) => {
            document.getElementById('status').textContent = 'Error: ' + event.error;
            document.getElementById('status').style.color = '#f44336';
        };

        recognition.start();
    }

    function stopListening() {
        if (recognition) {
            recognition.stop();
        }
    }
    </script>
    """

    # Render the component
    components.html(html_code, height=120, key=key)

    # Check for voice input via query params (workaround for Streamlit component communication)
    return None


def render_voice_chat(api_url, headers, history_key="chat_history", chat_key="voice"):
    """Full voice chat interface with TTS playback."""
    import requests as req

    col_mode, _ = st.columns([1, 3])
    with col_mode:
        voice_on = st.toggle("Voice Mode", key=f"voice_toggle_{chat_key}")

    if voice_on:
        voice_chat_component(key=f"vc_{chat_key}")

        # Manual voice input fallback (since Streamlit component messaging is limited)
        st.caption("Or type what you said:")
        with st.form(f"voice_form_{chat_key}", clear_on_submit=True):
            voice_text = st.text_input("Voice transcript", label_visibility="collapsed",
                                       placeholder="Speak or type here...", key=f"vt_{chat_key}")
            col_send, col_tts = st.columns([3, 1])
            with col_send:
                sent = st.form_submit_button("Send", use_container_width=True)
            with col_tts:
                play_tts = st.form_submit_button("Send + Speak", use_container_width=True)

        if (sent or play_tts) and voice_text:
            st.session_state[history_key].append({"role": "user", "text": f"[Voice] {voice_text}"})
            cr = req.post(f"{api_url}/api/chat/message",
                          json={"message": voice_text}, headers=headers)
            if cr.status_code == 200:
                reply = cr.json()["response"]
            else:
                reply = "Something went wrong."
            st.session_state[history_key].append({"role": "assistant", "text": reply})

            # TTS playback
            if play_tts:
                tts_r = req.post(f"{api_url}/api/chat/speak",
                                 json={"message": reply}, headers=headers)
                if tts_r.status_code == 200:
                    st.audio(tts_r.content, format="audio/mp3", autoplay=True)

            st.rerun()

    return voice_on
