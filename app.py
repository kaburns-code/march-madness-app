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

# This stores who won each specific slot (e.g., 'South_Pod_1' stores the winner of 1vs16)
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
st.title("🏀 March Madness Tournament Master")
col1, col2 = st.columns(2)
with col1:
    team_a_name = st.selectbox("Team A", df['Team'].sort_values(), key='team_a')
with col2:
    team_b_name = st.selectbox("Team B", df['Team'].sort_values(), key='team_b')

# --- 5. Prediction Logic ---
if team_a_name and team_b_name:
    team_a = df[df['Team'] == team_a_name].iloc[0]
    team_b = df[df['Team'] == team_b_name].iloc[0]
    
    # Math: Base + Seed Modifier - Injuries
    total_r32 = team_a['R32'] + team_b['R32']
    base_prob_a = team_a['R32'] / total_r32 if total_r32 > 0 else 0.5
    modifier = (((team_a['R32'] - (17-team_a['Seed'])/16)) - ((team_b['R32'] - (17-team_b['Seed'])/16))) * 0.20
    
    def get_penalty(name):
        return pd.to_numeric(injuries_df[injuries_df['Team'] == name]['Injury Weight'], errors='coerce').sum()

    final_prob_a = max(0.01, min(0.99, base_prob_a + modifier - get_penalty(team_a_name) + get_penalty(team_b_name)))
    final_prob_b = 1 - final_prob_a
    
    # Display Result
    st.divider()
    pred_winner = team_a_name if final_prob_a > 0.5 else team_b_name
    st.success(f"**Predicted Winner:** {pred_winner} ({max(final_prob_a, final_prob_b)*100:.1f}%)")
    
    # Upset Watch
    if team_a['Seed'] != team_b['Seed']:
        underdog = team_a_name if team_a['Seed'] > team_b['Seed'] else team_b_name
        u_p = final_prob_a if underdog == team_a_name else final_prob_b
        st.info(f"**Upset Watch:** {underdog} has a **{u_p*100:.1f}%** chance.")

    # Injury Report
    match_inj = injuries_df[injuries_df['Team'].isin([team_a_name, team_b_name])]
    if not match_inj.empty:
        with st.expander("🚨 Injury Report"):
            st.table(match_inj[['Player', 'Team', 'Pos', 'Status']])

    # Advance Button
    if st.button(f"🚩 Advance {pred_winner} to Next Round", use_container_width=True):
        st.balloons()
    
# --- 6. Round of 64 Grid ---
st.divider()
st.header("🏆 Round of 64")
regions = df['Region'].dropna().unique()
tabs = st.tabs([str(r) for r in regions])
# Standard Pod Pairings: (1v16 & 8v9), (5v12 & 4v13), (6v11 & 3v14), (7v10 & 2v15)
matchups = [
    (1, 16, "Pod_A"), (8
