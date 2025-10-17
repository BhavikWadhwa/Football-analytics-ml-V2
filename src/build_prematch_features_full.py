"""
build_prematch_full.py
--------------------------------------------------------
Builds a full pre-match predictive dataset combining:
- Rolling 3-match averages per team (form)
- Rolling win rate (recent results)
- Opponent form comparison (form_diff)
Keeps all rows and fills early values intelligently.
"""

import os
import pandas as pd
import numpy as np

# --------------------------------
# 1. Load enriched base dataset
# --------------------------------
data_path = os.path.join("data", "features_enriched.csv")
df = pd.read_csv(data_path)
print(f"✅ Loaded dataset with {len(df)} rows and {len(df.columns)} columns")

# Ensure ordering
df["date"] = df["date"].astype(str)
df = df.sort_values(["season", "team", "date"])

# --------------------------------
# 2. Compute rolling averages (team form)
# --------------------------------
stats_cols = ["shots", "sog", "assists", "player_count", "avg_player_year"]

for col in stats_cols:
    df[f"{col}_rolling3"] = (
        df.groupby(["season", "team"])[col]
        .transform(lambda x: x.shift(1).rolling(window=3, min_periods=1).mean())
    )

# --------------------------------
# 3. Compute recent win rate
# --------------------------------
def to_numeric_result(r):
    if r == "win":
        return 1
    elif r == "loss":
        return 0
    else:
        return 0.5  # draws in the middle

df["numeric_result"] = df["result"].apply(to_numeric_result)

df["win_rate_rolling5"] = (
    df.groupby(["season", "team"])["numeric_result"]
    .transform(lambda x: x.shift(1).rolling(window=5, min_periods=1).mean())
)

# --------------------------------
# 4. Fill NaNs with team averages
# --------------------------------
rolling_cols = [f"{c}_rolling3" for c in stats_cols] + ["win_rate_rolling5"]
for col in rolling_cols:
    df[col] = df.groupby("team")[col].transform(lambda x: x.fillna(x.mean()))
df.fillna(df.mean(numeric_only=True), inplace=True)

# --------------------------------
# 5. Compute opponent form differences
# --------------------------------
# Merge dataset with itself by match_id to get opponent info
merged = df.merge(df, on="match_id", suffixes=("", "_opp"))
merged = merged[merged["team"] != merged["team_opp"]].copy()

for col in stats_cols:
    merged[f"{col}_form_diff"] = merged[f"{col}_rolling3"] - merged[f"{col}_rolling3_opp"]

merged["win_rate_diff"] = merged["win_rate_rolling5"] - merged["win_rate_rolling5_opp"]

# --------------------------------
# 6. Select columns for final dataset
# --------------------------------
keep_cols = [
    "match_id", "season", "team", "date", "home_team", "away_team", "is_home", "result"
]

form_cols = [f"{c}_rolling3" for c in stats_cols]
diff_cols = [f"{c}_form_diff" for c in stats_cols] + ["win_rate_diff"]

final_cols = form_cols + diff_cols + ["win_rate_rolling5"] + ["player_count", "for", "mid"]

final = merged[keep_cols + final_cols]

# --------------------------------
# 7. Save final predictive dataset
# --------------------------------
output_path = os.path.join("data", "features_prematch_full.csv")
final.to_csv(output_path, index=False)
print(f"✅ Saved full predictive dataset → {output_path} ({len(final)} rows)")
