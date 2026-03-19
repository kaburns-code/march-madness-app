import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

# --- 1. Load the Data ---
@st.cache_data
def load_data():
    df = pd.read_csv('data.csv')
    # Convert R32 from whole numbers to decimals for accurate math
    df['R32'] = df['R32'] / 100
    return df

df = load_data()

# --- 2. Session State (App Memory) ---
# Set default teams so the app doesn't start empty
if 'team_a' not in st.session_state:
    st.session_state.team_a = df['Team'].sort_values().iloc[0]
if 'team_b' not in st.session_state:
    st.session_state.team_b = df['Team'].sort_values().iloc[1]
if 'scroll_to_top' not in st.session_state:
    st.session_state.scroll_to_top = False

# This function updates the memory when a matchup button is clicked
def set_matchup(team1, team2):
    st.session_state.team_a = team1
    st.session_state.team_b = team2
    st.session_state.scroll_to_top = True  # Tells the app to jump up!

# --- The Scroll-to-Top Hack ---
if st.session_state.scroll_to_top:
    components.html(
        """
        <script>
            window.parent.scrollTo(0, 0);
        </script>
        """,
        height=0
    )
    st.session_state.scroll_to_top = False


# --- 3. Build the Streamlit UI ---
st.title("🏀 March Madness Upset Predictor")
st.write("Select two teams to calculate win probabilities and upset potential!")

col1, col2 = st.columns(2)

with col1:
    team_a_name = st.selectbox("Select Team A", df['Team'].sort_values(), key='team_a')

with col2:
    team_b_name = st.selectbox("Select Team B", df['Team'].sort_values(), key='team_b')


# --- 4. The Prediction Logic ---
if team_a_name and team_b_name:
    if team_a_name == team_b_name:
        st.warning("Please select two different teams.")
    else:
        team_a = df[df['Team'] == team_a_name].iloc[0]
        team_b = df[df['Team'] == team_b_name].iloc[0]
        
        # Base Probability 
        total_r32 = team_a['R32'] + team_b['R32']
        if total_r32 == 0:
            base_prob_a = 0.5 
        else:
            base_prob_a = team_a['R32'] / total_r32
        
        # Calculate Seeding Discrepancy
        expected_r32_a = (17 - team_a['Seed']) / 16
        expected_r32_b = (17 - team_b['Seed']) / 16
        
        disc_a = team_a['R32'] - expected_r32_a
        disc_b = team_b['R32'] - expected_r32_b
        
        # Net Discrepancy & Multiplier
        net_disc = disc_a - disc_b
        upset_weight = 0.20 
        modifier = net_disc * upset_weight
        
        # Final Probability Math
        final_prob_a = base_prob_a + modifier
        final_prob_a = max(0.01, min(0.99, final_prob_a)) 
        final_prob_b = 1 - final_prob_a
        
        # Determine the Favorite and the Underdog
        if team_a['Seed'] > team_b['Seed']:
            underdog = team_a_name
            upset_chance = final_prob_a
        elif team_b['Seed'] > team_a['Seed']:
            underdog = team_b_name
            upset_chance = final_prob_b
        else:
            underdog = "Neither (Same Seed)"
            upset_chance = 0.0

        predicted_winner = team_a_name if final_prob_a > 0.5 else team_b_name
        winner_prob = final_prob_a if predicted_winner == team_a_name else final_prob_b

        # --- 5. Output the Results ---
        st.divider()
        st.subheader("📊 Matchup Results")
        
        st.success(f"**Predicted Winner:** {predicted_winner} ({winner_prob * 100:.1f}%)")
        
        if underdog != "Neither (Same Seed)":
            st.info(f"**Upset Watch:** {underdog} has a **{upset_chance * 100:.1f}%** chance of pulling off the upset.")
            
            underdog_modifier = modifier if underdog == team_a_name else -modifier
            
            if underdog_modifier > 0:
                st.caption(f"🚨 *Upset logic boosted {underdog}'s chances by **{underdog_modifier * 100:.1f}%** because they are playing better than their seed!*")
            elif underdog_modifier < 0:
                st.caption(f"📉 *Upset logic actually penalized {underdog} by **{abs(underdog_modifier) * 100:.1f}%** because they are over-seeded.*")
            else:
                st.caption("⚖️ *Seeding aligns perfectly with expected performance. No upset modifier applied.*")
        else:
            st.info("Even matchup based on seeding. No technical upset possible.")
            
        # --- Verbal Breakdown of the Math ---
        st.write("### How We Calculated This")
        st.markdown(f"""
        **1. Base Win Probability:**
        First, we look at their raw chances to reach the Round of 32. 
        *{team_a_name}* has a {team_a['R32']*100:.1f}% chance, and *{team_b_name}* has a {team_b['R32']*100:.1f}% chance. 
        Head-to-head, this gives *{team_a_name}* a baseline win probability of **{base_prob_a * 100:.1f}%**.

        **2. Seeding Discrepancy (The Upset Factor):**
        A typical {team_a['Seed']}-seed expects a {expected_r32_a*100:.1f}% chance to advance, meaning *{team_a_name}* is performing at a **{disc_a * 100:+.1f}%** difference compared to historical expectations. 
        *{team_b_name}* (a {team_b['Seed']}-seed) is performing at a **{disc_b * 100:+.1f}%** difference.

        **3. The Final Formula:**
        We compare these two discrepancies to see who is relatively "hotter" and apply our upset weight. This generates a modifier of **{modifier * 100:+.1f}%**. 
        We add this modifier to the base probability ({base_prob_a * 100:.1f}% {modifier * 100:+.1f}%) to get *{team_a_name}*'s true win probability of **{final_prob_a * 100:.1f}%**. 
        Because one team must win, *{team_b_name}*'s chance is exactly the remaining percentage (**{final_prob_b * 100:.1f}%**).
        """)
            
        # Show Behind the Math stats
        st.write("### Behind the Math")
        stats_df = pd.DataFrame({
            'Team': [team_a['Team'], team_b['Team']],
            'Seed': [team_a['Seed'], team_b['Seed']],
            'Actual R32 %': [f"{team_a['R32']*100:.1f}%", f"{team_b['R32']*100:.1f}%"],
            'Expected R32 %': [f"{expected_r32_a*100:.1f}%", f"{expected_r32_b*100:.1f}%"]
        })
        st.dataframe(stats_df)

# --- 6. Visualizing the Round of 64 Matchups ---
st.divider()
st.header("🏆 Round of 64 Matchups")
# --- Display the visual bracket image ---
# You can replace this URL with any image link of the current bracket!
st.image(
    "https://sportshub.cbsistatic.com/i/r/2026/03/15/7e968c18-f3e4-42b9-93a0-0b7f617074e5/thumbnail/1200x675/c33e85c7427fb547d22006588b5caaea/march-madness-bracket-2026-men-border.jpg", 
    caption="The Tournament Bracket"
)
st.write("Click any matchup below to instantly load it into the predictor!")

regions = df['Region'].dropna().unique()

if len(regions) > 0:
    tabs = st.tabs([str(r) for r in regions])
    matchups = [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]
    
    for i, region in enumerate(regions):
        with tabs[i]:
            region_df = df[df['Region'] == region]
            for high_seed, low_seed in matchups:
                team_high = region_df[region_df['Seed'] == high_seed]
                team_low = region_df[region_df['Seed'] == low_seed]
                
                if not team_high.empty and not team_low.empty:
                    name_high = team_high.iloc[0]['Team']
                    name_low = team_low.iloc[0]['Team']
                    
                    st.button(
                        f"🏀 {high_seed} {name_high} vs. {low_seed} {name_low}", 
                        key=f"{region}_{high_seed}_{low_seed}", 
                        on_click=set_matchup,        
                        args=(name_high, name_low),  
                        use_container_width=True     
                    )
                else:
                    st.markdown(f"**{high_seed}** TBD  vs.  **{low_seed}** TBD")
else:
    st.info("No region data found in the CSV.")
