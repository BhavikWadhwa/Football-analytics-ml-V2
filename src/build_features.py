import pandas as pd
import numpy as np
from pathlib import Path

# -------------------------------------------------
# File paths
# -------------------------------------------------
matches_path = Path("data/matches_all.csv")
boxscores_path = Path("data/match_boxscores_detailed_cleaned.csv")
lineups_path = Path("data/team_lineups_clean.csv")
out_path = Path("data/features_train.csv")

# -------------------------------------------------
# Load datasets
# -------------------------------------------------
matches = pd.read_csv(matches_path)
box = pd.read_csv(boxscores_path)
lineups = pd.read_csv(lineups_path)

print("✅ Loaded:")
print(f"Matches: {len(matches)} rows")
print(f"Boxscores: {len(box)} rows")
print(f"Lineups: {len(lineups)} rows\n")

# -------------------------------------------------
# Step 1: Normalize column names
# -------------------------------------------------
box.columns = [c.strip().lower() for c in box.columns]
matches.columns = [c.strip().lower() for c in matches.columns]
lineups.columns = [c.strip().lower() for c in lineups.columns]

# -------------------------------------------------
# Step 2: Rename stat columns correctly
# -------------------------------------------------
rename_map = {
    "a": "assists",
    "sh": "shots",
    "sog": "sog",
    "g": "goals"
}
box = box.rename(columns=rename_map)

# -------------------------------------------------
# Step 3: Clean text columns
# -------------------------------------------------
for df in [matches, box, lineups]:
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype(str).str.strip().str.lower()

# -------------------------------------------------
# Step 4: Ensure numeric columns
# -------------------------------------------------
for col in ["shots", "sog", "goals", "assists"]:
    if col in box.columns:
        box[col] = pd.to_numeric(box[col], errors="coerce").fillna(0)
    else:
        box[col] = 0

# -------------------------------------------------
# Step 5: Aggregate team stats
# -------------------------------------------------
team_stats = (
    box.groupby(["match_id", "team"], as_index=False)
    .agg({
        "goals": "sum",
        "shots": "sum",
        "sog": "sum",
        "assists": "sum",
        "player": "count"
    })
    .rename(columns={"player": "player_count"})
)

# -------------------------------------------------
# Step 6: Merge player attributes (lineups)
# -------------------------------------------------
if {"position_group", "year_num"}.issubset(lineups.columns):
    box_lineup = box.merge(
        lineups[["player", "team", "position_group", "year_num"]],
        on=["player", "team"],
        how="left"
    )

    roster_summary = (
        box_lineup.groupby(["match_id", "team"], as_index=False)
        .agg({
            "year_num": "mean",
            "position_group": lambda x: x.value_counts(normalize=True).to_dict()
        })
    )

    roster_expanded = pd.DataFrame(roster_summary["position_group"].apply(pd.Series)).fillna(0)
    roster_final = pd.concat([roster_summary[["match_id", "team", "year_num"]], roster_expanded], axis=1)
    roster_final = roster_final.rename(columns={"year_num": "avg_player_year"})
else:
    print("⚠️ Missing 'position_group' or 'year_num' in lineups → skipping roster composition.")
    roster_final = pd.DataFrame()

# -------------------------------------------------
# Step 7: Combine stats + roster + matches
# -------------------------------------------------
features = team_stats.merge(roster_final, on=["match_id", "team"], how="left")

matches["match_id"] = matches["match_id"].astype(str).str.lower()
for col in ["home_team", "away_team"]:
    matches[col] = matches[col].astype(str).str.lower()

home = features.merge(matches, left_on=["match_id", "team"], right_on=["match_id", "home_team"], how="inner")
home["is_home"] = 1
away = features.merge(matches, left_on=["match_id", "team"], right_on=["match_id", "away_team"], how="inner")
away["is_home"] = 0

combined = pd.concat([home, away], ignore_index=True)

# -------------------------------------------------
# Step 8: Compute match result
# -------------------------------------------------
def result(row):
    if "home_goals" in row and "away_goals" in row:
        if row["is_home"] == 1:
            if row["home_goals"] > row["away_goals"]: return "win"
            elif row["home_goals"] < row["away_goals"]: return "loss"
            else: return "draw"
        else:
            if row["away_goals"] > row["home_goals"]: return "win"
            elif row["away_goals"] < row["home_goals"]: return "loss"
            else: return "draw"
    return np.nan

combined["result"] = combined.apply(result, axis=1)

# -------------------------------------------------
# Step 9: Save
# -------------------------------------------------
combined.to_csv(out_path, index=False)
print(f"💾 Saved → {out_path}")
print("✅ Final shape:", combined.shape)

# Optional: sanity check
print("\n🔍 Sample team stats:")
print(team_stats.head())
