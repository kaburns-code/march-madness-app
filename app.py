import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

# --- 1. Load the Data ---
@st.cache_data
def load_data():
    df = pd.read_csv('data.csv')
    df['R32'] = df['R32'] / 100
    
    try:
        # Pulling from your new injuries.csv
        inj_df = pd.read_csv('injuries.csv')
    except:
        # Fallback if file isn't found
        inj_df = pd.DataFrame(columns=['Player', 'Team', 'Position', 'Injury', 'Status', 'Value', 'Injury Weight'])
    
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
st.write("Analyze matchups with live **Injury Impact** layering.")

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
        
        # C. Injury Layering (Using your EXACT column names)
        def get_injury_penalty(name):
            relevant = injuries_df[injuries_df['Team'] == name]
            # Use 'Injury Weight' with the space!
            return relevant['Injury Weight'].sum()

        penalty_a = get_injury_penalty(team_a_name)
        penalty_b = get_injury_penalty(team_b_name)
        
        # Apply Logic: Base + Upset Logic - Team A Injuries + Team B Injuries
        final_prob_a = max(0.01, min(0.99, base_prob_a + modifier - penalty_a + penalty_b))
        final_prob_b = 1 - final_prob_a

        # --- 5. Display Results ---
        st.divider()
        
       # Dynamic Injury Report
        matchup_injuries = injuries_df[injuries_df['Team'].isin([team_a_name, team_b_name])]
        if not matchup_injuries.empty:
            st.warning("⚠️ **Injury Impact Detected:** Win probabilities have been adjusted.")
            with st.expander("🔍 View Scouting & Injury Report"):
                # Updated to use 'Pos' instead of 'Position' to match your CSV
                st.table(matchup_injuries[['Player', 'Team', 'Pos', 'Injury', 'Status', 'Value']])

        predicted_winner = team_a_name if final_prob_a > 0.5 else team_b_name
        win_p = final_prob_a if predicted_winner == team_a_name else final_prob_b
        
        st.success(f"**Predicted Winner:** {predicted_winner} ({win_p*100:.1f}%)")

        # Visual Probability Bar
        chart_data = pd.DataFrame({
            "Team": [team_a_name, team_b_name], 
            "Win %": [final_prob_a*100, final_prob_b*100]
        }).set_index("Team")
        st.bar_chart(chart_data)

# --- 6. Bracket Matchups (at bottom) ---
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
