"""
merge_player_features.py
---------------------------------
Creates an enriched training dataset by merging
per-match player summaries into team-level features.
"""

import os
import pandas as pd

# ----------------------------
# 1. Load the two main datasets
# ----------------------------
features_path = os.path.join("data", "features_train.csv")
players_path = os.path.join("data", "match_boxscores_detailed_cleaned.csv")

features = pd.read_csv(features_path)
players = pd.read_csv(players_path)

print(f"✅ Loaded {len(features)} team-match rows and {len(players)} player-match rows")

# ----------------------------
# Normalize key columns for merging
# ----------------------------
for df in (features, players):
    df["team"] = (
        df["team"]
        .str.lower()          # lowercase everything
        .str.strip()          # remove extra spaces
        .str.replace(" ", "-", regex=False)  # turn spaces into dashes
    )
    df["match_id"] = df["match_id"].str.lower().str.strip()


# ----------------------------
# 2. Build player-level summaries per team per match
# ----------------------------
agg = players.groupby(["match_id", "team"]).agg({
    "G": ["sum", "mean", "max"],
    "SH": ["sum", "mean"],
    "SOG": ["sum", "mean"],
    "A": ["sum", "mean"],
    "player": "count"     # number of player entries that match
}).reset_index()

# Flatten multi-level column names
agg.columns = [
    "match_id", "team",
    "G_sum", "G_mean", "G_max",
    "SH_sum", "SH_mean",
    "SOG_sum", "SOG_mean",
    "A_sum", "A_mean",
    "player_count_match"
]

print(f"✅ Built {len(agg)} aggregated player rows")

# ----------------------------
# 3. Merge with team features
# ----------------------------
merged = features.merge(agg, on=["match_id", "team"], how="left")

print(f"✅ Merged shape: {merged.shape}")

# ----------------------------
# 4. Save enriched dataset
# ----------------------------
output_path = os.path.join("data", "features_enriched.csv")
merged.to_csv(output_path, index=False)

print(f"✅ Saved enriched dataset → {output_path}")
print("You can now retrain your model with this new file.")
