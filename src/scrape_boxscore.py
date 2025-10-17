import os
import csv
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# ---------------------------------------------
# SELENIUM SETUP
# ---------------------------------------------
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


# ---------------------------------------------
# SCRAPE ONE BOX SCORE PAGE (FIXED)
# ---------------------------------------------
def scrape_boxscore(driver, match_info):
    url = match_info["url"]
    print(f"\nScraping boxscore → {url}")
    driver.get(url)

    try:
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.player-name"))
        )
    except Exception:
        print("  ⚠️ Timed out waiting for player table to load.")
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        return []

    time.sleep(2)
    all_rows = []

    # Find all tables that contain players
    tables = driver.find_elements(By.CSS_SELECTOR, "table")
    print(f"  🧩 Found {len(tables)} tables total on page")

    # Label the first table as HOME, second as AWAY
    team_labels = [(match_info["home_team"], "home"), (match_info["away_team"], "away")]

    valid_tables = []
    for tbl in tables:
        # Only keep tables that actually contain player names
        if tbl.find_elements(By.CSS_SELECTOR, "a.player-name"):
            valid_tables.append(tbl)

    print(f"  🧾 Found {len(valid_tables)} valid player tables")

    for idx, tbl in enumerate(valid_tables):
        if idx >= len(team_labels):
            break  # safety

        team_name, side = team_labels[idx]
        header_cells = tbl.find_elements(By.CSS_SELECTOR, "thead th")
        headers = [h.text.strip().upper() for h in header_cells if h.text.strip()]

        tbody = tbl.find_element(By.TAG_NAME, "tbody")
        trs = tbody.find_elements(By.TAG_NAME, "tr")

        for tr in trs:
            try:
                th = tr.find_element(By.TAG_NAME, "th")

                player_name = ""
                position = ""
                number = ""

                try:
                    player_name = th.find_element(By.CSS_SELECTOR, "a.player-name").text.strip()
                except:
                    pass
                try:
                    position = th.find_element(By.CSS_SELECTOR, "span.position").text.strip()
                except:
                    pass
                try:
                    number = th.find_element(By.CSS_SELECTOR, "span.uniform").text.strip()
                except:
                    pass

                if not player_name:
                    continue

                tds = [td.text.strip() for td in tr.find_elements(By.TAG_NAME, "td")]

                player_data = {
                    "season": match_info["season"],
                    "match_id": match_info["match_id"],
                    "date": match_info["date"],
                    "home_team": match_info["home_team"],
                    "away_team": match_info["away_team"],
                    "team": team_name,
                    "team_side": side,
                    "player": player_name,
                    "number": number,
                    "position": position,
                }

                # Add numeric/stat columns
                for i, stat in enumerate(tds):
                    if i < len(headers):
                        player_data[headers[i]] = stat
                    else:
                        player_data[f"STAT_{i+1}"] = stat

                all_rows.append(player_data)

            except Exception:
                continue

    print(f"  ✅ Found {len(all_rows)} player entries for {match_info['match_id']}")
    return all_rows


# ---------------------------------------------
# MAIN SCRIPT
# ---------------------------------------------
def main():
    matches_path = "data/matches_all.csv"
    if not os.path.exists(matches_path):
        print("⚠️ Missing data/matches_all.csv file.")
        return

    df = pd.read_csv(matches_path)
    url_col = None
    for col in df.columns:
        if col.lower() in ["url", "boxscore_url", "link"]:
            url_col = col
            break
    if not url_col:
        print("⚠️ No URL column found in matches_all.csv")
        return

    driver = get_driver()
    all_players = []

    for _, row in df.iterrows():
        if not str(row[url_col]).startswith("http"):
            continue

        match_info = {
            "match_id": row.get("match_id", ""),
            "season": row.get("season", ""),
            "date": row.get("date", ""),
            "home_team": row.get("home_team", ""),
            "away_team": row.get("away_team", ""),
            "url": row[url_col],
        }

        players = scrape_boxscore(driver, match_info)
        all_players.extend(players)
        time.sleep(1.5)

    driver.quit()

    os.makedirs("data", exist_ok=True)
    out_path = "data/match_boxscores_detailed.csv"

    # Collect all columns dynamically
    all_keys = set()
    for r in all_players:
        all_keys.update(r.keys())
    fieldnames = sorted(list(all_keys))

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_players)

    print(f"\n✅ Saved {len(all_players)} total player rows → {out_path}")


if __name__ == "__main__":
    main()
