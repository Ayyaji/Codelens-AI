import streamlit as st
import streamlit.components.v1 as components

def render_behaviour_tracker():
    components.html("""
    <script>
        let keystrokes = 0;
        let backspaces = 0;
        let startTime = null;
        let endTime = null;

        document.addEventListener('keydown', function(e) {
            if (startTime === null) {
                startTime = new Date().getTime();
            }
            keystrokes++;
            if (e.key === 'Backspace') {
                backspaces++;
            }
            endTime = new Date().getTime();
        });

        function calculateWPM() {
            if (startTime === null || endTime === null) return 0;
            let durationMinutes = (endTime - startTime) / 60000;
            if (durationMinutes === 0) return 0;
            let wpm = (keystrokes / 5) / durationMinutes;
            return Math.round(wpm);
        }

        function getBehaviourData() {
            return {
                wpm: calculateWPM(),
                backspaces: backspaces,
                duration: endTime ? Math.round((endTime - startTime) / 1000) : 0
            };
        }

        window.getBehaviourData = getBehaviourData;

        setInterval(function() {
            let data = getBehaviourData();
            window.parent.postMessage({
                type: 'behaviour',
                wpm: data.wpm,
                backspaces: data.backspaces,
                duration: data.duration
            }, '*');
        }, 5000);
    </script>
    <p style="color: gray; font-size: 12px;">🔍 Behaviour monitoring active</p>
    """, height=30)