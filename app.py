import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

# --- 1. Load the Data ---
@st.cache_data
def load_data():
    df = pd.read_csv('data.csv')
    df['R32'] = df['R32'] / 100
    return df

df = load_data()
# --- Session State (App Memory) ---
# Set default teams so the app doesn't start empty
if 'team_a' not in st.session_state:
    st.session_state.team_a = df['Team'].sort_values().iloc[0]
if 'team_b' not in st.session_state:
    st.session_state.team_b = df['Team'].sort_values().iloc[1]

# This function updates the memory when a matchup button is clicked
def set_matchup(team1, team2):
    st.session_state.team_a = team1
    st.session_state.team_b = team2
    st.session_state.scroll_to_top = True  # Tells the app to jump up!

# --- 2. Build the Streamlit UI ---
st.title("🏀 March Madness Upset Predictor")
st.write("Select two teams to calculate win probabilities and upset potential!")
# --- The Scroll-to-Top Hack ---
# If a button told the app to scroll, inject a tiny invisible script
if st.session_state.get('scroll_to_top', False):
    components.html(
        """
        <script>
            // Forces the main window to scroll to the very top
            window.parent.scrollTo(0, 0);
        </script>
        """,
        height=0
    )
    # Immediately turn the flag off so it doesn't get stuck at the top
    st.session_state.scroll_to_top = False

col1, col2 = st.columns(2)

with col1:
    team_a_name = st.selectbox("Select Team A", df['Team'].sort_values(), key='team_a')

with col2:
    team_b_name = st.selectbox("Select Team B", df['Team'].sort_values(), key='team_b')

# --- 3. The Prediction Logic ---
if team_a_name and team_b_name:
    if team_a_name == team_b_name:
        st.warning("Please select two different teams.")
    else:
        team_a = df[df['Team'] == team_a_name].iloc[0]
        team_b = df[df['Team'] == team_b_name].iloc[0]
        
        # 1. Base Probability 
        # Compares their raw chances of advancing. 
        # We normalize it so they add up to 100% for this specific head-to-head.
        total_r32 = team_a['R32'] + team_b['R32']
        if total_r32 == 0:
            base_prob_a = 0.5 # Fallback if both teams have a 0% R32 chance
        else:
            base_prob_a = team_a['R32'] / total_r32
        
        # 2. Calculate Seeding Discrepancy
        # A simple formula to estimate expected win % based on seed: (17 - Seed) / 16
        # A 1-seed expects ~100% (1.0). A 16-seed expects ~6% (0.06).
        expected_r32_a = (17 - team_a['Seed']) / 16
        expected_r32_b = (17 - team_b['Seed']) / 16
        
        # Discrepancy = Actual R32 minus Expected R32
        # Positive = Under-seeded (Dangerous!). Negative = Over-seeded (Vulnerable!).
        disc_a = team_a['R32'] - expected_r32_a
        disc_b = team_b['R32'] - expected_r32_b
        
        # 3. Net Discrepancy & Multiplier
        net_disc = disc_a - disc_b
        
        # Since we are working with percentages now, a weight of 0.2 means a 
        # massive discrepancy could swing the game by up to 20%
        upset_weight = 0.20 
        modifier = net_disc * upset_weight
        
        # 4. Final Probability Math
        final_prob_a = base_prob_a + modifier
        final_prob_a = max(0.01, min(0.99, final_prob_a)) # Keep between 1% and 99%
        final_prob_b = 1 - final_prob_a
        
        # Determine the Favorite and the Underdog (based strictly on Seed)
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

        # --- 4. Output the Results ---
        st.divider()
        st.subheader("📊 Matchup Results")
        
        st.success(f"**Predicted Winner:** {predicted_winner} ({winner_prob * 100:.1f}%)")
        
if underdog != "Neither (Same Seed)":
            st.info(f"**Upset Watch:** {underdog} has a **{upset_chance * 100:.1f}%** chance of pulling off the upset.")
            
            # Figure out how much the modifier specifically helped or hurt the underdog
            underdog_modifier = modifier if underdog == team_a_name else -modifier
            
            # Show the user exactly what the upset logic did!
            if underdog_modifier > 0:
                st.caption(f"🚨 *Upset logic boosted {underdog}'s chances by **{underdog_modifier * 100:.1f}%** because they are playing better than their seed!*")
            elif underdog_modifier < 0:
                st.caption(f"📉 *Upset logic actually penalized {underdog} by **{abs(underdog_modifier) * 100:.1f}%** because they are over-seeded.*")
            else:
                st.caption("⚖️ *Seeding aligns perfectly with expected performance. No upset modifier applied.*")
        else:
            st.info("Even matchup based on seeding. No technical upset possible.")
            
        # Show the stats so you can verify the math is working as expected
        st.write("### Behind the Math")
        stats_df = pd.DataFrame({
            'Team': [team_a['Team'], team_b['Team']],
            'Seed': [team_a['Seed'], team_b['Seed']],
            'Actual R32 %': [f"{team_a['R32']*100:.1f}%", f"{team_b['R32']*100:.1f}%"],
            'Expected R32 %': [f"{expected_r32_a*100:.1f}%", f"{expected_r32_b*100:.1f}%"]
        })
        st.dataframe(stats_df)


# --- 5. Visualizing the Round of 64 Matchups ---
st.divider()
st.header("🏆 Round of 64 Matchups")
st.write("Here are the opening matchups based on your loaded bracket data:")

# Get the unique regions from your CSV (e.g., South, East, Midwest, West)
# We drop any empty ones just in case your CSV has blank rows
regions = df['Region'].dropna().unique()

if len(regions) > 0:
    # Create interactive tabs for each region!
    tabs = st.tabs([str(r) for r in regions])
    
    # The standard NCAA tournament pairings for the Round of 64
    matchups = [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]
    
    for i, region in enumerate(regions):
        with tabs[i]:
            # Filter the dataframe to only show teams in this specific region
            region_df = df[df['Region'] == region]
            
            # Loop through the standard pairings and print them out
            for high_seed, low_seed in matchups:
                team_high = region_df[region_df['Seed'] == high_seed]
                team_low = region_df[region_df['Seed'] == low_seed]
                
                # Check to make sure both teams exist in your data before writing
                if not team_high.empty and not team_low.empty:
                    name_high = team_high.iloc[0]['Team']
                    name_low = team_low.iloc[0]['Team']
                    
                    # Display the matchup in a clean, readable format
                    # Create a clickable button for each matchup
                    st.button(
                        f"🏀 {high_seed} {name_high} vs. {low_seed} {name_low}", 
                        key=f"{region}_{high_seed}", # A unique ID for each button
                        on_click=set_matchup,        # The function to run when clicked
                        args=(name_high, name_low),  # The teams to send to the dropdowns
                        use_container_width=True     # Makes the buttons wide and uniform
                    )
                else:
                    # If a team is missing (like a play-in game), show a placeholder
                    st.markdown(f"**{high_seed}** TBD  vs.  **{low_seed}** TBD")
else:
    st.info("No region data found in the CSV.")
