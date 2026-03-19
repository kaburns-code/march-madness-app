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
        # Pulling from your injuries.csv
        inj_df = pd.read_csv('injuries.csv')
    except:
        # Fallback empty dataframe
        inj_df = pd.DataFrame(columns=['Player', 'Team', 'Pos', 'Injury', 'Status', 'Value', 'Injury Weight'])
    return df, inj_df

df, injuries_df = load_data()

# --- 2. Session State & Anchor Jump ---
if 'team_a' not in st.session_state:
    st.session_state.team_a = df['Team'].sort_values().iloc[0]
if 'team_b' not in st.session_state:
    st.session_state.team_b = df['Team'].sort_values().iloc[1]
if 'scroll_to_top' not in st.session_state:
    st.session_state.scroll_to_top = False

def set_matchup(team1, team2):
    st.session_state.team_a = team1
    st.session_state.team_b = team2
    st.session_state.scroll_to_top = True

st.markdown("<div id='top'></div>", unsafe_allow_html=True)
if st.session_state.scroll_to_top:
    components.html("<script>window.parent.location.hash = 'top';</script>", height=0)
    st.session_state.scroll_to_top = False

# --- 3. UI Selectors ---
st.title("🏀 March Madness Upset Predictor")
st.write("Analyze matchups with **Seeding Logic** and **Real-Time Injury Reports**.")

col1, col2 = st.columns(2)
with col1:
    team_a_name = st.selectbox("Select Team A", df['Team'].sort_values(), key='team_a')
with col2:
    team_b_name = st.selectbox("Select Team B", df['Team'].sort_values(), key='team_b')

# --- 4. Prediction Logic ---
if team_a_name and team_b_name:
    if team_a_name == team_b_name:
        st.warning("Please select two different teams.")
    else:
        team_a = df[df['Team'] == team_a_name].iloc[0]
        team_b = df[df['Team'] == team_b_name].iloc[0]
        
        # A. Base Power Ratio
        total_r32 = team_a['R32'] + team_b['R32']
        base_prob_a = team_a['R32'] / total_r32 if total_r32 > 0 else 0.5
        
        # B. Upset Modifier (Seed vs Performance)
        exp_a = (17 - team_a['Seed']) / 16
        exp_b = (17 - team_b['Seed']) / 16
        modifier = ((team_a['R32'] - exp_a) - (team_b['R32'] - exp_b)) * 0.20
        
        # C. Injury Layering (Using Injury Weight with a space)
        def get_injury_penalty(name):
            relevant = injuries_df[injuries_df['Team'] == name]
            return pd.to_numeric(relevant['Injury Weight'], errors='coerce').sum()

        penalty_a = get_injury_penalty(team_a_name)
        penalty_b = get_injury_penalty(team_b_name)
        
        # FINAL MATH: Base + Logic - Injuries
        final_prob_a = max(0.01, min(0.99, base_prob_a + modifier - penalty_a + penalty_b))
        final_prob_b = 1 - final_prob_a

        # --- 5. Display Results ---
        st.divider()
        
        # Determine Underdog for the "Blue Section"
        if team_a['Seed'] > team_b['Seed']:
            underdog, u_prob = team_a_name, final_prob_a
        elif team_b['Seed'] > team_a['Seed']:
            underdog, u_prob = team_b_name, final_prob_b
        else:
            underdog, u_prob = None, 0

        # Predicted Winner (Green Box)
        predicted_winner = team_a_name if final_prob_a > 0.5 else team_b_name
        win_p = final_prob_a if predicted_winner == team_a_name else final_prob_b
        st.success(f"**Predicted Winner:** {predicted_winner} ({win_p*100:.1f}%)")

        # THE BLUE SECTION (Upset Watch)
        if underdog:
            st.info(f"**Upset Watch:** {underdog} has a **{u_prob * 100:.1f}%** chance of pulling off the upset.")

# Injury Warning (Yellow Box)
        matchup_injuries = injuries_df[injuries_df['Team'].isin([team_a_name, team_b_name])]
        if not matchup_injuries.empty:
            st.warning("⚠️ **Injury Impact Detected:** Win probabilities have been adjusted based on player availability.")
            with st.expander("🔍 View Scouting & Injury Report"):
                # Fixed: Removed the extra closing parenthesis at the end
                st.table(matchup_injuries[['Player', 'Team', 'Pos', 'Injury', 'Status', 'Value']])

        # --- 6. The Simulation Button ---
        if st.button("🎲 Simulate Game Result", use_container_width=True):
            roll = random.random() 
            if roll < final_prob_a:
                st.balloons()
                st.subheader(f"🏆 {team_a_name} wins the simulation!")
            else:
                st.snow()
                st.subheader(f"🏆 {team_b_name} wins the simulation!")
            st.caption(f"Simulation based on a {final_prob_a*100:.1f}% vs {final_prob_b*100:.1f}% probability split.")

# --- 7. Bracket Buttons (at bottom) ---
st.divider()
st.header("🏆 Round of 64 Matchups")
regions = df['Region'].dropna().unique()
if len(regions) > 0:
    tabs = st.tabs([str(r) for r in regions])
    matchups = [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]
    for i, region in enumerate(regions):
        with tabs[i]:
            region_df = df[df['Region'] == region]
            for s1, s2 in matchups:
                t1, t2 = region_df[region_df['Seed'] == s1], region_df[region_df['Seed'] == s2]
                if not t1.empty and not t2.empty:
                    n1, n2 = t1.iloc[0]['Team'], t2.iloc[0]['Team']
                    st.button(f"🏀 {s1} {n1} vs {s2} {n2}", key=f"btn_{region}_{s1}", on_click=set_matchup, args=(n1, n2), use_container_width=True)
