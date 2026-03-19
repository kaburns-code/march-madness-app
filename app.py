import streamlit as st
import pandas as pd

# --- 1. Load the Data ---
@st.cache_data
def load_data():
    df = pd.read_csv('data.csv')
    return df

df = load_data()

# --- 2. Build the Streamlit UI ---
st.title("🏀 March Madness Upset Predictor")
st.write("Select two teams to calculate win probabilities and upset potential!")

col1, col2 = st.columns(2)

with col1:
    # Assuming your CSV has a 'Team' column. Change 'Team' if it's named differently!
    team_a_name = st.selectbox("Select Team A", df['Team'].sort_values())

with col2:
    team_b_name = st.selectbox("Select Team B", df['Team'].sort_values(), index=1)

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
