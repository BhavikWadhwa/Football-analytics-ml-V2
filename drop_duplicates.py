import pandas as pd

# Load the CSV
df = pd.read_csv("data/match_boxscores_detailed.csv")

# --- Fix column misalignment (real meanings from Canada West site) ---
df = df.rename(columns={
    'G': 'A',        # Assists
    'PLAYER': 'SH',  # Shots
    'SH': 'SOG',     # Shots on Goal
    'SOG': 'G'       # Goals
})

# --- Drop duplicates if any ---
df = df.drop_duplicates()

# --- Save the cleaned file ---
output_path = "data/match_boxscores_detailed_cleaned.csv"
df.to_csv(output_path, index=False)

print(f"✅ Cleaned and realigned dataset saved → {output_path}")