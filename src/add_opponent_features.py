"""
add_opponent_features.py
--------------------------------
Adds opponent-relative stats to the enriched dataset.
"""

import os
import pandas as pd

# Load dataset
data_path = os.path.join("data", "features_enriched.csv")
df = pd.read_csv(data_path)
print(f"✅ Loaded {len(df)} rows")

# ----------------------------
# 1. Create opponent mapping per match
# ----------------------------

# We will merge the dataframe to itself to get opponent stats
# Suffix "_opp" will refer to the opposing team in that match
merged = df.merge(
    df,
    on="match_id",
    suffixes=("", "_opp")
)

# Keep only rows where team != team_opp (avoid self-pair)
merged = merged[merged["team"] != merged["team_opp"]].copy()
print(f"✅ Created opponent pairs: {len(merged)} rows")

# ----------------------------
# 2. Calculate relative features
# ----------------------------

merged["goal_diff"] = merged["goals"] - merged["goals_opp"]
merged["shot_diff"] = merged["shots"] - merged["shots_opp"]
merged["sog_diff"] = merged["sog"] - merged["sog_opp"]
merged["assist_diff"] = merged["assists"] - merged["assists_opp"]

# Optional: player-based relative features
merged["G_mean_diff"] = merged["G_mean"] - merged["G_mean_opp"]
merged["SH_mean_diff"] = merged["SH_mean"] - merged["SH_mean_opp"]
merged["SOG_mean_diff"] = merged["SOG_mean"] - merged["SOG_mean_opp"]
merged["A_mean_diff"] = merged["A_mean"] - merged["A_mean_opp"]

# ----------------------------
# 3. Select relevant columns for final dataset
# ----------------------------

keep_cols = [
    "match_id", "team", "season", "date", "home_team", "away_team",
    "is_home", "result",
    "goal_diff", "shot_diff", "sog_diff", "assist_diff",
    "G_mean_diff", "SH_mean_diff", "SOG_mean_diff", "A_mean_diff"
]

# Add back all original features you want to keep
base_cols = [
    "goals", "shots", "sog", "assists",
    "player_count", "avg_player_year", "for", "mid",
    "G_mean", "SH_mean", "SOG_mean", "A_mean"
]

final = merged[base_cols + keep_cols]

# ----------------------------
# 4. Save final dataset
# ----------------------------
output_path = os.path.join("data", "features_opponent.csv")
final.to_csv(output_path, index=False)
print(f"✅ Saved dataset with opponent-relative features → {output_path}")
