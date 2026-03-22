import streamlit as st
import requests
import json
import os

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8080")

st.set_page_config(page_title="Agora AI", page_icon="🏛️", layout="wide")

# Inject Custom CSS for Glassmorphism & Agora theme
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap');

/* Base Font & Hide default Header/Footer */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}
header {visibility: hidden;}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Custom Dark Background with Glowing Orbs via CSS gradients */
.stApp {
    background: #05060f !important;
    background-image: 
        radial-gradient(circle at 15% 50%, rgba(245, 158, 11, 0.12), transparent 25%),
        radial-gradient(circle at 85% 30%, rgba(236, 72, 153, 0.12), transparent 25%),
        radial-gradient(circle at 50% 80%, rgba(124, 58, 237, 0.1), transparent 30%);
    color: #f0f0ff;
}

/* Glassmorphism Inputs */
.stTextArea textarea, .stSelectbox > div > div, .stRadio > div {
    background: rgba(255, 255, 255, 0.04) !important;
    backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 12px !important;
    color: #f0f0ff !important;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

/* Titles */
h1, h2, h3 {
    letter-spacing: -0.02em !important;
}

/* Custom Primary Button */
button[kind="primary"] {
    background: linear-gradient(135deg, #f59e0b, #ec4899) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.75rem 2rem !important;
    font-weight: 800 !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 0 20px rgba(245, 158, 11, 0.25) !important;
    width: 100% !important;
}
button[kind="primary"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 0 30px rgba(236, 72, 153, 0.4) !important;
}

/* Custom Secondary Button (Examples) */
button[kind="secondary"] {
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    color: #9090b0 !important;
    font-weight: 600 !important;
    border-radius: 20px !important;
    padding: 0.25rem 1rem !important;
    min-height: 2rem !important;
    transition: all 0.2s ease !important;
}
button[kind="secondary"]:hover {
    color: white !important;
    border-color: rgba(236, 72, 153, 0.4) !important;
    background: rgba(236, 72, 153, 0.15) !important;
}

/* Agent Chat Messages Container */
.stChatMessage {
    background: rgba(255, 255, 255, 0.03) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 16px !important;
    padding: 1.5rem !important;
    margin-bottom: 1rem !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15) !important;
}

/* Divider Lines */
hr {
    border-color: rgba(255, 255, 255, 0.1) !important;
    margin: 2rem 0 !important;
}

/* Custom Gradient Text */
.gradient-text {
    background: linear-gradient(135deg, #f59e0b, #ec4899);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 900;
}
</style>
""", unsafe_allow_html=True)

# Main UI Header
st.markdown("""
<div style="text-align: center; padding: 2rem 0;">
    <h1 style="font-size: 3.5rem; font-weight: 900; margin-bottom: 0.5rem;"><span style="color:white">🏛️ Agora </span><span class="gradient-text">AI</span></h1>
    <p style="color: #9090b0; font-size: 1.1rem; max-width: 600px; margin: 0 auto;">Multi-Agent Reasoning & Debate Engine</p>
</div>
""", unsafe_allow_html=True)

# The Agents Legend
st.markdown("""
<div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; margin-bottom: 30px;">
  <div style="background: rgba(255,255,255,0.04); border-top: 2px solid #00d4aa; padding: 12px 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
    <div style="font-size: 1.2rem; margin-bottom: 4px;">⚖️</div>
    <div style="font-weight: 700; color: #f0f0ff;">Ethical Agent</div>
    <div style="font-size: 0.75rem; color: #00d4aa; text-transform: uppercase; letter-spacing: 0.05em;">Gemma 2</div>
  </div>
  <div style="background: rgba(255,255,255,0.04); border-top: 2px solid #ff6b6b; padding: 12px 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
    <div style="font-size: 1.2rem; margin-bottom: 4px;">📜</div>
    <div style="font-weight: 700; color: #f0f0ff;">Legal Agent</div>
    <div style="font-size: 0.75rem; color: #ff6b6b; text-transform: uppercase; letter-spacing: 0.05em;">Llama 3.2</div>
  </div>
  <div style="background: rgba(255,255,255,0.04); border-top: 2px solid #ffd166; padding: 12px 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
    <div style="font-size: 1.2rem; margin-bottom: 4px;">📈</div>
    <div style="font-weight: 700; color: #f0f0ff;">Economic Agent</div>
    <div style="font-size: 0.75rem; color: #ffd166; text-transform: uppercase; letter-spacing: 0.05em;">Qwen 2.5</div>
  </div>
  <div style="background: rgba(255,255,255,0.04); border-top: 2px solid #6c63ff; padding: 12px 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
    <div style="font-size: 1.2rem; margin-bottom: 4px;">🤝</div>
    <div style="font-weight: 700; color: #f0f0ff;">Social Agent</div>
    <div style="font-size: 0.75rem; color: #6c63ff; text-transform: uppercase; letter-spacing: 0.05em;">Mistral</div>
  </div>
  <div style="background: rgba(255,255,255,0.04); border-top: 2px solid #f8f8f2; padding: 12px 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
    <div style="font-size: 1.2rem; margin-bottom: 4px;">🏛️</div>
    <div style="font-weight: 700; color: #f0f0ff;">Consensus Agent</div>
    <div style="font-size: 0.75rem; color: #f8f8f2; text-transform: uppercase; letter-spacing: 0.05em;">Phi-3.5</div>
  </div>
</div>
""", unsafe_allow_html=True)

def set_topic(new_topic):
    st.session_state.topic = new_topic

if "topic" not in st.session_state:
    st.session_state.topic = ""

topic = st.text_area("Debate Topic or Situation", key="topic", placeholder="e.g., Should universal basic income be implemented globally?", height=120)

st.markdown("<p style='font-size:0.8rem; color:#9090b0; margin-bottom: 5px; margin-top: -10px;'>Try an example:</p>", unsafe_allow_html=True)
eg1, eg2, eg3 = st.columns(3)
eg1.button("UBI Worldwide?", on_click=set_topic, args=("Should universal basic income be implemented globally?",), use_container_width=True, type="secondary")
eg2.button("AI Regulation?", on_click=set_topic, args=("Is strict government regulation of Artificial Intelligence necessary?",), use_container_width=True, type="secondary")
eg3.button("Mars Colonization?", on_click=set_topic, args=("Should humanity prioritize Mars colonization over solving Earth's immediate crises?",), use_container_width=True, type="secondary")

col1, col2 = st.columns(2)
with col1:
    mode = st.radio("Mode", ["debate", "situation"], index=0, format_func=lambda x: "⚔️ Debate Mode" if x == "debate" else "🔮 Situation Analysis")
with col2:
    personality = st.selectbox("Agent Personality", ["balanced", "academic", "aggressive", "friendly", "philosophical"])

st.markdown("<br>", unsafe_allow_html=True)

if st.button("Start Debate Engine", type="primary", use_container_width=True):
    if not topic.strip():
        st.error("Please enter a topic.")
    else:
        st.divider()
        st.markdown(f"<h3 style='text-align: center; color: white;'>Analyzing Topic: <span class='gradient-text'>{topic}</span></h3>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        url = f"{API_URL}/api/debate"
        payload = {"topic": topic, "mode": mode, "personality": personality, "rounds": 4}
        
        try:
            with requests.post(url, json=payload, stream=True) as r:
                if r.status_code != 200:
                    st.error(f"Backend error: {r.status_code}")
                    st.stop()
                
                current_agent = None
                current_content = ""
                agent_placeholder = st.empty()
                
                for line in r.iter_lines():
                    if line:
                        decoded_line = line.decode("utf-8")
                        if decoded_line.startswith("data: "):
                            try:
                                evt = json.loads(decoded_line[6:])
                            except:
                                continue
                            
                            if evt.get("type") == "agent_start":
                                current_agent = evt
                                current_content = ""
                                st.markdown(f"<p style='color: #f59e0b; font-weight: 700; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.1em;'>{evt.get('round_label', 'Round')}</p>", unsafe_allow_html=True)
                                
                            elif evt.get("type") == "agent_chunk":
                                current_content += evt.get("chunk", "")
                                with agent_placeholder.container():
                                    with st.chat_message(current_agent.get("agent", "Agent"), avatar=current_agent.get("icon", "🤖")):
                                        st.markdown(f"**{current_agent.get('agent', '')}** — *{current_agent.get('role', '')}*")
                                        st.markdown(current_content)
                                        
                            elif evt.get("type") == "agent_end":
                                agent_placeholder.empty()
                                with st.chat_message(current_agent.get("agent", "Agent"), avatar=current_agent.get("icon", "🤖")):
                                    st.markdown(f"**{current_agent.get('agent', '')}** — *{current_agent.get('role', '')}*")
                                    st.markdown(current_content)
                                
                            elif evt.get("type") == "debate_end":
                                st.markdown("---")
                                st.success("⚖️ Debate Complete.")
                                
        except Exception as e:
            st.error(f"Could not connect to backend at {API_URL}. Ensure the backend is running. Error: {e}")
