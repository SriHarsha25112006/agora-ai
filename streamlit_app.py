import streamlit as st
import requests
import json
import os

# Configuration: Point this to your Render backend URL once deployed.
# E.g., API_URL = "https://agora-ai-backend.onrender.com"
API_URL = os.getenv("API_URL", "http://localhost:8080")

st.set_page_config(page_title="Agora AI", page_icon="🏛️", layout="wide")

st.title("🏛️ Agora AI — Multi-Agent Debate Engine")
st.markdown("Five specialized AI perspectives (Ethical, Legal, Economic, Social, Consensus) collaborate across four structured rounds.")

st.markdown("---")

topic = st.text_area("Debate Topic or Situation", placeholder="e.g., Should universal basic income be implemented globally?", height=100)

col1, col2 = st.columns(2)
with col1:
    mode = st.radio("Mode", ["debate", "situation"], index=0, format_func=lambda x: "⚔️ Debate" if x == "debate" else "🔮 Situation Analysis")
with col2:
    personality = st.selectbox("Agent Personality", ["balanced", "academic", "aggressive", "friendly", "philosophical"])

if st.button("Start Debate", type="primary", use_container_width=True):
    if not topic.strip():
        st.error("Please enter a topic.")
    else:
        st.divider()
        st.subheader(f"Topic: {topic}")
        
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
                                st.markdown(f"#### {evt.get('round_label', 'Round')}")
                                
                            elif evt.get("type") == "agent_chunk":
                                current_content += evt.get("chunk", "")
                                with agent_placeholder.container():
                                    with st.chat_message(current_agent.get("agent", "Agent"), avatar=current_agent.get("icon", "🤖")):
                                        st.markdown(f"**{current_agent.get('agent', '')}** ({current_agent.get('role', '')})")
                                        st.markdown(current_content)
                                        
                            elif evt.get("type") == "agent_end":
                                agent_placeholder.empty()
                                with st.chat_message(current_agent.get("agent", "Agent"), avatar=current_agent.get("icon", "🤖")):
                                    st.markdown(f"**{current_agent.get('agent', '')}** ({current_agent.get('role', '')})")
                                    st.markdown(current_content)
                                
                            elif evt.get("type") == "debate_end":
                                st.success("⚖️ Debate Complete.")
                                
        except Exception as e:
            st.error(f"Could not connect to backend at {API_URL}. Ensure the backend is running. Error: {e}")
