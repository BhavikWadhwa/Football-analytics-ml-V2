# app.py — Football Match Prediction & Lineup Analysis (dark theme, logos, polished)

import os
import time
import numpy as np
import pandas as pd
import streamlit as st
import joblib
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ============================================================================
# Page setup & styles
# ============================================================================
st.set_page_config(page_title="Football Match Prediction & Lineup Analysis", layout="wide")

st.markdown("""
<style>
/* Dark base */
:root { --card-bg: #111827; --card-border: #1F2937; --fg: #E5E7EB; --fg-subtle:#9CA3AF; --accent:#60A5FA; }
html,body,[class*="css"] { background-color: #0E1117 !important; color: var(--fg) !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] button { color: var(--fg-subtle); font-weight: 600; }
.stTabs [aria-selected="true"] { color: var(--accent) !important; border-bottom: 3px solid var(--accent) !important; }

/* Cards */
.card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 14px; padding: 16px; }
.kpi-title { margin:0 0 4px 0; color:#D1D5DB; font-size:14px; }
.kpi-value { margin:0; font-size:28px; font-weight:800; color:#F9FAFB; }

/* Plots */
.stPlotlyChart { background: var(--card-bg); border-radius: 12px; padding: 6px; }

/* Headings */
h1,h2,h3 { color: #F9FAFB; }

/* Dataframe */
div[data-testid="stDataFrame"] { background: var(--card-bg); border-radius:10px; }

.logo-wrap { display:flex; align-items:center; gap:10px; }
.logo-wrap img { width:28px; height:28px; border-radius:50%; object-fit:cover; border:1px solid #374151; }
.logo-wrap span { font-weight:700; text-transform:uppercase; letter-spacing:.5px; }
</style>
""", unsafe_allow_html=True)

st.title("Football Match Prediction & Lineup Analysis")

PLOTLY_TEMPLATE = "plotly_dark"

# ============================================================================
# Helpers
# ============================================================================
def safe_load_csv(path_candidates):
    for p in path_candidates:
        if os.path.exists(p):
            return pd.read_csv(p)
    st.warning(f"Missing file: tried {path_candidates}")
    return pd.DataFrame()

def readable_labels(classes):
    if all(isinstance(c, (int, np.integer)) for c in classes):
        m = {0: "Draw", 1: "Loss", 2: "Win"}
        return [m.get(int(c), str(c)) for c in classes]
    return [str(c).capitalize() for c in classes]

def kpi_card(col, title, value):
    with col:
        st.markdown(f"""
        <div class="card">
          <div class="kpi-title">{title}</div>
          <div class="kpi-value">{value}</div>
        </div>""", unsafe_allow_html=True)

def load_logo(team_slug):
    # expects team slug lowercased (e.g., "ubc")
    p = os.path.join("data", "logos", f"{team_slug}.png")
    return p if os.path.exists(p) else None

def team_header_with_logo(team_slug):
    logo = load_logo(team_slug)
    if logo:
        st.markdown(f"""
        <div class="logo-wrap">
           <img src="file://{os.path.abspath(logo)}" />
           <span>{team_slug}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='logo-wrap'><span>{team_slug}</span></div>", unsafe_allow_html=True)

def ensure_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def feature_importance_bar(model, feature_names, title):
    if not hasattr(model, "feature_importances_"):
        return go.Figure()
    imp = model.feature_importances_
    order = np.argsort(imp)[::-1]
    fn = [feature_names[i] for i in order]
    iv = [imp[i] for i in order]
    fig = px.bar(x=iv, y=fn, orientation="h", title=title, template=PLOTLY_TEMPLATE)
    fig.update_layout(xaxis_title="Importance", yaxis_title="Feature", margin=dict(l=120))
    return fig

def context_scatter(prematch, xcol, ycol, home_team, away_team):
    df = prematch.copy()
    df = ensure_numeric(df, [xcol, ycol])
    df = df.dropna(subset=[xcol, ycol])
    fig = px.scatter(df, x=xcol, y=ycol, opacity=0.35, template=PLOTLY_TEMPLATE,
                     title=f"League Context: {ycol} vs {xcol}")
    # highlight selected teams' latest rows
    for t, color in [(home_team, "#60A5FA"), (away_team, "#F59E0B")]:
        dft = df[df["team"] == t].sort_values("date")
        if not dft.empty:
            point = dft.iloc[-1]
            fig.add_trace(go.Scatter(x=[point[xcol]], y=[point[ycol]], mode="markers+text",
                                     text=[t.upper()], textposition="top center",
                                     marker=dict(size=12, color=color), name=t.upper()))
    fig.update_traces(showlegend=False)
    return fig

def radar_compare_matrix(series_dict, title):
    # series_dict: {"LABEL":[v1,v2,v3,v4], "LABEL2":[...]}
    metrics = ["Shots", "Shots on Goal", "Assists", "Avg Player Year"]
    comp = pd.DataFrame({"Metric": metrics})
    for label, vals in series_dict.items():
        comp[label] = vals
    numeric = comp.drop(columns=["Metric"]).select_dtypes(include=[np.number])
    max_val = (numeric.to_numpy().max() if not numeric.empty else 1.0) * 1.05

    fig = go.Figure()
    for label in series_dict.keys():
        fig.add_trace(go.Scatterpolar(r=comp[label], theta=comp["Metric"],
                                      fill='toself', name=label.upper()))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max_val])),
                      showlegend=True, template=PLOTLY_TEMPLATE, title=title)
    return fig

def animated_swap_bar(labels, before, after, title):
    df = pd.DataFrame({
        "Outcome": list(labels) * 2,
        "Probability": np.concatenate([before, after]),
        "Scenario": ["Before"] * len(labels) + ["After"] * len(labels)
    })
    fig = px.bar(df, x="Outcome", y="Probability", color="Scenario",
                 animation_frame="Scenario", range_y=[0, 1],
                 text="Probability", title=title, template=PLOTLY_TEMPLATE)
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(transition={"duration": 500})
    return fig

# ============================================================================
# Load models & data (cached)
# ============================================================================
@st.cache_resource
def load_models():
    pred = joblib.load("models/random_forest_predictive.pkl")
    ana  = joblib.load("models/random_forest_postmatch.pkl")
    return pred, ana

@st.cache_data
def load_data():
    players = safe_load_csv([
        "data/match_boxscore_detailed_cleaned.csv",
        "data/match_boxscores_detailed_cleaned.csv"
    ])
    prematch = safe_load_csv(["data/features_prematch_full.csv"])
    enriched = safe_load_csv(["data/features_enriched.csv"])

    for df in [players, prematch, enriched]:
        if "team" in df.columns:
            df["team"] = df["team"].astype(str).str.lower().str.strip()
        if "match_id" in df.columns:
            df["match_id"] = df["match_id"].astype(str).str.strip()
        if "date" in df.columns:
            df["date"] = df["date"].astype(str)

    return players, prematch, enriched

model_predictive, model_analytic = load_models()
players, prematch, enriched = load_data()

# ============================================================================
# Tabs
# ============================================================================
tab_pred, tab_swap = st.tabs(["Match Prediction", "Player Swap Analysis"])

# ----------------------------------------------------------------------------
# TAB 1 — Match Prediction
# ----------------------------------------------------------------------------
with tab_pred:
    st.subheader("Pre-match Prediction")

    teams = sorted(prematch["team"].unique())
    csel = st.columns(2)
    home_team = csel[0].selectbox("Home Team", teams, index=0)
    away_team = csel[1].selectbox("Away Team", teams, index=1 if len(teams) > 1 else 0)

    def latest_form(team):
        df = prematch[prematch["team"] == team].sort_values("date")
        return df.iloc[-1] if len(df) else None

    home = latest_form(home_team)
    away = latest_form(away_team)

    if (home is None) or (away is None):
        st.warning("Not enough form data for one or both teams.")
    else:
        # Logos row
        cl = st.columns(2)
        with cl[0]: team_header_with_logo(home_team)
        with cl[1]: team_header_with_logo(away_team)

        # Build predictive feature row
        def val(s): return float(s) if pd.notna(s) else 0.0

        form_diff = {
            "shots_form_diff":   val(home["shots_rolling3"]) - val(away["shots_rolling3"]),
            "sog_form_diff":     val(home["sog_rolling3"]) - val(away["sog_rolling3"]),
            "assists_form_diff": val(home["assists_rolling3"]) - val(away["assists_rolling3"]),
            "player_count_form_diff": val(home["player_count_rolling3"]) - val(away["player_count_rolling3"]),
            "avg_player_year_form_diff": val(home["avg_player_year_rolling3"]) - val(away["avg_player_year_rolling3"]),
            "win_rate_diff":     val(home["win_rate_rolling5"]) - val(away["win_rate_rolling5"])
        }

        row = pd.DataFrame([{
            "shots_rolling3": val(home["shots_rolling3"]),
            "sog_rolling3": val(home["sog_rolling3"]),
            "assists_rolling3": val(home["assists_rolling3"]),
            "player_count_rolling3": val(home["player_count_rolling3"]),
            "avg_player_year_rolling3": val(home["avg_player_year_rolling3"]),
            "win_rate_rolling5": val(home["win_rate_rolling5"]),
            "is_home": 1,
            "for": val(home["for"]),
            "mid": val(home["mid"]),
            **form_diff
        }])

        # Ensure correct column order
        feat_order = list(getattr(model_predictive, "feature_names_in_", row.columns))
        for f in feat_order:
            if f not in row.columns:
                row[f] = 0.0
        row = row[feat_order]

        probs = model_predictive.predict_proba(row)[0]
        labels = readable_labels(model_predictive.classes_)

        # KPI
        k1,k2,k3 = st.columns(3)
        p_map = dict(zip(labels, probs))
        kpi_card(k1, "Win probability", f"{p_map.get('Win',0):.1%}")
        kpi_card(k2, "Draw probability", f"{p_map.get('Draw',0):.1%}")
        kpi_card(k3, "Loss probability", f"{p_map.get('Loss',0):.1%}")

        # Row: donut + bar
        cc = st.columns([1,2])
        with cc[0]:
            fig_d = go.Figure(data=[go.Pie(labels=labels, values=probs, hole=0.6, textinfo="label+percent")])
            fig_d.update_layout(template=PLOTLY_TEMPLATE, title="Outcome Distribution", showlegend=False)
            st.plotly_chart(fig_d, use_container_width=True)
        with cc[1]:
            df_bar = pd.DataFrame({"Outcome": labels, "Probability": probs})
            fig_b = px.bar(df_bar, x="Outcome", y="Probability", color="Outcome",
                           text="Probability", template=PLOTLY_TEMPLATE,
                           title=f"Predicted Outcome: {home_team.upper()} vs {away_team.upper()}")
            fig_b.update_traces(texttemplate="%{text:.2f}", textposition="outside")
            fig_b.update_layout(yaxis=dict(range=[0,1]), showlegend=False)
            st.plotly_chart(fig_b, use_container_width=True)

        # Radar comparison
        st.subheader("Team Form Comparison")
        series = {
            home_team: [val(home["shots_rolling3"]), val(home["sog_rolling3"]),
                        val(home["assists_rolling3"]), val(home["avg_player_year_rolling3"])],
            away_team: [val(away["shots_rolling3"]), val(away["sog_rolling3"]),
                        val(away["assists_rolling3"]), val(away["avg_player_year_rolling3"])]
        }
        st.plotly_chart(radar_compare_matrix(series, "Form (last 3/5)"), use_container_width=True)

        # Feature importance
        st.subheader("Model Feature Importance")
        st.plotly_chart(feature_importance_bar(model_predictive, feat_order, "Predictive Model — Feature Importance"),
                        use_container_width=True)

        # Context scatter (league-wide)
        st.subheader("League Context")
        st.plotly_chart(context_scatter(prematch, "shots_rolling3", "win_rate_rolling5", home_team, away_team),
                        use_container_width=True)

# ----------------------------------------------------------------------------
# TAB 2 — Player Swap Analysis
# ----------------------------------------------------------------------------
with tab_swap:
    st.subheader("Player Swap Impact")

    # Match first; restrict teams to those in the match
    match_ids = sorted(enriched["match_id"].unique(), reverse=True)
    match_id = st.selectbox("Select match", match_ids)

    # Determine teams present in this match
    match_rows = enriched[enriched["match_id"] == match_id]
    possible_teams = sorted(match_rows["team"].unique())
    team = st.selectbox("Select team", possible_teams)

    # Show logos for both sides
    col_logo = st.columns(2)
    if len(possible_teams) == 2:
        with col_logo[0]: team_header_with_logo(possible_teams[0])
        with col_logo[1]: team_header_with_logo(possible_teams[1])

    # Load lineup for this match & team
    lineup = players[(players["match_id"] == match_id) & (players["team"] == team)].copy()
    st.subheader(f"Current lineup — {team.upper()}")
    if lineup.empty:
        st.warning("No player data for this match/team combination.")
        st.stop()

    base_stats = ["G", "SH", "SOG", "A"]
    lineup = ensure_numeric(lineup, base_stats)
    st.dataframe(lineup[["number", "player", "position"] + base_stats], use_container_width=True)

    swap_out = st.selectbox("Swap OUT player", lineup["player"].unique())
    pool = players[(players["team"] == team) & (players["match_id"] != match_id)].copy()
    pool = ensure_numeric(pool, base_stats)
    swap_in = st.selectbox("Swap IN player", pool["player"].unique())

    if st.button("Simulate swap"):
        # Original & new averages
        orig_means = lineup[base_stats].mean().fillna(0)
        new_lineup = lineup.copy()
        incoming_stats = pool.loc[pool["player"] == swap_in, base_stats].mean().fillna(0)
        new_lineup.loc[new_lineup["player"] == swap_out, base_stats] = incoming_stats.values
        new_means = new_lineup[base_stats].mean().fillna(0)

        # Enriched row for model
        enriched_row = match_rows[match_rows["team"] == team].copy()
        if enriched_row.empty:
            st.error("No enriched row found for this match/team.")
            st.stop()

        # Update per-match player mean features based on simulated lineup
        mapping = {"G_mean": "G", "SH_mean": "SH", "SOG_mean": "SOG", "A_mean": "A"}
        for fcol, bcol in mapping.items():
            enriched_row[fcol] = float(new_means[bcol])

        try:
            # Ensure expected analytic feature set
            feat_order = list(getattr(model_analytic, "feature_names_in_", enriched_row.columns))
            for f in feat_order:
                if f not in enriched_row.columns:
                    enriched_row[f] = 0.0
            X_new = enriched_row[feat_order].copy()
            X_old = enriched_row.assign(**{k: float(v) for k, v in orig_means.to_dict().items()})[feat_order].copy()

            probs_new = model_analytic.predict_proba(X_new)[0]
            probs_old = model_analytic.predict_proba(X_old)[0]
            labels = readable_labels(model_analytic.classes_)

            # Top section: grouped bar + animated transition
            ctop = st.columns([2, 2])
            with ctop[0]:
                df_m = pd.DataFrame({"Outcome": labels, "Before": probs_old, "After": probs_new}) \
                          .melt(id_vars="Outcome", var_name="Scenario", value_name="Probability")
                fig_group = px.bar(df_m, x="Outcome", y="Probability", color="Scenario",
                                   barmode="group", text="Probability", template=PLOTLY_TEMPLATE,
                                   title="Before vs After")
                fig_group.update_traces(texttemplate="%{text:.2f}", textposition="outside")
                fig_group.update_layout(yaxis=dict(range=[0,1]))
                st.plotly_chart(fig_group, use_container_width=True)
            with ctop[1]:
                st.plotly_chart(
                    animated_swap_bar(labels, probs_old, probs_new, "Animated transition"),
                    use_container_width=True
                )

            # Radar: before vs after team stat means
            st.subheader("Team stat profile (before vs after)")
            series = {
                "Before": [float(orig_means["SH"]), float(orig_means["SOG"]),
                           float(orig_means["A"]), 0.0],  # we don't have avg player year per lineup swap
                "After":  [float(new_means["SH"]), float(new_means["SOG"]),
                           float(new_means["A"]), 0.0]
            }
            st.plotly_chart(radar_compare_matrix(series, "Lineup stat profile"), use_container_width=True)

            # Delta table
            st.subheader("Stat deltas after swap")
            delta = (new_means - orig_means).round(3)
            delta_df = pd.DataFrame({
                "Stat": delta.index,
                "Before": [float(orig_means[s]) for s in delta.index],
                "After": [float(new_means[s]) for s in delta.index],
                "Change": [float(delta[s]) for s in delta.index],
            })
            st.dataframe(delta_df, use_container_width=True)

            # Save scenario
            st.subheader("Save scenario")
            if st.button("Save as CSV"):
                os.makedirs("data/swap_scenarios", exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                out_path = os.path.join("data", "swap_scenarios",
                                        f"{match_id}__{team}__{swap_out}_to_{swap_in}__{ts}.csv")
                pd.DataFrame({
                    "match_id":[match_id],
                    "team":[team],
                    "swap_out":[swap_out],
                    "swap_in":[swap_in],
                    **{f"prob_before_{labels[i].lower()}":[float(probs_old[i])] for i in range(len(labels))},
                    **{f"prob_after_{labels[i].lower()}":[float(probs_new[i])] for i in range(len(labels))},
                    **{f"orig_mean_{k.lower()}":[float(v)] for k,v in orig_means.items()},
                    **{f"new_mean_{k.lower()}":[float(v)] for k,v in new_means.items()},
                }).to_csv(out_path, index=False)
                st.success(f"Saved: {out_path}")

        except Exception as e:
            st.error(f"Error during swap simulation: {e}")
