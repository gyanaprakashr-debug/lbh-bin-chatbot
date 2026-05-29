import streamlit as st
import math
import re
import os
import base64

# Set page config
st.set_page_config(page_title="LBH Bin Chatbot", page_icon="📦", layout="centered")

# Path updated for Cloud Deployment (Both files must be in the same GitHub folder)
LOGO_PATH = "L&D Logo.png"

# Default Sample CSV Data (Fallback)
INITIAL_CSV = """Outlier FSN as per system,Priority,WID ( collected ),L (cm),B (cm),H (cm),W (kg),Vertical,Volume(cc cm),Date of update
EDOGTYMYKZDUGZDX,P1 FSN,23,23,31,15,16399,16 May 2025
EDOGWFXCGE7FJ5P2,P1 FSN,23,23,31,15,16399,16 May 2025
EDOFAA8TMQGYYGTN,P1 FSN,22,22,31,15,15004,16 May 2025
EDOFXYMCPBFUN4WB,P1 FSN,22,22,31,15,15004,16 May 2025
EDOFAA8TB7QZNWFY,Outlier FSN - P0,22.5,23,32,14,16560,16 May 2025
EDOGTYMYF7RRAZCX,P1 FSN,23,23,31,14,16399,16 May 2025
EDOFXNPHN65S4MUY,29,18,39.5,13.65,20619,12 June 2025
MLKG74TNHYU4CHEB,Outlier FSN - P0,39,21,21,13.44,17199,16 May 2025
MLKG74TNW42RUDNY,50,20.5,20,13.4,20500,20 June 2025
RICGD45YX2Y2QSG4,Outlier FSN - P0,XIKCTNT,42,31.5,10,10.8,13230,16 January 2026
FLRGPYXQGGY8YY67,Outlier FSN - P0,51,35,10,10.5,17850,16 May 2025
MLKEUHKGZBVZNFCW,P1 FSN,4.5,3.5,10.5,0.21,165,23 May 2025
FLREUC5PGWMYACW2,Outlier FSN - P0,XIO2633,47.5,33.5,11,10.198,17504,16 January 2026
RICGQP3FSARQZYG5,P1 FSN,XIO8BSV,47.2,32.3,11.1,10.15,16923,16 January 2026
FLRFFZRTD66QAJHB,P1 FSN,XIOAWJS,53,35,7,10.14,12985,16 January 2026
RICGQAM77HQR8DHN,P1 FSN,XINWFY8,44,33,9.5,10.128,13794,16 January 2026
RICGPZHXMHHHWUBF,Outlier FSN - P0,XIO920E,49,35,7,10.12,12005,16 January 2026
RICF576PHBFGZKSV,Outlier FSN - P0,XINQITR,49.4,33,7.5,10.12,12227,16 January 2026
FLRGPFZRBEA3Z8DP,Outlier FSN - P0,XIO8TVX,54,39,7,10.12,14742,16 January 2026
RICF576PK3Y9YPUH,P1 FSN,42,35,12,10.1,17640,16 May 2025
RICGQAM7REGGAGJJ,P1 FSN,42,35,12,10.1,17640,16 May 2025"""

def parse_csv(csv_str):
    """Advanced parser with aggressive text cleaning to handle invisible characters."""
    inventory = {}
    lines = csv_str.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.lower().startswith('outlier') or line.lower().startswith('master') or line.startswith('```'):
            continue
            
        parts = re.split(r'[,\t]', line)
        
        fsn = None
        for p in parts:
            # AGGRESSIVE CLEANING: Strip absolutely everything except letters and numbers
            clean_p = re.sub(r'[^A-Z0-9]', '', p.upper())
            
            # Smart FSN Finder: Find the first long alphanumeric string
            if len(clean_p) >= 10 and not clean_p.isnumeric():
                fsn = clean_p
                break
                
        if not fsn:
            continue
            
        nums = []
        for p in parts:
            clean_num_str = p.strip(' \t"\'\r\n')
            if clean_num_str:
                try:
                    val = float(clean_num_str)
                    nums.append(val)
                except ValueError:
                    continue
                    
        if len(nums) >= 3:
            # Assume the first 3 numbers found are the dimensions
            inventory[fsn] = {"l": nums[0], "b": nums[1], "h": nums[2], "valid": True}
        else:
            # FSN exists, but it doesn't have 3 valid numbers for dimensions
            inventory[fsn] = {"valid": False}
            
    return inventory

def calculate_max_fit(item, bin_dims, num_fsns=1):
    """Calculates optimal 3D fitting and optionally divides capacity for mixed packing."""
    l, b, h = item['l'], item['b'], item['h']
    bin_l, bin_b, bin_h = bin_dims['l'], bin_dims['b'], bin_dims['h']
    
    orientations = [
        (l, b, h), (l, h, b), (b, l, h),
        (b, h, l), (h, l, b), (h, b, l)
    ]
    
    max_qty_full_bin = 0
    best_orientation = None
    
    for ori in orientations:
        qty_l = math.floor(bin_l / ori[0])
        qty_b = math.floor(bin_b / ori[1])
        qty_h = math.floor(bin_h / ori[2])
        total = qty_l * qty_b * qty_h
        
        if total > max_qty_full_bin:
            max_qty_full_bin = total
            best_orientation = ori
            
    # Divide the total bin capacity by the number of different FSNs sharing the bin
    allocated_qty = math.floor(max_qty_full_bin / num_fsns)
    
    return allocated_qty, best_orientation

# --- UI Setup ---

# Sidebar for Settings
with st.sidebar:
    # Add Logo to Sidebar
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, use_container_width=True)
        st.markdown("---")
    else:
        st.warning(f"⚠️ Logo not found!\nPlease make sure `{LOGO_PATH}` is uploaded alongside your app.py file.")
        st.markdown("---")
        
    st.header("⚙️ Settings")
    st.subheader("Bin Dimensions (cm)")
    
    col1, col2, col3 = st.columns(3)
    bin_l = col1.number_input("Length", min_value=1.0, value=35.0, step=1.0)
    bin_b = col2.number_input("Breadth", min_value=1.0, value=42.0, step=1.0)
    bin_h = col3.number_input("Height", min_value=1.0, value=29.0, step=1.0)
    bin_dims = {"l": bin_l, "b": bin_b, "h": bin_h}
    
    st.markdown("---")
    st.subheader("Mixed Packing Configuration")
    num_fsns = st.number_input(
        "No. of FSNs sharing the bin", 
        min_value=1, 
        value=1, 
        step=1,
        help="If you plan to mix multiple FSNs in one bin, this divides the total volume capacity fairly among them."
    )
    
    st.markdown("---")
    st.subheader("Database Upload")
    
    # NEW: File Uploader instead of text area
    uploaded_file = st.file_uploader("Upload Master LBH (CSV file)", type=["csv"])

    # ADDED COPYRIGHT
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: gray; font-size: 13px; font-weight: bold;'>build by Gyana Prakash Rout</div>", unsafe_allow_html=True)

# Determine which data to use
if uploaded_file is not None:
    try:
        # Read the uploaded file as text
        csv_string = uploaded_file.getvalue().decode("utf-8")
        inventory = parse_csv(csv_string)
        st.sidebar.success(f"✅ Successfully loaded {len(inventory)} items from file!")
    except Exception as e:
        st.sidebar.error("❌ Error reading file. Please ensure it is a valid CSV.")
        inventory = parse_csv(INITIAL_CSV) # Fallback if file is corrupted
else:
    st.sidebar.info("ℹ️ Using default sample data. Upload your CSV to check real FSNs.")
    inventory = parse_csv(INITIAL_CSV)


# --- Main Chat Interface - Sticky Constant Header ---

# Generate base64 encoding for the local image to embed directly in HTML
encoded_logo = ""
if os.path.exists(LOGO_PATH):
    try:
        with open(LOGO_PATH, "rb") as image_file:
            encoded_logo = base64.b64encode(image_file.read()).decode()
    except Exception:
        pass

# CSS and HTML combined to create the sticky header
header_html = f"""
<style>
.sticky-header {{
    position: sticky;
    top: 0;
    background-color: #ffffff; /* Fallback for light mode */
    z-index: 999;
    padding: 15px 0px 10px 0px;
    text-align: center;
    border-bottom: 2px solid rgba(128, 128, 128, 0.2);
    margin-bottom: 1rem;
}}
/* Dark mode compatibility */
@media (prefers-color-scheme: dark) {{
    .sticky-header {{
        background-color: #0e1117; 
    }}
}}
</style>
<div class="sticky-header">
"""

# Inject the logo if it exists
if encoded_logo:
    header_html += f'<img src="data:image/png;base64,{encoded_logo}" style="max-height: 80px; margin-bottom: 10px;"><br>'

# Welcome message and dynamic configuration specs
header_html += '<h2 style="margin: 0; padding: 0;">📦 Welcome to LBH Bin Chatbot</h2>'

config_text = f"Bin Size: {bin_l}x{bin_b}x{bin_h} cm"
if num_fsns > 1:
    config_text += f" | Mixed Mode: {num_fsns} FSNs/Bin"

header_html += f'<p style="color: gray; margin-top: 5px; font-size: 14px;">{config_text}</p>'
header_html += '</div>'

# Render the sticky header
st.markdown(header_html, unsafe_allow_html=True)


# Initialize chat history
if "messages" not in st.session_state:
    welcome_msg = f"👋 Hello! I am your **LBH Bin Chatbot**.\n\nI currently have **{len(inventory)}** products loaded in my memory.\n\nSend me an **FSN** (e.g., `EDOGTYMYKZDUGZDX`) or multiple FSNs separated by commas, and I'll compute the maximum quantity that can be placed in your bin."
    st.session_state.messages = [{"role": "assistant", "content": welcome_msg}]

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("Type an FSN here..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process the input
    words = re.split(r'[\s,]+', prompt.strip())
    responses = []
    valid_checks = 0
    
    for word in words:
        # AGGRESSIVE CLEANING: Strip absolutely everything except letters and numbers
        fsn = re.sub(r'[^A-Z0-9]', '', word.upper())
        
        if len(fsn) >= 5:
            valid_checks += 1
            if fsn in inventory:
                item = inventory[fsn]
                
                # Check if dimensions were missing
                if not item.get("valid", True):
                    responses.append(f"⚠️ **{fsn}**: Found in database, but **dimensions (L, B, or H) are missing/blank** in your uploaded CSV!")
                    continue
                    
                max_qty, best_ori = calculate_max_fit(item, bin_dims, num_fsns)
                
                # Dynamic label depending on mixed mode or standard mode
                qty_label = "Allocated Fit Quantity (Mixed)" if num_fsns > 1 else "Max Fit Quantity"
                
                if max_qty > 0:
                    best_l, best_b, best_h = best_ori
                    resp = (f"**📦 {fsn}**\n\n"
                            f"Item Dims: {item['l']} x {item['b']} x {item['h']} cm\n\n"
                            f"✅ **{qty_label}: {max_qty}** \n"
                            f"*(Optimal orientation: {best_l}x{best_b}x{best_h} cm)*")
                else:
                    resp = (f"**📦 {fsn}**\n\n"
                            f"Item Dims: {item['l']} x {item['b']} x {item['h']} cm\n\n"
                            f"⚠️ **Max Quantity: 0** \n"
                            f"*(Item is larger than the space allocated for it)*")
                responses.append(resp)
            else:
                responses.append(f"❌ **{fsn}**: Not found in the database. (Make sure you uploaded the latest CSV)")
                
    bot_response = "\n\n---\n\n".join(responses) if valid_checks > 0 else "Please send a valid FSN to check quantities."

    # Display assistant response
    with st.chat_message("assistant"):
        st.markdown(bot_response)
        
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": bot_response})