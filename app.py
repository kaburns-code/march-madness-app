import streamlit as st
import pandas as pd
import random

# --- 1. Load the Data ---
@st.cache_data
def load_data():
    # Load Main Bracket Stats
    df = pd.read_csv('data.csv')
    df['R32'] = df['R32'] / 100
    
    # Load and Clean Injury Data
    try:
        inj_df = pd.read_csv('injuries.csv')
        # This line ensures "Injury Weight" is a number so the math works
        inj_df['Injury Weight'] = pd.to_numeric(inj_df['Injury Weight'], errors='coerce').fillna(0)
    except:
        # Fallback if the file is missing or broken
        inj_df = pd.DataFrame(columns=['Player', 'Team', 'Pos', 'Injury', 'Status', 'Value', 'Injury Weight'])
    
    return df, inj_df

df, injuries_df = load_data()

# --- 2. Session State (Tournament Memory) ---
if 'team_a' not in st.session_state:
    st.session_state.team_a = df['Team'].sort_values().iloc[0]
if 'team_b' not in st.session_state:
    st.session_state.team_b = df['Team'].sort_values().iloc[1]
if 'bracket_winners' not in st.session_state:
    st.session_state.bracket_winners = {}

# FIXED: set_matchup no longer uses the broken set_query_params
def set_matchup(team1, team2):
    st.session_state.team_a = team1
    st.session_state.team_b = team2
    # Triggers a rerun to show the new teams at the top
    st.rerun()

def advance_team(team_name, slot_id):
    st.session_state.bracket_winners[slot_id] = team_name
    st.toast(f"🚩 {team_name} moved to Round of 32!")

# --- 3. Main Predictor UI ---
st.title("🏀 Tournament Master 2026")
st.write("Calculates odds using **2026 Season Stats** + **Active Injury Reports**.")

col1, col2 = st.columns(2)
with col1:
    team_a_name = st.selectbox("Team A", df['Team'].sort_values(), key='team_a_select')
with col2:
    team_b_name = st.selectbox("Team B", df['Team'].sort_values(), key='team_b_select')

# Update state if user manually changes the dropdowns
st.session_state.team_a = team_a_name
st.session_state.team_b = team_b_name

# --- 4. The Logic Engine ---
if st.session_state.team_a and st.session_state.team_b:
    t_a = df[df['Team'] == st.session_state.team_a].iloc[0]
    t_b = df[df['Team'] == st.session_state.team_b].iloc[0]
    
    # A. Base Stats Math
    total_power = t_a['R32'] + t_b['R32']
    base_prob = t_a['R32'] / total_power if total_power > 0 else 0.5
    
    # B. Seeding Bias Logic
    mod = (((t_a['R32'] - (17-t_a['Seed'])/16)) - ((t_b['R32'] - (17-t_b['Seed'])/16))) * 0.20
    
    # C. RESTORED INJURY MATH
    pen_a = injuries_df[injuries_df['Team'] == st.session_state.team_a]['Injury Weight'].sum()
    pen_b = injuries_df[injuries_df['Team'] == st.session_state.team_b]['Injury Weight'].sum()
    
    # Calculation: Base + Mod - (Injuries for A) + (Injuries for B)
    final_a = max(0.01, min(0.99, base_prob + mod - pen_a + pen_b))
    final_b = 1 - final_a

    # --- 5. Results Display ---
    st.divider()
    
    # Winner Box
    winner = st.session_state.team_a if final_a > 0.5 else st.session_state.team_b
    win_pct = max(final_a, final_b) * 100
    st.success(f"**Projected Winner:** {winner} ({win_pct:.1f}%)")

    # Blue Section: Upset Watch
    if t_a['Seed'] != t_b['Seed']:
        dog = st.session_state.team_a if t_a['Seed'] > t_b['Seed'] else st.session_state.team_b
        dog_pct = final_a if dog == st.session_state.team_a else final_b
        st.info(f"**Upset Watch:** {dog} has a **{dog_pct*100:.1f}%** chance to win.")

    # Yellow Section: Injury Report
    match_inj = injuries_df[injuries_df['Team'].isin([st.session_state.team_a, st.session_state.team_b])]
    if not match_inj.empty:
        st.warning("⚠️ **Active Injury Report for this Matchup:**")
        with st.expander("🔍 See Impact Details"):
            st.table(match_inj[['Player', 'Team', 'Pos', 'Injury', 'Status', 'Injury Weight']])

    st.bar_chart(pd.DataFrame({"Win %": [final_a*100, final_b*100]}, index=[st.session_state.team_a, st.session_state.team_b]))

    if st.button("🎲 Simulate Game Result", use_container_width=True):
        if random.random() < final_a:
            st.balloons()
            st.subheader(f"🏆 {st.session_state.team_a} wins the simulation!")
        else:
            st.snow()
            st.subheader(f"🏆 {st.session_state.team_b} wins the simulation!")

# --- 6. Round of 64 Grid ---
st.divider()
st.header("🏆 Round of 64")
regions = df['Region'].dropna().unique()
tabs = st.tabs([str(r) for r in regions])
matchups = [(1,16,"A"), (8,9,"A"), (5,12,"B"), (4,13,"B"), (6,11,"C"), (3,14,"C"), (7,10,"D"), (2,15,"D")]

for i, region in enumerate(regions):
    with tabs[i]:
        reg_df = df[df['Region'] == region]
        for s1, s2, pod in matchups:
            t1, t2 = reg_df[reg_df['Seed'] == s1], reg_df[reg_df['Seed'] == s2]
            if not t1.empty and not t2.empty:
                n1, n2 = t1.iloc[0]['Team'], t2.iloc[0]['Team']
                c_btn, c_adv = st.columns([3, 1.2])
                with c_btn:
                    st.button(f"🏀 {s1} {n1} vs {s2} {n2}", key=f"b_{region}_{s1}", on_click=set_matchup, args=(n1, n2), use_container_width=True)
                with c_adv:
                    pick = st.selectbox("Win", [n1, n2], key=f"s_{region}_{s1}", label_visibility="collapsed")
                    if st.button("➕", key=f"a_{region}_{s1}", help="Advance to Round of 32"):
                        advance_team(pick, f"{region}_{pod}_{s1}")

# --- 7. Round of 32 Builder ---
st.divider()
st.header("🧬 Your Custom Round of 32 Matchups")
for r in regions:
    with st.expander(f"Region: {r}"):
        pods = {"A":[1,8], "B":[5,4], "C":[6,3], "D":[7,2]}
        for p, s_nums in pods.items():
            w1 = st.session_state.bracket_winners.get(f"{r}_{p}_{s_nums[0]}")
            w2 = st.session_state.bracket_winners.get(f"{r}_{p}_{s_nums[1]}")
            if w1 and w2:
                st.button(f"🔥 Analyze: {w1} vs {w2}", key=f"r32_{r}_{p}", on_click=set_matchup, args=(w1, w2), use_container_width=True)
            else:
                st.caption(f"Pod {p}: Waiting for Round of 64 winners...")
