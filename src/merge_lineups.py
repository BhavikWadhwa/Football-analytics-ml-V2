# src/merge_lineups.py
import pandas as pd
from pathlib import Path

def main():
    base = Path("data/per_season")
    files = sorted(base.glob("team_lineups_*.csv"))
    parts = []
    for f in files:
        df = pd.read_csv(f)
        # standardize headers
        df.columns = [c.strip().lower() for c in df.columns]
        parts.append(df)
    all_df = pd.concat(parts, ignore_index=True)
    # basic cleaning
    for c in ["gp","gs","goals","assists","points","number"]:
        if c in all_df.columns:
            all_df[c] = pd.to_numeric(all_df[c], errors="coerce").fillna(0)
    all_df.to_csv("data/team_lineups_all.csv", index=False)
    print(f"✅ merged {len(parts)} files → data/team_lineups_all.csv  rows={len(all_df)}")

if __name__ == "__main__":
    main()
