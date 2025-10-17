import os
import csv
import time
from dataclasses import dataclass

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------------------------
# CONFIG
# ---------------------------------------------
SEASONS = ["2025-26", "2024-25", "2023-24"]  # scrape these seasons

# Team display name -> slug (slug rarely changes; adjust if you hit 404s)
TEAM_SLUGS = {
    "UBC": "ubc",
    "UFV": "ufv",
    "Calgary": "calgary",
    "Victoria": "victoria",
    "UNBC": "unbc",
    "Mount Royal": "mountroyal",
    "Alberta": "alberta",
    "Lethbridge": "lethbridge",
    "Trinity Western": "trinitywestern",
    "Saskatchewan": "saskatchewan",
    "MacEwan": "macewan",
    "UBCO": "ubco",
    "Thompson Rivers": "thompsonrivers",
}

def season_url(season: str, slug: str) -> str:
    # e.g., https://canadawest.org/sports/msoc/2024-25/teams/ubc?view=lineup
    return f"https://canadawest.org/sports/msoc/{season}/teams/{slug}?view=lineup"

def fname_season(season: str) -> str:
    # Filenames can't have slashes; 2025-26 -> 2025_26
    return season.replace("-", "_")

# ---------------------------------------------
# DATA CLASS
# ---------------------------------------------
@dataclass
class PlayerRow:
    season: str
    team: str
    number: str
    player: str
    year: str
    position: str
    gp: str
    gs: str
    goals: str
    assists: str
    points: str

# ---------------------------------------------
# SELENIUM
# ---------------------------------------------
def get_driver():
    options = Options()
    options.add_argument("--headless")  
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# ---------------------------------------------
# CORE SCRAPE (same logic PREVIOSULY working)
# ---------------------------------------------
def scrape_team_lineup(driver, season: str, team_name: str, url: str) -> list[PlayerRow]:
    print(f"[{season}] Scraping lineup for {team_name} ...")
    try:
        driver.get(url)
    except Exception as e:
        print(f"  ⚠️ Navigation error for {team_name}: {e}")
        return []

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
    except:
        print(f"  ⚠️ No table found for {team_name} (timed out)")
        return []

    time.sleep(5)  # give the DataTables JS time to populate

    # Find the target table by header text (POS / GP / PTS etc.)
    tables = driver.find_elements(By.TAG_NAME, "table")
    target_table = None
    for tbl in tables:
        txt = tbl.text
        if ("POS" in txt) or ("Gp" in txt) or ("GP" in txt) or ("PTS" in txt) or ("Pts" in txt):
            target_table = tbl
            break

    if not target_table:
        print(f"  ⚠️ Couldn't locate stats table for {team_name}")
        return []

    try:
        tbody = target_table.find_element(By.TAG_NAME, "tbody")
        tr_elements = tbody.find_elements(By.TAG_NAME, "tr")
    except Exception as e:
        print(f"  ⚠️ Couldn't access tbody for {team_name}: {e}")
        return []

    rows = []
    for tr in tr_elements:
        tds = tr.find_elements(By.TAG_NAME, "td")
        if len(tds) < 5:
            continue

        def safe(td):
            return td.text.strip() if td else ""

        number = safe(tds[0])
        player = safe(tds[1])
        year = safe(tds[2])
        position = safe(tds[3])
        gp = safe(tds[4])
        gs = safe(tds[5]) if len(tds) > 5 else ""
        goals = safe(tds[6]) if len(tds) > 6 else ""
        assists = safe(tds[7]) if len(tds) > 7 else ""
        points = safe(tds[8]) if len(tds) > 8 else ""

        if not player:
            continue

        rows.append(PlayerRow(
            season=season,
            team=team_name,
            number=number,
            player=player,
            year=year,
            position=position,
            gp=gp,
            gs=gs,
            goals=goals,
            assists=assists,
            points=points,
        ))

    print(f"  ✅ [{season}] {team_name}: {len(rows)} players")
    return rows

# ---------------------------------------------
# MAIN
# ---------------------------------------------
def main():
    driver = get_driver()
    combined_all = []

    os.makedirs("data", exist_ok=True)

    for season in SEASONS:
        season_rows = []
        print(f"\n=== Season {season} ===")
        for team_name, slug in TEAM_SLUGS.items():
            url = season_url(season, slug)
            team_rows = scrape_team_lineup(driver, season, team_name, url)
            season_rows.extend(team_rows)
            time.sleep(1.5)  # be polite

        # write per-season file
        out_path_season = f"data/team_lineups_{fname_season(season)}.csv"
        with open(out_path_season, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=PlayerRow.__dataclass_fields__.keys())
            writer.writeheader()
            for r in season_rows:
                writer.writerow(r.__dict__)
        print(f"💾 Saved {len(season_rows)} rows → {out_path_season}")

        combined_all.extend(season_rows)

    driver.quit()

    # write combined file (3 seasons)
    out_all = "data/team_lineups_all.csv"
    with open(out_all, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PlayerRow.__dataclass_fields__.keys())
        writer.writeheader()
        for r in combined_all:
            writer.writerow(r.__dict__)
    print(f"\n✅ Saved {len(combined_all)} total rows across all seasons → {out_all}")

if __name__ == "__main__":
    main()
