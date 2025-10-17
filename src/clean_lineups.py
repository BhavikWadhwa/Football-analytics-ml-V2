import pandas as pd
import unicodedata
import re

INPUT = "data/team_lineups_all.csv"
OUTPUT = "data/team_lineups_clean.csv"

def normalize_text(s):
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return " ".join(s.split())

def normalize_year(y):
    """Normalize academic year across formats like Fr/So/Jr/Sr/1st/2nd/3rd/4th/5th."""
    if pd.isna(y) or not str(y).strip():
        return (0, "UNK")

    # Clean up text
    y = str(y).strip().lower().replace(".", "")

    mapping_text = {
        "fr": "1st", "frosh": "1st", "freshman": "1st",
        "so": "2nd", "sophomore": "2nd",
        "jr": "3rd", "junior": "3rd",
        "sr": "4th", "senior": "4th",
        "1": "1st", "1st": "1st", "first": "1st",
        "2": "2nd", "2nd": "2nd", "second": "2nd",
        "3": "3rd", "3rd": "3rd", "third": "3rd",
        "4": "4th", "4th": "4th", "fourth": "4th",
        "5": "5th", "5th": "5th", "fifth": "5th"
    }

    year_std = mapping_text.get(y, "UNK")

    mapping_num = {
        "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5,
        "UNK": 0
    }

    return (mapping_num[year_std], year_std)

def normalize_position(p):
    """Return both raw zone (like CB, CDM) and broad group (DEF/MID/FOR/GK)"""
    if pd.isna(p) or not str(p).strip():
        return ("UNK", "UNK")

    p = re.sub(r"[^a-zA-Z/]", "", str(p).upper())

    # handle multi-position (e.g. "CDM/CB")
    main_pos = p.split("/")[0]

    if any(x in main_pos for x in ["GK", "GOAL"]):
        return (main_pos, "GK")

    if any(x in main_pos for x in ["CB","D", "LB", "RB", "DEF", "FB", "WB", "BACK", "CD"]):
        return (main_pos, "DEF")

    if any(x in main_pos for x in ["CM","M", "CDM", "LMF", "RMF", "MF", "MID", "CAM", "AMF"]):
        return (main_pos, "MID")

    if any(x in main_pos for x in ["ST","F", "CF", "FW", "F", "W"]):
        return (main_pos, "FOR")

    return (main_pos, "UNK")

def main():
    df = pd.read_csv(INPUT)
    df.columns = [c.strip().lower() for c in df.columns]

    for col in ["season","team","player"]:
        df[col] = df[col].map(normalize_text)

    year_data = df["year"].apply(normalize_year)
    df["year_num"], df["year_std"] = zip(*year_data)

    # Apply improved position normalization
    pos_data = df["position"].apply(normalize_position)
    df["position_zone"], df["position_group"] = zip(*pos_data)

    # convert numeric cols
    num_cols = ["gp","gs","goals","assists","points"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # drop duplicates
    df = df.drop_duplicates(subset=["season","team","player"], keep="last")

    print("✅ Cleaned:", len(df), "rows")
    print(df[["player", "position", "position_zone", "position_group"]].head(15))

    df.to_csv(OUTPUT, index=False)
    print(f"💾 Saved clean version → {OUTPUT}")

if __name__ == "__main__":
    main()
