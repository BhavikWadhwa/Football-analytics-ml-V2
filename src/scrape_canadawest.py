# src/scrape_canadawest.py
# -----------------------------------------------------------
# v2 Scraper: Multi-season Canada West (Men's Soccer)
# - Collects match summaries from schedule pages
# - Follows boxscore links to extract player lineups + advanced stats
# - Saves two CSVs:
#     data/matches_all.csv  (one row per match)
#     data/lineups_all.csv  (one row per player per match)
# -----------------------------------------------------------

import csv
import os
import re
import time
import random
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter, Retry

# ---------- Config ----------

SEASONS = {
    "2025-26": "https://canadawest.org/sports/msoc/2025-26/schedule",
    "2024-25": "https://canadawest.org/sports/msoc/2024-25/schedule",
    "2023-24": "https://canadawest.org/sports/msoc/2023-24/schedule",
}

OUT_MATCHES = "data/matches_all.csv"
OUT_LINEUPS = "data/lineups_all.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    )
}

REQUESTS_TIMEOUT = 25
REQUESTS_SLEEP_RANGE = (0.8, 1.8)  # polite delay between requests (seconds)
MAX_PER_SEASON = None  # set to an int to limit for quick tests, e.g., 10

# ---------- Data models ----------

@dataclass
class MatchRow:
    match_id: str
    season: str
    date: str
    home_team: str
    away_team: str
    home_goals: Optional[int]
    away_goals: Optional[int]
    boxscore_url: str

@dataclass
class LineupRow:
    match_id: str
    season: str
    team: str
    player: str
    position: str
    minutes: Optional[int]
    goals: Optional[int]
    assists: Optional[int]
    shots: Optional[int]
    shots_on_goal: Optional[int]
    yellow_cards: Optional[int]
    red_cards: Optional[int]

# ---------- HTTP session with retries ----------

def build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    retries = Retry(
        total=3,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s

SESSION = build_session()

# ---------- Utilities ----------

def sleep_polite():
    time.sleep(random.uniform(*REQUESTS_SLEEP_RANGE))

def to_int(s: Optional[str]) -> Optional[int]:
    if s is None:
        return None
    s = s.strip()
    if s == "" or s.lower() in {"na", "n/a", "-"}:
        return None
    try:
        return int(re.sub(r"[^\d-]", "", s))
    except Exception:
        return None

def clean_text(el) -> str:
    if not el:
        return ""
    return re.sub(r"\s+", " ", el.get_text(strip=True))

def make_match_id(season: str, date: str, home: str, away: str) -> str:
    """Stable ID using season + date + teams (slugified)."""
    def slug(x: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", x.lower()).strip("-")
    return f"{slug(season)}__{slug(date)}__{slug(home)}__{slug(away)}"

# ---------- Schedule parsing ----------

def fetch_html(url: str) -> Optional[BeautifulSoup]:
    try:
        resp = SESSION.get(url, timeout=REQUESTS_TIMEOUT)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except requests.HTTPError as e:
        print(f"  ! HTTP error for {url}: {e}")
    except Exception as e:
        print(f"  ! Error fetching {url}: {e}")
    return None

def parse_schedule_page(soup: BeautifulSoup, season: str, base_url: str) -> List[Dict]:
    """
    Returns a list of dicts with:
      date, home_team, away_team, home_goals, away_goals, boxscore_url
    """
    matches: List[Dict] = []

    # Each game row (from your v1 inspection)
    rows = soup.select("tr.event-row")
    for row in rows:
        # Date is in a nearby parent with data-date
        date_el = row.find_previous("div", class_="section-event-date")
        date = date_el.get("data-date", "Unknown") if date_el else "Unknown"

        # Teams (two spans with flex-md-grow-1)
        team_spans = row.select("span.flex-md-grow-1")
        if len(team_spans) != 2:
            continue
        away_team = clean_text(team_spans[0])
        home_team = clean_text(team_spans[1])

        # Scores (two spans.result) – may be empty for future fixtures
        score_spans = row.select("span.result")
        home_goals, away_goals = None, None
        if len(score_spans) == 2:
            away_goals = to_int(score_spans[0].get_text())
            home_goals = to_int(score_spans[1].get_text())

        # Boxscore link (anchor containing 'boxscores')
        box_a = row.select_one("a[href*='boxscores']")
        box_href = urljoin(base_url, box_a.get("href")) if box_a and box_a.get("href") else ""

        matches.append({
            "season": season,
            "date": date,
            "home_team": home_team,
            "away_team": away_team,
            "home_goals": home_goals,
            "away_goals": away_goals,
            "boxscore_url": box_href
        })
    return matches

# ---------- Boxscore lineup parsing ----------

def fetch_boxscore(url: str) -> Optional[BeautifulSoup]:
    if not url:
        return None
    try:
        resp = SESSION.get(url, timeout=REQUESTS_TIMEOUT)
        # Some boxscore endpoints may masquerade as .xml but return HTML.
        # We'll treat everything as HTML; if blocked (403), return None.
        if resp.status_code == 403:
            print(f"    - Boxscore blocked (403): {url}")
            return None
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        print(f"    - Error fetching boxscore {url}: {e}")
        return None

def detect_lineup_tables(soup: BeautifulSoup) -> List[Tuple[str, BeautifulSoup]]:
    """
    Heuristically find lineup tables for both teams.
    Returns list of (team_name, table_element).
    We look for tables whose headers contain Player/Pos/Min/G/A/S/SOG/YC/RC.
    """
    results = []
    # Try common table patterns
    tables = soup.select("table, .table, table.table")
    wanted_headers = {"player", "pos", "minutes", "min", "g", "a", "s", "sog", "yc", "rc"}

    for tbl in tables:
        thead = tbl.find("thead")
        headers = []
        if thead:
            headers = [clean_text(th).lower() for th in thead.select("th")]
        else:
            # Sometimes header is first row of tbody
            first_tr = tbl.select_one("tbody tr")
            if first_tr:
                headers = [clean_text(td).lower() for td in first_tr.select("td")]

        if not headers:
            continue

        # Enough overlap with expected lineup headers?
        norm = set(h.replace(".", "").strip() for h in headers)
        if len(norm & wanted_headers) >= 3:
            # Try to locate a caption or a preceding heading for team name
            team_name = ""
            cap = tbl.find("caption")
            if cap:
                team_name = clean_text(cap)
            if not team_name:
                # Look up to find a heading near the table
                h = tbl.find_previous(["h2", "h3", "h4", "h5"])
                if h:
                    team_name = clean_text(h)
            results.append((team_name, tbl))

    return results

def parse_lineup_table(table, team_name, match_id, season):
    """Parse a PrestoSports lineup table for a single team (home or away)."""
    rows = []
    tbody = table.find("tbody")
    if not tbody:
        return rows  # no player data present

    # --- detect stat columns dynamically ---
    headers = [th.get_text(strip=True).lower() for th in table.select("thead th")]
    # normalize header names
    header_map = {
        "player": "player",
        "pos": "position",
        "position": "position",
        "sh": "shots",
        "shot": "shots",
        "sog": "shots_on_goal",
        "g": "goals",
        "a": "assists",
        "yc": "yellow_cards",
        "rc": "red_cards",
    }

    # assign index-based mapping for the <td> columns
    td_indices = {}
    for i, h in enumerate(headers):
        key = header_map.get(h, None)
        if key:
            td_indices[key] = i

    for tr in tbody.select("tr"):
        try:
            # extract player + position (nested inside <th>)
            player_tag = tr.select_one("a.player-name")
            player_name = player_tag.get_text(strip=True) if player_tag else ""

            pos_tag = tr.select_one("span.position")
            position = pos_tag.get_text(strip=True) if pos_tag else ""

            # now get all <td> cells (stats)
            tds = tr.select("td")

            def get_td_stat(label):
                """Safely extract numeric stat from td by mapped index."""
                idx = td_indices.get(label, None)
                if idx is None or idx >= len(tds):
                    return 0
                text = tds[idx].get_text(strip=True)
                return int(text) if text.isdigit() else 0

            shots = get_td_stat("shots")
            sog = get_td_stat("shots_on_goal")
            goals = get_td_stat("goals")
            assists = get_td_stat("assists")
            yc = get_td_stat("yellow_cards")
            rc = get_td_stat("red_cards")

            # minutes aren’t directly listed — leave blank for now
            minutes = ""

            if player_name:
                rows.append({
                    "match_id": match_id,
                    "season": season,
                    "team": team_name,
                    "player": player_name,
                    "position": position,
                    "minutes": minutes,
                    "goals": goals,
                    "assists": assists,
                    "shots": shots,
                    "shots_on_goal": sog,
                    "yellow_cards": yc,
                    "red_cards": rc,
                })
        except Exception as e:
            print("   ⚠️  Failed to parse a player row:", e)
            continue

    return rows


# ---------- CSV IO ----------

def ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def write_matches(rows: List[MatchRow], out_csv: str):
    ensure_dir(out_csv)
    write_header = not os.path.exists(out_csv)
    with open(out_csv, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(MatchRow.__dataclass_fields__.keys()))
        if write_header:
            w.writeheader()
        for r in rows:
            w.writerow(asdict(r))

def write_lineups(rows: List[LineupRow], out_csv: str):
    ensure_dir(out_csv)
    write_header = not os.path.exists(out_csv)
    with open(out_csv, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(LineupRow.__dataclass_fields__.keys()))
        if write_header:
            w.writeheader()
        for r in rows:
            w.writerow(r)


# ---------- Orchestration ----------

def process_season(season: str, schedule_url: str):
    print(f"\n=== Season {season} ===")
    soup = fetch_html(schedule_url)
    if not soup:
        print("  ! Skipping season (could not fetch schedule).")
        return

    # 1) Collect matches from the schedule
    raw_matches = parse_schedule_page(soup, season, schedule_url)
    if MAX_PER_SEASON:
        raw_matches = raw_matches[:MAX_PER_SEASON]

    season_match_rows: List[MatchRow] = []
    for m in raw_matches:
        match_id = make_match_id(season, m["date"], m["home_team"], m["away_team"])
        season_match_rows.append(MatchRow(
            match_id=match_id,
            season=season,
            date=m["date"],
            home_team=m["home_team"],
            away_team=m["away_team"],
            home_goals=m["home_goals"],
            away_goals=m["away_goals"],
            boxscore_url=m["boxscore_url"],
        ))

    print(f"  - Found {len(season_match_rows)} matches on schedule.")
    write_matches(season_match_rows, OUT_MATCHES)

    # 2) For each match, try to fetch boxscore and parse lineups
    total_lineups = 0
    for i, mr in enumerate(season_match_rows, start=1):
        if not mr.boxscore_url:
            continue

        print(f"  [{i}/{len(season_match_rows)}] Boxscore: {mr.boxscore_url}")
        soup_box = fetch_boxscore(mr.boxscore_url)
        sleep_polite()
        if not soup_box:
            continue

        # Try to infer team names around tables if captions don't exist
        tables = detect_lineup_tables(soup_box)
        if not tables:
            # No clearly detected lineup tables; move on
            continue

        # Heuristic: if table caption/heading is empty, fall back to home/away guess
        # We'll look for team labels on the page to map order.
        team_labels = [mr.home_team, mr.away_team]
        found_lineups: List[LineupRow] = []

        for idx, (team_name, tbl) in enumerate(tables):
            team_guess = team_name or (team_labels[idx] if idx < len(team_labels) else "")
            found_lineups.extend(parse_lineup_table(tbl, team_guess, mr.match_id, season))


        if found_lineups:
            write_lineups(found_lineups, OUT_LINEUPS)
            total_lineups += len(found_lineups)

    print(f"  - Saved lineups rows: {total_lineups}")

def main():
    # Fresh run? Uncomment to wipe outputs each time:
    # for p in (OUT_MATCHES, OUT_LINEUPS):
    #     if os.path.exists(p):
    #         os.remove(p)

    for season, url in SEASONS.items():
        process_season(season, url)

    print("\nDone.")

if __name__ == "__main__":
    main()
