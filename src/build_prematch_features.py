"""
build_prematch_features.py
----------------------------------
Builds predictive pre-match features using rolling averages of
team performance from the last 3 matches (or fewer if limited data).
Keeps all rows and fills early matches with team or global averages.
"""

import os
import pandas as pd

# --------------------------------
# 1. Load main enriched dataset
# --------------------------------
data_path = os.path.join("data", "features_enriched.csv")
df = pd.read_csv(data_path)

print(f"✅ Loaded dataset with {len(df)} rows and {len(df.columns)} columns")

# --------------------------------
# 2. Sort for correct temporal order
# --------------------------------
# Make sure date is treated consistently
df["date"] = df["date"].astype(str)
df = df.sort_values(["season", "team", "date"])

# --------------------------------
# 3. Select columns for rolling averages
# --------------------------------
stats_cols = ["shots", "sog", "assists", "player_count", "avg_player_year"]

# --------------------------------
# 4. Compute rolling averages for previous 3 matches
# --------------------------------
for col in stats_cols:
    df[f"{col}_rolling3"] = (
        df.groupby(["season", "team"])[col]
        .transform(lambda x: x.shift(1).rolling(window=3, min_periods=1).mean())
    )

# --------------------------------
# 5. Fill missing rolling values intelligently
# --------------------------------
# If a team’s first few matches don’t have previous data, fill with that team’s mean.
for col in stats_cols:
    roll_col = f"{col}_rolling3"
    df[roll_col] = df.groupby(["team"])[roll_col].transform(
        lambda x: x.fillna(x.mean())
    )

# Any remaining NaNs (e.g., new teams) → fill with global mean
df.fillna(df.mean(numeric_only=True), inplace=True)

# --------------------------------
# 6. Sanity check
# --------------------------------
print("✅ Rolling averages created:")
print(df[[f"{c}_rolling3" for c in stats_cols]].head())

# --------------------------------
# 7. Save predictive dataset
# --------------------------------
output_path = os.path.join("data", "features_prematch.csv")
df.to_csv(output_path, index=False)
print(f"✅ Saved pre-match dataset → {output_path} ({len(df)} rows)")
