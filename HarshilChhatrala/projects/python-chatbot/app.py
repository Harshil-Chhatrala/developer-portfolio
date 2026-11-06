"""
app.py - Streamlit Frontend Interface.
Manages application state controls, chat interface layouts, cards, and styling wrappers.
"""

import streamlit as st
import pandas as pd
import os
import helpers
from chatbot import RuleBasedLaptopChatbot

# Configure global multi-pane interface defaults
st.set_page_config(
    page_title="HardwareGuru | Laptop Chatbot",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom injection layer to standardize application visuals
st.markdown("""
<style>
    .reportview-container { background: #0f1116; }
    .stChatFloatingInputContainer { background-color: rgba(15,17,22,0.9) !important; }
    div.element-container title { color: #2e7d32; }
    .rec-card {
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 20px;
        background-color: #161b22;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Path asset enforcement
DATASET_PATH = "laptop_catalog.csv"

def create_mock_csv_if_missing():
    """Generates a dataset runtime framework file if not present in the local execution directory."""
    if not os.path.exists(DATASET_PATH):
        mock_data = {
            'id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            'brand': ['Dell', 'HP', 'Lenovo', 'ASUS', 'Apple', 'Apple', 'Dell', 'ASUS', 'Lenovo', 'HP', 'Acer', 'MSI', 'Dell', 'HP', 'Apple'],
            'model': ['Inspiron 15', 'Pavilion x360', 'Legion 5 Pro', 'ROG Strix G16', 'MacBook Air M1', 'MacBook Pro M2', 'XPS 13 OLED', 'Vivobook 14', 'ThinkPad E14', 'Envy x360', 'Nitro 5', 'Cyborg 15', 'Inspiron 14', 'Victus 16', 'MacBook Air M3'],
            'ram_gb': [8, 16, 16, 32, 8, 16, 16, 8, 16, 16, 8, 16, 8, 16, 16],
            'storage_gb': [512, 512, 1024, 1024, 256, 512, 1024, 512, 512, 512, 512, 512, 512, 1024, 512],
            'storage_type': ['SSD', 'SSD', 'SSD', 'SSD', 'SSD', 'SSD', 'SSD', 'SSD', 'SSD', 'SSD', 'SSD', 'SSD', 'SSD', 'SSD', 'SSD'],
            'processor': ['Intel i5', 'Intel i7', 'Ryzen 7', 'Ryzen 9', 'Apple M1', 'Apple M2', 'Intel i7', 'Ryzen 5', 'Intel i5', 'Ryzen 7', 'Intel i5', 'Intel i7', 'Intel i3', 'Ryzen 5', 'Apple M3'],
            'price_inr': [52500, 74900, 118000, 164900, 79900, 149900, 139900, 44500, 68000, 86000, 62000, 89000, 39900, 71000, 114900],
            'screen_size_inch': [15.6, 14.0, 16.0, 16.0, 13.3, 14.2, 13.4, 14.0, 14.0, 13.3, 15.6, 15.6, 14.0, 16.1, 13.6],
            'gpu': ['Intel Iris Xe', 'Intel Iris Xe', 'RTX 4060', 'RTX 4070', 'Apple 7-Core', 'Apple 10-Core', 'Intel Iris Xe', 'AMD Radeon', 'Intel UHD', 'AMD Radeon', 'RTX 3050', 'RTX 4050', 'Intel UHD', 'RTX 2050', 'Apple 10-Core'],
            'in_stock': [True, True, True, True, True, True, False, True, True, True, True, True, True, True, True]
        }
        pd.DataFrame(mock_data).to_csv(DATASET_PATH, index=False)

create_mock_csv_if_missing()

# Initialize state controllers
if 'chatbot' not in st.session_state:
    st.session_state.chatbot = RuleBasedLaptopChatbot(DATASET_PATH)

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = [
        {
            "role": "assistant",
            "text": "🤖 Welcome to the **Smart Laptop Recommendation Portal**! Ask me anything regarding brands, components, pricing, or gaming benchmarks. Let's find your perfect setup! ✨",
            "data": pd.DataFrame(),
            "type": "greeting"
        }
    ]

if 'laptop_of_the_day' not in st.session_state:
    st.session_state.laptop_of_the_day = helpers.laptop_of_the_day(st.session_state.chatbot.df)

# Sidebar System Navigation controls
with st.sidebar:
    st.title("⚙️ Hardware Engine Portal")
    st.markdown("---")
    
    # Render the curated Laptop of the Day card
    st.subheader("🌟 Choice Machine of the Day")
    lotd = st.session_state.laptop_of_the_day
    if lotd is not None:
        st.markdown(f"""
        <div class="rec-card">
            <h3 style='margin-top:0;'>{lotd['brand']} {lotd['model']}</h3>
            <p>💰 <b>Price:</b> ₹{lotd['price_inr']:,}</p>
            <p>🎛 <b>CPU:</b> {lotd['processor']}</p>
            <p>⚡ <b>RAM:</b> {lotd['ram_gb']} GB</p>
            <p>⭐ <b>Rating:</b> {helpers.get_rating(lotd)}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 💡 Quick Search Examples")
    st.caption("• `Dell laptops under 60000`")
    st.caption("• `Best gaming laptop`")
    st.caption("• `compare MacBook Air M1 vs XPS 13`")
    st.caption("• `High performance 16GB RAM models`")
    st.caption("• `surprise me`")
    
    if st.button("🗑 Clear Chat History", use_container_width=True):
        st.session_state.chat_history = [st.session_state.chat_history[0]]
        st.rerun()

# Application Title Workspace Banner Layout
st.title("🚀 Smart Laptop Recommendation Consultant")
st.subheader("Rule-Based High-Fidelity Query Processing Engine")
st.markdown("---")

# Render active runtime chat history pools
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["text"])
        
        # Render tabular arrays if loaded into payload
        if "data" in message and not message["data"].empty:
            if message["type"] == "comparison":
                st.dataframe(helpers.prepare_dataframe(message["data"]), use_container_width=True)
            else:
                # Render comprehensive cards alongside structural reporting tables
                st.dataframe(helpers.prepare_dataframe(message["data"]), use_container_width=True)
                
                st.markdown("### 📋 Recommendation Breakdown Profile")
                for _, row in message["data"].head(2).iterrows():
                    score = helpers.calculate_score(row)
                    match_pct = helpers.match_percentage(score)
                    stars = helpers.get_rating(row)
                    reasons = helpers.recommendation_reason(row)
                    
                    # Output individual recommendation cards
                    with st.container():
                        st.markdown(f"""
                        <div class="rec-card">
                            <h4 style='margin:0 0 10px 0; color:#4fecf7;'>🎯 {row['brand']} {row['model']}</h4>
                            <p style='margin:2px 0;'>🏆 <b>Match Precision Index:</b> <span style='color:#00ff88; font-weight:bold;'>{match_pct}%</span> | <b>Hardware Quality:</b> {stars}</p>
                            <p style='margin:2px 0;'>💵 <b>Price Evaluation:</b> ₹{row['price_inr']:,} INR</p>
                            <p style='margin:2px 0; font-size: 0.9em; color:#8b949e;'>💾 {row['ram_gb']}GB RAM | {row['storage_gb']}GB {row['storage_type']} | {row['processor']} | {row['gpu']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Display structural textual analysis tags safely
                        for r in reasons:
                            st.markdown(f"<span style='color:#00ff88; font-weight:bold;'>{r}</span>", unsafe_allow_html=True)

# Main Streamlit Chat Input Processing Layer
if user_input := st.chat_input("Ask me about brands, budgets, or hardware specifications..."):
    
    # Instantly project user chat message to UI
    with st.chat_message("user"):
        st.markdown(user_input)
        
    st.session_state.chat_history.append({"role": "user", "text": user_input, "data": pd.DataFrame(), "type": "text"})
    
    # Process responses under a processing spinner container layout block
    with st.chat_message("assistant"):
        text_placeholder = st.empty()
        
        with st.spinner("Parsing query signatures against hardware indices..."):
            reply_payload = st.session_state.chatbot.process_query(user_input)
            
            # Apply progressive typing layout to simulate real-time analytics delivery
            helpers.typing_effect(reply_payload["text"], container=text_placeholder, delay=0.005)
            
            # Contextually append tracking tables or analytical graphs if needed
            if not reply_payload["data"].empty:
                if reply_payload["type"] == "comparison":
                    st.dataframe(helpers.prepare_dataframe(reply_payload["data"]), use_container_width=True)
                else:
                    st.dataframe(helpers.prepare_dataframe(reply_payload["data"]), use_container_width=True)
                    st.markdown("### 📋 Recommendation Breakdown Profile")
                    
                    # Cap visual recommendations to top 2 configurations to prevent layout bloat
                    for _, row in reply_payload["data"].head(2).iterrows():
                        score = helpers.calculate_score(row)
                        match_pct = helpers.match_percentage(score)
                        stars = helpers.get_rating(row)
                        reasons = helpers.recommendation_reason(row)
                        
                        with st.container():
                            st.markdown(f"""
                            <div class="rec-card">
                                <h4 style='margin:0 0 10px 0; color:#4fecf7;'>🎯 {row['brand']} {row['model']}</h4>
                                <p style='margin:2px 0;'>🏆 <b>Match Precision Index:</b> <span style='color:#00ff88; font-weight:bold;'>{match_pct}%</span> | <b>Hardware Quality:</b> {stars}</p>
                                <p style='margin:2px 0;'>💵 <b>Price Evaluation:</b> ₹{row['price_inr']:,} INR</p>
                                <p style='margin:2px 0; font-size: 0.9em; color:#8b949e;'>💾 {row['ram_gb']}GB RAM | {row['storage_gb']}GB {row['storage_type']} | {row['processor']} | {row['gpu']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            for r in reasons:
                                st.markdown(f"<span style='color:#00ff88; font-weight:bold;'>{r}</span>", unsafe_allow_html=True)
                                
        # Commit generated state payload directly into persistent global history tracker
        st.session_state.chat_history.append({
            "role": "assistant",
            "text": reply_payload["text"],
            "data": reply_payload["data"],
            "type": reply_payload["type"]
        })
