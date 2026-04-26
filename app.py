import streamlit as st
import json
import time
import random
import pandas as pd
import re
import google.generativeai as genai

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Catalyst Scout AI", page_icon="🤖", layout="wide")

# --- LOAD LOCAL DATABASE ---
@st.cache_data
def load_data():
    try:
        with open("candidates.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Error: 'candidates.json' not found in the directory.")
        return []

all_candidates = load_data()

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

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.header("⚙️ Agent Configuration")
    api_key = st.text_input("Gemini API Key:", type="password")
    demo_mode = st.toggle("Enable Demo Mode (Local Heuristics)", value=False, help="Bypass API for presentations.")
    
    if api_key:
        genai.configure(api_key=api_key)

st.title("🤖 Catalyst Scout AI")
st.markdown("**AI-Powered Talent Scouting & Engagement Pipeline**")

# --- UI INPUT ---
st.subheader("1. Input Job Description")
jd = st.text_area("Paste the Job Description here:", height=150)

col1, col2 = st.columns([1, 2])
with col1:
    num_to_screen = st.slider("Select batch size to screen:", min_value=1, max_value=len(all_candidates), value=min(5, len(all_candidates)))
    sample_strategy = st.radio("Candidate Selection:", options=["Random", "From Start", "From End"], horizontal=True)

# --- PIPELINE EXECUTION ---
if st.button("Start AI Agent Pipeline"):
    if not jd.strip():
        st.warning("Action Required: Please paste a Job Description to initiate the scouting pipeline.")
    elif not demo_mode and not api_key:
        st.error("Authentication Required: Please enter your Gemini API Key in the sidebar or enable Demo Mode.")
    else:
        # --- 1. DOMAIN DISCOVERY FILTER & EXPERIENCE GATEKEEPER ---
        jd_lower = jd.lower()
        tech_keywords = [
            'developer', 'engineer', 'cloud', 'rpa', 'automation', 'it', 
            'data', 'software', 'ai', 'tech', 'programmer', 'scripting',
            'python', 'uipath', 'aws', 'azure', 'bot', 'code', 'database',
            'network', 'security', 'machine learning', 'frontend', 'backend'
        ]
        
        # 1. Determine if Technical using whole-word boundaries
        is_tech_jd = any(re.search(rf'\b{re.escape(kw)}\b', jd_lower) for kw in tech_keywords)
        
        # 2. Extract required experience from JD (Finds ALL matches and takes the highest)
        exp_matches = re.findall(r'(\d+)\s*\+?\s*(?:year|yr)s?', jd_lower)
        required_exp = max([int(m) for m in exp_matches]) if exp_matches else 0
        
        # UI Feature: Show the recruiter what the Gatekeeper is doing
        if required_exp > 0:
            st.info(f"🛡️ Gatekeeper Active: Strictly enforcing a minimum of {required_exp} years of experience.")
        
        # Filter the database BEFORE the AI runs
        domain_candidates = []
        for c in all_candidates:
            # Check candidate domain
            c_text = (c['title'] + " " + c['skills']).lower()
            is_tech_candidate = any(re.search(rf'\b{re.escape(kw)}\b', c_text) for kw in tech_keywords)
            
            # Extract candidate's numerical experience from their JSON
            c_exp_str = str(c.get('experience', '0'))
            c_exp_match = re.search(r'(\d+)', c_exp_str)
            c_exp = int(c_exp_match.group(1)) if c_exp_match else 0
            
            # Group them by domain AND enforce the experience threshold
            if (is_tech_jd and is_tech_candidate) or (not is_tech_jd and not is_tech_candidate):
                if c_exp >= required_exp:
                    domain_candidates.append(c)

        # --- Safety Check: Did the Gatekeeper filter EVERYONE out? ---
        if not domain_candidates:
            st.error(f"Discovery Failed: No candidates found matching this domain with {required_exp}+ years of experience.")
        else:
            # --- 2. APPLY SELECTION STRATEGY ---
            actual_num_to_screen = min(num_to_screen, len(domain_candidates))
            
            if sample_strategy == "From Start":
                candidates_to_screen = domain_candidates[:actual_num_to_screen]
            elif sample_strategy == "From End":
                candidates_to_screen = domain_candidates[-actual_num_to_screen:]
            else:
                candidates_to_screen = random.sample(domain_candidates, actual_num_to_screen)
            
            model_name = "Local Heuristics" if demo_mode else "Gemini Pro/Flash API"
            
            with st.spinner(f"Gatekeeper passed {len(domain_candidates)} profiles. Scouting top {actual_num_to_screen} using {model_name}..."):
                results = []
                if not demo_mode:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                
                # --- THE AGENT LOOP ---
                for candidate in candidates_to_screen:
                    if demo_mode:
                        # --- LOCAL HEURISTIC ENGINE ---
                        jd_words = set(re.findall(r'\b\w+\b', jd_lower))
                        cand_words = set(re.findall(r'\b\w+\b', (candidate['title'] + " " + candidate['skills']).lower()))
                        
                        if len(jd_words.intersection(cand_words)) > 0:
                            match_score = random.randint(85, 98)
                            match_reason = "Strong keyword overlap detected in profile."
                        else:
                            match_score = random.randint(10, 45)
                            match_reason = "Minimal keyword overlap with JD requirements."
                            
                        vibe_lower = candidate.get('vibe', '').lower()
                        if any(w in vibe_lower for w in ['desperate', 'motivated', 'startup', 'active']):
                            interest_score = random.randint(88, 99)
                        else:
                            interest_score = random.randint(40, 65)
                            
                        simulated_reply = "I would love to learn more about this opportunity."
                        interest_reason = "Simulated based on local vibe parameter."
                        time.sleep(0.5)
                        
                    else:
                        # --- LIVE API ENGINE ---
                        # 1. Define the Match Prompt
                        match_prompt = f"""
                        You are an AI hiring evaluator.
                        Task: Evaluate how well the candidate matches the job description.
                        Inputs:
                        Job Description: {jd}
                        Candidate Title: {candidate['title']}
                        Candidate Skills: {candidate['skills']}
                        Candidate Experience: {candidate.get('experience', 'Not specified')}
                        Instructions:
                        - Return a match score between 0 and 100 (integer only).
                        - Base the score on skill overlap, relevance of title, and years of experience.
                        - Keep reasoning concise (max 15 words).
                        Output format (strict, no extra text):
                        Score: <number>
                        Reason: <short explanation>
                        """
                        
                        try:
                            match_response = model.generate_content(match_prompt).text.replace("**", "").replace("*", "")
                            match_score = int([line for line in match_response.split('\n') if "Score:" in line][0].replace("Score:", "").strip())
                            match_reason = [line for line in match_response.split('\n') if "Reason:" in line][0].replace("Reason:", "").strip()
                        except Exception as e:
                            match_score = 0
                            match_reason = "API Error parsing score."

                        # 2. Define the Engagement Prompt (Requires match_score to exist)
                        engagement_prompt = f"""
                        You are an AI recruiter.
                        Task: Simulate a candidate's reply to outreach.
                        Inputs:
                        Candidate Name: {candidate['name']}
                        Candidate Vibe/Status: {candidate['vibe']}
                        Match Score: {match_score}
                        Instructions:
                        - Simulate a short, realistic email reply based solely on their vibe.
                        - Return an Interest Score between 0 and 100 (integer only).
                        - Keep reasoning concise (max 15 words).
                        Output format (strict, no extra text):
                        Reply: <simulated message>
                        Interest: <number>
                        Reasoning: <short explanation>
                        """
                        
                        try:
                            engage_response = model.generate_content(engagement_prompt).text.replace("**", "").replace("*", "")
                            simulated_reply = [line for line in engage_response.split('\n') if "Reply:" in line][0].replace("Reply:", "").strip()
                            interest_score = int([line for line in engage_response.split('\n') if "Interest:" in line][0].replace("Interest:", "").strip())
                            interest_reason = [line for line in engage_response.split('\n') if "Reasoning:" in line][0].replace("Reasoning:", "").strip()
                        except Exception as e:
                            interest_score = 0
                            simulated_reply = "Simulation failed."
                            interest_reason = "API Error parsing interest."
                        
                        time.sleep(5) # Avoid API rate limit
                        
                    # Append candidate data to results
                    results.append({
                        "Candidate": candidate['name'],
                        "Title": candidate['title'],
                        "Experience": candidate.get('experience', 'N/A'),
                        "Match %": match_score,
                        "Match Reason": match_reason,
                        "Interest %": interest_score,
                        "Simulated Chat": simulated_reply,
                        "Interest Reason": interest_reason
                    })
                
                # --- FINAL OUTPUT GENERATION ---
                st.success("Pipeline Execution Complete!")
                st.subheader("📊 Ranked Candidate Shortlist")
                
                df = pd.DataFrame(results)
                
                # Multi-Tier Sorting Logic
                df = df.sort_values(by=["Match %", "Interest %"], ascending=[False, False])
                df.index = range(1, len(df) + 1)
                
                st.dataframe(df, use_container_width=True)
