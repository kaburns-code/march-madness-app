import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

# --- 1. Load and Clean the Data ---
@st.cache_data
def load_data():
    df = pd.read_csv('data.csv')
    # Convert R32 from whole numbers (e.g. 93.5) to decimals (0.935)
    df['R32'] = df['R32'] / 100
    return df

df = load_data()

# --- 2. Session State (App Memory) ---
if 'team_a' not in st.session_state:
    st.session_state.team_a = df['Team'].sort_values().iloc[0]
if 'team_b' not in st.session_state:
    st.session_state.team_b = df['Team'].sort_values().iloc[1]
if 'scroll_to_top' not in st.session_state:
    st.session_state.scroll_to_top = False

# Function to update teams and trigger the jump
def set_matchup(team1, team2):
    st.session_state.team_a = team1
    st.session_state.team_b = team2
    st.session_state.scroll_to_top = True

# --- 3. The Anchor Jump (Visual Fix) ---
# This invisible div is our "target" at the top of the page
st.markdown("<div id='top'></div>", unsafe_allow_html=True)

if st.session_state.scroll_to_top:
    # This script tells the browser to navigate to the #top anchor
    components.html(
        """
        <script>
            window.parent.location.hash = 'top';
        </script>
        """,
        height=0
    )
    st.session_state.scroll_to_top = False

# --- 4. Main UI ---
st.title("🏀 March Madness Upset Predictor")
st.write("Analyze matchups using efficiency metrics and custom upset logic.")

col1, col2 = st.columns(2)

with col1:
    team_a_name = st.selectbox("Select Team A", df['Team'].sort_values(), key='team_a')
with col2:
    team_b_name = st.selectbox("Select Team B", df['Team'].sort_values(), key='team_b')

# --- 5. Prediction Logic ---
if team_a_name and team_b_name:
    if team_a_name == team_b_name:
        st.warning("Please select two different teams.")
    else:
        team_a = df[df['Team'] == team_a_name].iloc[0]
        team_b = df[df['Team'] == team_b_name].iloc[0]
        
        # Base Probability (Head-to-Head R32 Ratio)
        total_r32 = team_a['R32'] + team_b['R32']
        base_prob_a = team_a['R32'] / total_r32 if total_r32 > 0 else 0.5
        
        # Seeding Discrepancy
        expected_r32_a = (17 - team_a['Seed']) / 16
        expected_r32_b = (17 - team_b['Seed']) / 16
        disc_a = team_a['R32'] - expected_r32_a
        disc_b = team_b['R32'] - expected_r32_b
        
        # Final Modifier
        modifier = (disc_a - disc_b) * 0.20 
        final_prob_a = max(0.01, min(0.99, base_prob_a + modifier))
        final_prob_b = 1 - final_prob_a

        # --- 6. Results Display ---
        st.divider()
        predicted_winner = team_a_name if final_prob_a > 0.5 else team_b_name
        winner_prob = final_prob_a if predicted_winner == team_a_name else final_prob_b
        
        st.success(f"**Predicted Winner:** {predicted_winner} ({winner_prob * 100:.1f}%)")
        
        # Upset Context
        if team_a['Seed'] != team_b['Seed']:
            underdog = team_a_name if team_a['Seed'] > team_b['Seed'] else team_b_name
            u_prob = final_prob_a if underdog == team_a_name else final_prob_b
            st.info(f"**Upset Watch:** {underdog} has a **{u_prob * 100:.1f}%** chance of winning.")
            
            # Modifier Explanation
            u_mod = modifier if underdog == team_a_name else -modifier
            if u_mod > 0:
                st.caption(f"🚨 Logic boosted {underdog} by {u_mod*100:.1f}% (Under-seeded/Over-performing).")
            else:
                st.caption(f"📉 Logic penalized {underdog} by {abs(u_mod)*100:.1f}% (Over-seeded/Under-performing).")

        # Verbal Breakdown
        with st.expander("📖 View Calculation Details"):
            st.markdown(f"""
            - **Base Power:** Based on R32 metrics, {team_a_name} starts with a **{base_prob_a*100:.1f}%** edge.
            - **Seed Strength:** A {team_a['Seed']}-seed usually has a {expected_r32_a*100:.0f}% R32 chance. {team_a_name} is at {team_a['R32']*100:.1f}%.
            - **Adjustment:** The 'Upset Factor' shifted the odds by **{modifier*100:+.1f}%** based on seed vs. performance.
            """)

# --- 7. Bracket & Matchups ---
st.divider()
st.header("🏆 Round of 64 Bracket")
# Note: This is a placeholder bracket image. Update URL for the current year!
st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/March_Madness_Bracket.svg/1024px-March_Madness_Bracket.svg.png")

regions = df['Region'].dropna().unique()
if len(regions) > 0:
    tabs = st.tabs([str(r) for r in regions])
    matchups = [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]
    
    for i, region in enumerate(regions):
        with tabs[i]:
            region_df = df[df['Region'] == region]
            for s1, s2 in matchups:
                t1 = region_df[region_df['Seed'] == s1]
                t2 = region_df[region_df['Seed'] == s2]
                if not t1.empty and not t2.empty:
                    name1, name2 = t1.iloc[0]['Team'], t2.iloc[0]['Team']
                    st.button(f"🏀 {s1} {name1} vs {s2} {name2}", key=f"btn_{region}_{s1}", 
                              on_click=set_matchup, args=(name1, name2), use_container_width=True)
