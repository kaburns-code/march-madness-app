import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import random

# --- 1. Load the Data ---
@st.cache_data
def load_data():
    df = pd.read_csv('data.csv')
    df['R32'] = df['R32'] / 100
    try:
        inj_df = pd.read_csv('injuries.csv')
    except:
        inj_df = pd.DataFrame(columns=['Player', 'Team', 'Pos', 'Injury', 'Status', 'Value', 'Injury Weight'])
    return df, inj_df

df, injuries_df = load_data()

# --- 2. Session State (Tournament Memory) ---
if 'team_a' not in st.session_state:
    st.session_state.team_a = df['Team'].sort_values().iloc[0]
if 'team_b' not in st.session_state:
    st.session_state.team_b = df['Team'].sort_values().iloc[1]
if 'scroll_to_top' not in st.session_state:
    st.session_state.scroll_to_top = False
if 'bracket_winners' not in st.session_state:
    st.session_state.bracket_winners = {}

def set_matchup(team1, team2):
    st.session_state.team_a = team1
    st.session_state.team_b = team2
    st.session_state.scroll_to_top = True

def advance_team(team_name, slot_id):
    st.session_state.bracket_winners[slot_id] = team_name
    st.toast(f"✅ {team_name} advanced!")

# --- 3. Scroll Hack ---
st.markdown("<div id='top'></div>", unsafe_allow_html=True)
if st.session_state.scroll_to_top:
    components.html("<script>window.parent.location.hash = 'top';</script>", height=0)
    st.session_state.scroll_to_top = False

# --- 4. Main Predictor UI ---
st.title("🏀 Tournament Master")
col1, col2 = st.columns(2)
with col1:
    team_a_name = st.selectbox("Team A", df['Team'].sort_values(), key='team_a')
with col2:
    team_b_name = st.selectbox("Team B", df['Team'].sort_values(), key='team_b')

# --- 5. Prediction Logic ---
if team_a_name and team_b_name:
    team_a = df[df['Team'] == team_a_name].iloc[0]
    team_b = df[df['Team'] == team_b_name].iloc[0]
    
    total_r32 = team_a['R32'] + team_b['R32']
    base_prob_a = team_a['R32'] / total_r32 if total_r32 > 0 else 0.5
    
    exp_a = (17 - team_a['Seed']) / 16
    exp_b = (17 - team_b['Seed']) / 16
    modifier = ((team_a['R32'] - exp_a) - (team_b['R32'] - exp_b)) * 0.20
    
    def get_penalty(name):
        relevant = injuries_df[injuries_df['Team'] == name]
        return pd.to_numeric(relevant['Injury Weight'], errors='coerce').sum()

    final_prob_a = max(0.01, min(0.99, base_prob_a + modifier - get_penalty(team_a_name) + get_penalty(team_b_name)))
    final_prob_b = 1 - final_prob_a
    
    st.divider()
    pred_winner = team_a_name if final_prob_a > 0.5 else team_b_name
    st.success(f"**Predicted Winner:** {pred_winner} ({max(final_prob_a, final_prob_b)*100:.1f}%)")
    
    if team_a['Seed'] != team_b['Seed']:
        underdog = team_a_name if team_a['Seed'] > team_b['Seed'] else team_b_name
        u_p = final_prob_a if underdog == team_a_name else final_prob_b
        st.info(f"**Upset Watch:** {underdog} has a **{u_p*100:.1f}%** chance.")

# --- 6. Round of 64 Grid ---
st.divider()
st.header("🏆 Round of 64")
regions = df['Region'].dropna().unique()
tabs = st.tabs([str(r) for r in regions])
matchups = [
    (1, 16, "Pod_A"), (8, 9, "Pod_A"),
    (5, 12, "Pod_B"), (4, 13, "Pod_B"),
    (6, 11, "Pod_C"), (3, 14, "Pod_C"),
    (7, 10, "Pod_D"), (2, 15, "Pod_D")
]

for i, region in enumerate(regions):
    with tabs[i]:
        reg_df = df[df['Region'] == region]
        for s1, s2, pod in matchups:
            # FIX: Both now use reg_df correctly
            t1 = reg_df[reg_df['Seed'] == s1]
            t2 = reg_df[reg_df['Seed'] == s2]
            
            if not t1.empty and not t2.empty:
                n1, n2 = t1.iloc[0]['Team'], t2.iloc[0]['Team']
                c_btn, c_adv = st.columns([3, 1])
                with c_btn:
                    st.button(f"🏀 {s1} {n1} vs {s2} {n2}", key=f"bt_{region}_{s1}", on_click=set_matchup, args=(n1, n2), use_container_width=True)
                with c_adv:
                    winner_pick = st.selectbox("Winner", [n1, n2], key=f"sel_{region}_{s1}", label_visibility="collapsed")
                    if st.button("➕", key=f"adv_{region}_{s1}"):
                        advance_team(winner_pick, f"{region}_{pod}_{s1}")

# --- 7. Round of 32 Pods ---
st.divider()
st.header("🧬 Your Custom Round of 32")
for region in regions:
    with st.expander(f"Region: {region}"):
        # Check Pod A (1/16 winner vs 8/9 winner)
        w1 = st.session_state.bracket_winners.get(f"{region}_Pod_A_1")
        w8 = st.session_state.bracket_winners.get(f"{region}_Pod_A_8")
        if w1 and w8:
            st.button(f"🔥 Analyze: {w1} vs {w8}", key=f"r32_{region}_A", on_click=set_matchup, args=(w1, w8))
        
        # Check Pod B (5/12 winner vs 4/13 winner)
        w5 = st.session_state.bracket_winners.get(f"{region}_Pod_B_5")
        w4 = st.session_state.bracket_winners.get(f"{region}_Pod_B_4")
        if w5 and w4:
            st.button(f"🔥 Analyze: {w5} vs {w4}", key=f"r32_{region}_B", on_click=set_matchup, args=(w5, w4))
            
        # Check Pod C (6/11 winner vs 3/14 winner)
        w6 = st.session_state.bracket_winners.get(f"{region}_Pod_C_6")
        w3 = st.session_state.bracket_winners.get(f"{region}_Pod_C_3")
        if w6 and w3:
            st.button(f"🔥 Analyze: {w6} vs {w3}", key=f"r32_{region}_C", on_click=set_matchup, args=(w6, w3))

        # Check Pod D (7/10 winner vs 2/15 winner)
        w7 = st.session_state.bracket_winners.get(f"{region}_Pod_D_7")
        w2 = st.session_state.bracket_winners.get(f"{region}_Pod_D_2")
        if w7 and w2:
            st.button(f"🔥 Analyze: {w7} vs {w2}", key=f"r32_{region}_D", on_click=set_matchup, args=(w7, w2))
