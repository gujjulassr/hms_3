"""
Voice chat component — mic button with Web Speech API.
Click mic → listens → auto-sends on pause → plays TTS response.
"""
import streamlit as st
import streamlit.components.v1 as components


def voice_input_widget():
    """Embeds a mic button that uses Web Speech API. Returns transcript via session state."""

    html_code = """
    <div style="display: flex; align-items: center; gap: 12px; padding: 8px 0;">
        <button id="micBtn" onclick="toggleMic()" style="
            width: 50px; height: 50px; border-radius: 50%; border: none;
            background: #4CAF50; color: white; font-size: 24px; cursor: pointer;
            display: flex; align-items: center; justify-content: center;
            transition: background 0.3s;">
            🎤
        </button>
        <span id="status" style="color: #888; font-size: 14px;">Click mic to speak</span>
    </div>
    <div id="transcript" style="display:none;"></div>

    <script>
    let recognition = null;
    let isListening = false;
    let finalText = '';
    let silenceTimer = null;

    function toggleMic() {
        if (isListening) {
            stopMic();
        } else {
            startMic();
        }
    }

    function startMic() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            document.getElementById('status').textContent = 'Not supported in this browser. Use Chrome.';
            return;
        }
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SR();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';
        finalText = '';

        recognition.onstart = () => {
            isListening = true;
            document.getElementById('micBtn').style.background = '#f44336';
            document.getElementById('micBtn').textContent = '⏹';
            document.getElementById('status').textContent = 'Listening...';
            document.getElementById('status').style.color = '#f44336';
        };

        recognition.onresult = (e) => {
            clearTimeout(silenceTimer);
            let interim = '';
            for (let i = e.resultIndex; i < e.results.length; i++) {
                if (e.results[i].isFinal) {
                    finalText += e.results[i][0].transcript + ' ';
                } else {
                    interim += e.results[i][0].transcript;
                }
            }
            document.getElementById('status').textContent = finalText + interim;

            // Auto-send after 2 seconds of silence
            silenceTimer = setTimeout(() => {
                if (finalText.trim()) {
                    stopMic();
                }
            }, 2000);
        };

        recognition.onend = () => {
            isListening = false;
            document.getElementById('micBtn').style.background = '#4CAF50';
            document.getElementById('micBtn').textContent = '🎤';

            if (finalText.trim()) {
                document.getElementById('status').textContent = 'Sent: ' + finalText.trim();
                document.getElementById('status').style.color = '#4CAF50';
                document.getElementById('transcript').textContent = finalText.trim();

                // Send to Streamlit via URL hash
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: finalText.trim()
                }, '*');
            } else {
                document.getElementById('status').textContent = 'Click mic to speak';
                document.getElementById('status').style.color = '#888';
            }
        };

        recognition.onerror = (e) => {
            document.getElementById('status').textContent = 'Error: ' + e.error;
            isListening = false;
            document.getElementById('micBtn').style.background = '#4CAF50';
            document.getElementById('micBtn').textContent = '🎤';
        };

        recognition.start();
    }

    function stopMic() {
        clearTimeout(silenceTimer);
        if (recognition) recognition.stop();
    }
    </script>
    """
    components.html(html_code, height=80)
