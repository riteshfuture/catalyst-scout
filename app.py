import streamlit as st
import google.generativeai as genai
import pandas as pd
import time
import json
import random
import string

# --- SETUP ---
st.set_page_config(page_title="Catalyst Scout AI", page_icon="🎯", layout="wide")
st.title("🎯 Catalyst AI: Talent Scouting & Engagement Agent")

# --- CUSTOM FIGMA-STYLE UI INJECTION ---
st.markdown("""
<style>
    /* Dark Cloud/Tech Background with Dot Matrix */
    .stApp {
        background-color: #0a0e17;
        background-image: radial-gradient(rgba(0, 201, 255, 0.15) 1px, transparent 1px);
        background-size: 25px 25px;
    }
    
    /* Gradient App Title */
    h1 {
        background: -webkit-linear-gradient(45deg, #00C9FF, #92FE9D);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        padding-bottom: 10px;
    }
    
    /* Sleek Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.95);
        border-right: 1px solid rgba(0, 201, 255, 0.2);
    }
    
    /* Premium Glowing Button */
    .stButton>button {
        background: linear-gradient(90deg, #4776E6 0%, #8E54E9 100%);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.6rem 1.2rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(142, 84, 233, 0.4);
        width: 100%;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(142, 84, 233, 0.7);
        border: none;
        color: white;
    }

    /* Glassmorphism Input Areas */
    .stTextArea textarea {
        background-color: rgba(15, 23, 42, 0.7) !important;
        border: 1px solid #334155 !important;
        color: #e2e8f0 !important;
        border-radius: 8px;
    }
    
    .stTextArea textarea:focus {
        border-color: #00C9FF !important;
        box-shadow: 0 0 12px rgba(0, 201, 255, 0.3) !important;
    }

    /* DataFrame Table Styling */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid rgba(0, 201, 255, 0.2);
    }
</style>
""", unsafe_allow_html=True)
# ---------------------------------------

st.sidebar.header("Agent Configuration")
api_key = st.sidebar.text_input("Enter Google Gemini API Key:", type="password")
# THE HACKATHON LIFESAVER: Demo Mode Toggle
demo_mode = st.sidebar.checkbox("Enable Demo Mode (Bypass API Limits)", value=True, help="Uses local heuristics for instant demo recording without API quotas.")

if not api_key and not demo_mode:
    st.warning("Please enter your API Key or enable Demo Mode in the sidebar to start.")
    st.stop()

if not demo_mode:
    genai.configure(api_key=api_key)
    @st.cache_resource
    def get_working_model():
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'flash' in m.name.lower(): 
                    return m.name
        return 'models/gemini-1.5-pro' 

    try:
        valid_model_name = get_working_model()
        model = genai.GenerativeModel(valid_model_name)
        st.sidebar.success(f"Connected to model: {valid_model_name}")
    except Exception as e:
        st.sidebar.error("Could not fetch models. Check your API key.")
        st.stop()
else:
    valid_model_name = "Local Heuristic Engine (Demo Mode)"
    st.sidebar.success("Demo Mode Active. API bypassed.")

# --- LOAD DATABASE ---
@st.cache_data
def load_candidates():
    try:
        with open("candidates.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Could not find candidates.json. Ensure it is uploaded to the repository.")
        st.stop()

all_candidates = load_candidates()
st.sidebar.info(f"Database loaded: {len(all_candidates)} total candidates available.")

# --- UI INPUT ---
st.subheader("1. Input Job Description")
jd = st.text_area("Paste the Job Description here:", height=150)

col1, col2 = st.columns([1, 2])
with col1:
    num_to_screen = st.slider("Select batch size to screen:", min_value=1, max_value=len(all_candidates), value=min(5, len(all_candidates)))
    # NEW: Selection Strategy Toggle
    sample_strategy = st.radio("Candidate Selection:", options=["Random", "From Start", "From End"], horizontal=True)

# --- PIPELINE EXECUTION ---
if st.button("Start AI Agent Pipeline"):
    if not jd.strip():
        st.warning("Action Required: Please paste a Job Description to initiate the scouting pipeline.")
    else:
        # --- 1. DOMAIN DISCOVERY FILTER ---
        jd_lower = jd.lower()
        tech_keywords = [
            'developer', 'engineer', 'cloud', 'rpa', 'automation', 'it', 
            'data', 'software', 'ai', 'tech', 'programmer', 'scripting',
            'python', 'uipath', 'aws', 'azure', 'bot', 'code', 'database',
            'network', 'security', 'machine learning', 'frontend', 'backend'
        ]
        
        # Determine if the pasted JD is Technical or Non-Technical
        is_tech_jd = any(kw in jd_lower for kw in tech_keywords)
        
        # Filter the database BEFORE the AI runs
        domain_candidates = []
        for c in all_candidates:
            # Check if the candidate's profile is technical
            c_text = (c['title'] + " " + c['skills']).lower()
            is_tech_candidate = any(kw in c_text for kw in tech_keywords)
            
            # Group them! Tech JDs only get Tech candidates. Non-Tech gets Non-Tech.
            if is_tech_jd and is_tech_candidate:
                domain_candidates.append(c)
            elif not is_tech_jd and not is_tech_candidate:
                domain_candidates.append(c)
                
        # Safety check in case the filter finds no one
        if not domain_candidates:
            st.error("Discovery Failed: No candidates in the database match this job category.")
        else:
            # --- 2. APPLY SELECTION STRATEGY ---
            actual_num_to_screen = min(num_to_screen, len(domain_candidates))
            
            if sample_strategy == "From Start":
                candidates_to_screen = domain_candidates[:actual_num_to_screen]
            elif sample_strategy == "From End":
                candidates_to_screen = domain_candidates[-actual_num_to_screen:]
            else:
                candidates_to_screen = random.sample(domain_candidates, actual_num_to_screen)
            
            with st.spinner(f"Agent discovered {len(domain_candidates)} potential profiles. Scouting top {actual_num_to_screen} using {valid_model_name}...") :
                results = []
                
                # --- THE AGENT LOOP ---
                # (Keep your existing loop code from here down!)
                
                # --- THE AGENT LOOP ---
                # (Keep your existing loop code from here down!)            
            # --- THE AGENT LOOP ---
            for candidate in candidates_to_screen:
                
                # --- THE BOUNCER (Global Pre-Check) ---
                # Clean punctuation so we only match exact whole words
                jd_clean = jd.translate(str.maketrans('', '', string.punctuation)).lower()
                jd_words = set(jd_clean.split())
                
                # Our strict list of required whole words
                tech_keywords = {'developer', 'engineer', 'cloud', 'rpa', 'automation', 'it', 'data', 'software', 'ai', 'tech', 'programmer', 'scripting'}
                is_tech_jd = bool(jd_words.intersection(tech_keywords))

                if not is_tech_jd:
                    # If it's a Retail or HR job, instantly reject. No API calls needed!
                    match_score = 0
                    match_reason = "Complete mismatch. Non-technical JD."
                    interest_score = 0
                    simulated_reply = "I believe you have the wrong person. My background is strictly in technical engineering."
                    interest_reason = "Candidate immediately rejected the irrelevant outreach."
                    time.sleep(0.5)
                    
                elif demo_mode:
                    # --- LOCAL DEMO ENGINE ---
                    time.sleep(0.8) 
                    skills_lower = candidate['skills'].lower()
                    
                    if "uipath" in skills_lower or "python" in skills_lower or "automation" in skills_lower:
                        match_score = random.randint(85, 98)
                        match_reason = f"Strong alignment. Candidate possesses key skills like {candidate['skills'].split(',')[0]} required for the automation workflows."
                    else:
                        match_score = random.randint(30, 55)
                        match_reason = f"Partial match. Lacks core automation stack experience, offering mostly {candidate['skills'].split(',')[0]}."

                    vibe_lower = candidate['vibe'].lower()
                    if "desperate" in vibe_lower or "motivated" in vibe_lower or "startup" in vibe_lower:
                        interest_score = random.randint(88, 99)
                        simulated_reply = "Thank you for reaching out! This role perfectly aligns with my current career goals. When can we chat?"
                        interest_reason = "Candidate is actively looking and highly receptive to new technical challenges."
                    elif "passive" in vibe_lower or "comfortable" in vibe_lower:
                        interest_score = random.randint(40, 65)
                        simulated_reply = "I'm currently happy where I am, but I'd be willing to look at the compensation package."
                        interest_reason = "Passive candidate. Requires significant financial incentive to consider leaving current role."
                    else:
                        interest_score = random.randint(70, 85)
                        simulated_reply = "Sounds interesting. Could you send over a bit more detail regarding the team structure?"
                        interest_reason = "Moderate interest based on professional curiosity; open to discussions."

                else:
                    # --- LIVE API ENGINE ---
                    
                    # 1. Define the Match Prompt
                    match_prompt = f"""
                    You are an AI hiring evaluator.

                    Task:
                    Evaluate how well the candidate matches the job description.

                    Inputs:
                    Job Description: {jd}
                    Candidate Title: {candidate['title']}
                    Candidate Skills: {candidate['skills']}
                    Candidate Experience: {candidate.get('experience', 'Not specified')}

                    Instructions:
                    - Return a match score between 0 and 100 (integer only).
                    - Base the score on skill overlap, relevance of title, years of experience, and overall alignment.
                    - Do not assume missing information.
                    - Keep reasoning concise (max 15 words).

                    Output format (strict, no extra text, no bolding):
                    Score: <number>
                    Reason: <short explanation>
                    """
                    
                    # 2. Ask Gemini for the Match Score FIRST
                    try:
                        match_response = model.generate_content(match_prompt).text.replace("**", "").replace("*", "")
                        match_score = int([line for line in match_response.split('\n') if "Score:" in line][0].replace("Score:", "").strip())
                        match_reason = [line for line in match_response.split('\n') if "Reason:" in line][0].replace("Reason:", "").strip()
                    except Exception as e:
                        match_score = 0
                        match_reason = f"API Error: {str(e)[:40]}"

                    # 3. NOW define the Engagement Prompt (match_score exists now!)
                    engagement_prompt = f"""
                    You are an AI recruiter.

                    Task:
                    Simulate a candidate's reply to an outreach message and calculate their interest level.

                    Inputs:
                    Candidate Name: {candidate['name']}
                    Candidate Vibe/Status: {candidate['vibe']}
                    Match Score: {match_score}

                    Instructions:
                    - Simulate a short, realistic email reply based solely on their vibe.
                    - Return an Interest Score between 0 and 100 (integer only).
                    - Keep reasoning concise (max 15 words).

                    Output format (strict, no extra text, no bolding):
                    Reply: <simulated message>
                    Interest: <number>
                    Reasoning: <short explanation>
                    """
                    
                    # 4. Ask Gemini for the Interest Score
                    try:
                        engage_response = model.generate_content(engagement_prompt).text.replace("**", "").replace("*", "")
                        simulated_reply = [line for line in engage_response.split('\n') if "Reply:" in line][0].replace("Reply:", "").strip()
                        interest_score = int([line for line in engage_response.split('\n') if "Interest:" in line][0].replace("Interest:", "").strip())
                        interest_reason = [line for line in engage_response.split('\n') if "Reasoning:" in line][0].replace("Reasoning:", "").strip()
                    except Exception as e:
                        interest_score = 0
                        simulated_reply = "Simulation failed."
                        interest_reason = f"API Error: {str(e)[:40]}"
                    
                    time.sleep(6)
                
                # Save the data
                results.append({
                    "Candidate": candidate['name'],
                    "Title": candidate['title'],
                    "Match %": match_score,
                    "Match Reason": match_reason,
                    "Interest %": interest_score,
                    "Simulated Chat": simulated_reply,
                    "Interest Reason": interest_reason 
                })
                
            # --- OUTPUT ---
            st.success("Scouting Complete!")
            st.subheader("2. Ranked Shortlist")
            
            df = pd.DataFrame(results)
            
            # Sort by scores, drop the jumbled index, and create a fresh one
            df = df.sort_values(by=["Match %", "Interest %"], ascending=[False, False]).reset_index(drop=True)
            
            # Shift the index to start at 1 instead of 0 for a natural ranking look
            df.index = df.index + 1 
            
            st.dataframe(df, use_container_width=True)
