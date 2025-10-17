# Football Match Prediction & Lineup Analysis

### Built by [Bhavik Wadhwa](https://github.com/bhavikwadhwa)

A complete end-to-end football analytics platform that combines **data scraping, machine learning, and interactive visualization**.  
It predicts match outcomes in Canada West soccer and simulates **how changing player lineups could alter the result** built with Python, Pandas, Scikit-learn, and Streamlit.

---

## Overview

This project began as a simple **match prediction model (v1)** using basic statistics like goals and shots.  
Over time, it evolved into a **multi-stage analytics system** that now includes:

- automated scraping of **match boxscores, lineups, and player stats** for three seasons (2023–24 to 2025–26),  
- intelligent **feature engineering** that merges team and player data,  
- multiple trained models one for **pre-match prediction** and one for **post-match lineup analysis**,  
- an interactive **Streamlit dashboard** with visual analytics, team comparisons, and lineup swap simulations.

---

## Core Idea

The model uses historical match and player data from the [Canada West Soccer](https://canadawest.org/sports/msoc) site to predict outcomes (`Win`, `Loss`, or `Draw`) based on:

- team form metrics (shots, assists, possession proxies),
- player experience (average year, lineup count),
- home vs away advantage,
- rolling averages across recent matches,
- and player-level performance aggregates.

After prediction, users can simulate **“what-if” lineup changes** to see how replacing one player affects the team’s win probability.

---

## Features

### Data Pipeline
- **Web Scraping** using custom scripts built with `requests` and `BeautifulSoup` to extract match, team, and player stats.
- **Data Cleaning** with Pandas to remove duplicates, normalize team names, and merge across seasons.
- **Feature Engineering**:
  - Created rolling averages (`shots_rolling3`, `win_rate_rolling5`, etc.),
  - Generated per-player and per-team aggregates (goals, assists, SOG),
  - Added opponent differential stats for predictive modeling.

### Machine Learning
- **Model 1: Predictive Model** — trained on pre-match team features to predict match results.
- **Model 2: Post-Match Analytic Model** — used for evaluating how lineup swaps alter outcomes.
- Used `RandomForestClassifier` for interpretability and consistent performance.
- Typical Accuracy:
  - v1: ~57%
  - v2: up to **96%** after adding enriched player features.

### Architecture
data/
┣ match_boxscores_detailed_cleaned.csv
┣ features_prematch_full.csv
┣ features_enriched.csv
┣ team_lineups_clean.csv
┗ swap_scenarios/ ← stores saved simulations
models/
┣ random_forest_predictive.pkl
┗ random_forest_postmatch.pkl
src/
┣ scrape_canadawest.py
┣ build_features.py
┣ merge_player_features.py
┣ train_model_predictive.py
┗ train_model.py
app.py
requirements.txt
README.md


---

## Streamlit Application

### Tab 1 **Match Prediction**
Predicts outcomes between two teams before kickoff.

Includes:
- **Win/Draw/Loss probability cards**
- **Donut chart** for outcome distribution
- **Bar chart** with probabilities
- **Radar chart** comparing recent team form
- **Feature Importance** visualization
- **League Context** scatter plot showing how the selected teams compare across all matches

### Tab 2 **Player Swap Analysis**
Simulates the impact of changing a player in the lineup.

Includes:
- Team dropdowns **auto-filtered by match**
- Lineup tables with player stats
- **Before vs After** grouped bar chart
- **Animated transition chart**
- **Radar chart** comparing stat profiles
- **Delta table** showing stat differences
- Option to **save scenarios** to `/data/swap_scenarios/`

---

## Technology Stack

| Layer | Technologies |
|-------|---------------|
| **Language** | Python 3.11 |
| **Data Handling** | Pandas, NumPy |
| **Machine Learning** | scikit-learn |
| **Visualization** | Plotly, Streamlit |
| **Data Collection** | Requests, BeautifulSoup |
| **Environment** | Virtualenv |
| **Version Control** | Git + GitHub |

---

## Major Challenges & Solutions

### 1. **Data Duplication & Inconsistent Boxscores**
- **Challenge:** The scraped boxscore dataset initially had 16,000+ duplicate player entries.
- **Solution:** Added a `drop_duplicates.py` cleaning script with unique `match_id + player + team` logic.

### 2. **Merging Lineups Across Seasons**
- **Challenge:** Each CSV used a slightly different schema (e.g., “thompson-rivers” vs “Thompson Rivers”).
- **Solution:** Standardized team names and merged by unified `match_id` strings across all three seasons.

### 3. **Missing Player Stats**
- **Challenge:** Player-level data didn’t include per-match aggregates (`G_mean`, `SOG_mean`, etc.).
- **Solution:** Created a post-processing step to **calculate mean, sum, and max stats** dynamically before training.

### 4. **Model Overfitting**
- **Challenge:** When adding too many features, accuracy spiked unrealistically (e.g., 97%).
- **Solution:** Separated **predictive vs analytic models**, used stratified train/test split, and verified on unseen season data.

### 5. **Dynamic Team Matching in Streamlit**
- **Challenge:** Selecting teams not in a chosen match led to “No Data Found.”
- **Solution:** Implemented **auto-filtering** so that only the two valid teams per match appear.

### 6. **Feature Mismatch Errors During Swaps**
- **Challenge:** The analytic model required strict feature columns; missing ones caused runtime errors.
- **Solution:** Implemented automatic **feature alignment** that fills missing features with zeros before prediction.

### 7. **Frontend Performance**
- **Challenge:** Plotly and Streamlit rendering slowed with 500+ matches.
- **Solution:** Used **`@st.cache_resource` and `@st.cache_data`** to cache models and datasets for smooth UI performance.

### 8. **Visual Polish**
- **Challenge:** Early versions were functional but looked raw.
- **Solution:** Designed a **professional dark UI**, added **team logos**, KPI cards, and consistent Plotly theming.

---

## Results

- **500+ matches** across 3 seasons integrated.
- Realistic, data-driven **match outcome predictions**.
- Full **player-swap impact simulation**.
- **Reusable modular code**: each step from scraping → cleaning → modeling → app is independent.

---

## How to Run


### 1. Clone the repository
```bash
git clone https://github.com/bhavikwadhwa/football-prediction-app
cd football-prediction-app
```

### 2. Create and activate a virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate   # on Windows
```


### 3. Install dependencies
```bash
pip install -r requirements.txt
```


### 4. Run the Streamlit app
```bash
streamlit run app.py

Future Improvements

Integrate xG (Expected Goals) and possession data if available.

Add real-time match updates and predictive recalibration.

Deploy via Streamlit Cloud or Render.

Add player comparison profiles and interactive timelines.

Build an AI-powered commentary generator based on match data.
```

### Summary

This project combines data engineering, machine learning, and UI design to showcase what’s possible when analytics meets sports insight.
It represents three complete development cycles — from raw scraping to refined modeling and presentation.

### Author

Bhavik Wadhwa
Bachelor of Computer Information Systems, University of the Fraser Valley
Full-stack Developer & Data Enthusiast
