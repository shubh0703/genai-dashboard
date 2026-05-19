import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GenAI Usage Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── EPAM Theme CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600;700&display=swap');

    /* ── EPAM Brand Colors ──
       Background:   #1B1F2E  (deep navy)
       Surface:      #252A3A  (card/panel)
       Border:       #333850  (subtle)
       Accent:       #FF6B00  (EPAM orange)
       Accent2:      #CC5500  (hover orange)
       Text primary: #FFFFFF
       Text muted:   #8A93B0
    */

    /* Main background */
    .stApp { background-color: #1B1F2E; color: #FFFFFF; font-family: 'Source Sans Pro', Arial, sans-serif; }
    [data-testid="stAppViewContainer"] { background-color: #1B1F2E; }
    [data-testid="stHeader"] { background-color: #1B1F2E; }
    section[data-testid="stSidebar"] { background-color: #1B1F2E; }

    /* KPI Cards */
    .kpi-card {
        background-color: #252A3A;
        border: 1px solid #333850;
        border-top: 3px solid #FF6B00;
        border-radius: 6px;
        padding: 14px 18px 12px 18px;
        text-align: left;
        height: 110px;
        overflow: hidden;
        font-family: 'Source Sans Pro', Arial, sans-serif;
    }
    .kpi-label {
        font-size: 10px;
        font-family: 'Source Sans Pro', Arial, sans-serif;
        font-weight: 600;
        color: #8A93B0;
        letter-spacing: 1.4px;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: 700;
        font-family: 'Source Sans Pro', Arial, sans-serif;
        color: #FF6B00;
        line-height: 1.15;
    }
    .kpi-value-white {
        font-size: 22px;
        font-weight: 700;
        font-family: 'Source Sans Pro', Arial, sans-serif;
        color: #FFFFFF;
        line-height: 1.15;
    }
    .kpi-sub {
        font-size: 11px;
        font-family: 'Source Sans Pro', Arial, sans-serif;
        color: #FFFFFF;
        margin-top: 5px;
    }
    .kpi-sub-teal {
        font-size: 11px;
        font-family: 'Source Sans Pro', Arial, sans-serif;
        color: #FF6B00;
        margin-top: 5px;
        font-weight: 600;
    }

    /* Section headers */
    .section-header {
        font-size: 11px;
        font-weight: 700;
        font-family: 'Source Sans Pro', Arial, sans-serif;
        color: #8A93B0;
        letter-spacing: 1.6px;
        text-transform: uppercase;
        margin-bottom: 8px;
        padding-bottom: 5px;
        border-bottom: 1px solid #333850;
    }

    /* Dashboard header */
    .dash-header {
        background-color: #252A3A;
        border-radius: 6px;
        padding: 14px 20px;
        margin-bottom: 16px;
        border: 1px solid #333850;
        border-left: 4px solid #FF6B00;
    }
    .dash-title {
        font-size: 20px;
        font-weight: 700;
        font-family: 'Source Sans Pro', Arial, sans-serif;
        color: #FFFFFF;
    }
    .dash-subtitle {
        font-size: 11px;
        font-family: 'Source Sans Pro', Arial, sans-serif;
        color: #8A93B0;
        margin-top: 3px;
    }

    /* Filter bar */
    .filter-bar {
        background-color: #252A3A;
        border-radius: 6px;
        padding: 10px 16px;
        margin-bottom: 16px;
        border: 1px solid #333850;
    }

    /* Selectbox styling */
    .stSelectbox > div > div {
        background-color: #252A3A !important;
        color: #FFFFFF !important;
        border: 1px solid #333850 !important;
        font-family: 'Source Sans Pro', Arial, sans-serif !important;
    }
    .stSelectbox label {
        color: #8A93B0 !important;
        font-size: 11px !important;
        font-family: 'Source Sans Pro', Arial, sans-serif !important;
    }

    /* Table styling */
    .stDataFrame { background-color: #252A3A; }
    thead tr th {
        background-color: #1B1F2E !important;
        color: #8A93B0 !important;
        font-size: 11px !important;
        font-family: 'Source Sans Pro', Arial, sans-serif !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    tbody tr td {
        color: #FFFFFF !important;
        font-size: 13px !important;
        font-family: 'Source Sans Pro', Arial, sans-serif !important;
    }
    tbody tr:hover td { background-color: #2E3448 !important; }

    /* Divider */
    hr { border-color: #333850; }

    /* Metric delta */
    [data-testid="stMetricDelta"] { color: #FF6B00; }

    /* Plotly chart background fix */
    .js-plotly-plot { background-color: transparent !important; }

    /* Refresh button — EPAM orange */
    .stButton > button {
        background-color: #FF6B00;
        color: #FFFFFF;
        font-weight: 700;
        font-family: 'Source Sans Pro', Arial, sans-serif;
        border: none;
        border-radius: 4px;
        padding: 6px 18px;
        letter-spacing: 0.5px;
    }
    .stButton > button:hover { background-color: #CC5500; color: #FFFFFF; }

    /* Hide streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─── Constants ───────────────────────────────────────────────────────────────
SHEET_ID = "1pBTpsIqJzK6CyhLIQz8H8wKSI3xLQzxa74L-JISFPvc"
CALCULATED_SHEET = "Calculated"

CHART_COLORS = [
    "#4B9FE1", "#A259FF", "#00C2C7", "#57C785", "#FF6B00",
    "#FFB347", "#FF4F6B", "#7EC8E3", "#B0C4DE", "#FFA07A"
]

# Single-series bar charts use a blue-to-teal gradient sequence
BAR_GRADIENT = [
    "#1E90FF", "#2196F3", "#2FA8E8", "#3AB8D4", "#40C4B8",
    "#43CCA0", "#45D18A", "#57C785", "#6DCF6D", "#85CC55"
]

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#252A3A",
    font=dict(color="#FFFFFF", family="Source Sans Pro, Arial"),
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FFFFFF", size=11, family="Source Sans Pro, Arial")
    )
)

# ─── Flexible date parser ────────────────────────────────────────────────────
def _parse_dates(series):
    formats = [
        "%m/%d/%Y %H:%M:%S",   # 5/19/2026 15:53:00
        "%m/%d/%y %H:%M:%S",   # 05/19/26 11:06:11
        "%m/%d/%Y %H:%M",      # 5/19/2026 15:53
        "%m/%d/%y %H:%M",      # 05/19/26 11:06
        "%m/%d/%Y",            # 5/19/2026
        "%m/%d/%y",            # 05/19/26
        "%Y-%m-%d %H:%M:%S",   # 2026-05-19 15:53:00
        "%Y-%m-%dT%H:%M:%S",   # ISO format
        "%d/%m/%Y %H:%M:%S",   # European style
    ]
    result = pd.Series([pd.NaT] * len(series), index=series.index)
    remaining = series.copy()
    for fmt in formats:
        mask = result.isna() & remaining.notna()
        if not mask.any():
            break
        parsed = pd.to_datetime(remaining[mask], format=fmt, errors="coerce")
        result[mask] = parsed
    # Final fallback for anything still unparsed
    still_null = result.isna() & remaining.notna()
    if still_null.any():
        result[still_null] = pd.to_datetime(remaining[still_null], errors="coerce", format="mixed")
    return result

# ─── Data Loading ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800)  # 30-minute cache
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={CALCULATED_SHEET}"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()

    # Rename to standard names
    col_map = {
        df.columns[0]: "Email",
        df.columns[1]: "Account",
        df.columns[2]: "Project",
        df.columns[3]: "Tool",
        df.columns[4]: "Activity",
        df.columns[5]: "Hours Saved",
        df.columns[6]: "Satisfaction",
        df.columns[7]: "Confidence",
        df.columns[8]: "Frequency",
        df.columns[9]: "Blocker",
        df.columns[10]: "Week",
        df.columns[11]: "Submission Date",
    }
    df = df.rename(columns=col_map)

    # Type conversions
    df["Hours Saved"] = pd.to_numeric(df["Hours Saved"], errors="coerce").fillna(0)
    df["Satisfaction"] = pd.to_numeric(df["Satisfaction"], errors="coerce")
    df["Confidence"] = pd.to_numeric(df["Confidence"], errors="coerce")
    df["Submission Date"] = _parse_dates(df["Submission Date"])

    # Extract employee display name from email
    df["Employee"] = df["Email"].str.split("@").str[0].str.replace(".", " ").str.title()

    return df

# ─── Helper: Plotly bar chart ─────────────────────────────────────────────────
def horizontal_bar(data, x_col, y_col, title, color=None):
    fig = px.bar(
        data, x=x_col, y=y_col,
        orientation="h",
        color=color if color else x_col,
        color_discrete_sequence=CHART_COLORS,
        title=title
    )
    fig.update_layout(**PLOTLY_LAYOUT, title=dict(font=dict(size=12, color="#8899AA"), x=0))
    fig.update_yaxes(categoryorder="total ascending", color="#FFFFFF", tickfont=dict(size=11))
    fig.update_xaxes(color="#8899AA", gridcolor="#2A3B4C")
    fig.update_traces(showlegend=False)
    return fig

# ─── KPI Card HTML ────────────────────────────────────────────────────────────
def kpi_card(label, value, sub="", value_white=False, sub_teal=False):
    value_class = "kpi-value-white" if value_white else "kpi-value"
    sub_class = "kpi-sub-teal" if sub_teal else "kpi-sub"
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="{value_class}">{value}</div>
        <div class="{sub_class}">{sub}</div>
    </div>
    """

# ─── Main App ─────────────────────────────────────────────────────────────────
def main():
    # Load data
    try:
        df = load_data()
    except Exception as e:
        st.error(f"Could not load data: {e}. Make sure your Google Sheet is publicly shared.")
        st.stop()

    # ── Header ────────────────────────────────────────────────────────────────
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.markdown(f"""
        <div class="dash-header">
            <div class="dash-title">GenAI Usage Dashboard — Expedia Account</div>
            <div class="dash-subtitle">
                Auto-refreshes every 15 min &nbsp;·&nbsp;
                Source: Microsoft Forms → OneDrive Excel → Google Sheets &nbsp;·&nbsp;
                {len(df)} responses
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_h2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Refresh Data"):
            st.cache_data.clear()
            st.rerun()

    # ── Filters ───────────────────────────────────────────────────────────────
    # Build week range labels: "Apr 28 – May 04" style sorted chronologically
    def build_week_options(data):
        data = data.copy()
        data["Submission Date"] = _parse_dates(data["Submission Date"])
        data["_week_start"] = data["Submission Date"].dt.to_period("W").dt.to_timestamp()
        data["_week_end"] = data["Submission Date"].dt.to_period("W").dt.to_timestamp() + pd.Timedelta(days=6)
        data["_week_label"] = (
            data["_week_start"].dt.strftime("%b %d") + " – " + data["_week_end"].dt.strftime("%b %d, %Y")
        )
        week_map = (
            data[["_week_start", "_week_label"]]
            .drop_duplicates()
            .sort_values("_week_start")
        )
        return week_map["_week_label"].tolist(), dict(zip(week_map["_week_label"], week_map["_week_start"]))

    week_labels, week_start_map = build_week_options(df)
    week_options = ["All weeks"] + week_labels

    st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
    fc1, fc2, fc3, fc4, fc5 = st.columns(5)

    def make_filter(col, label, field):
        options = ["All"] + sorted(df[field].dropna().unique().tolist())
        return col.selectbox(label, options, key=field)

    with fc1: f_week = fc1.selectbox("Week", week_options, key="Week")
    with fc2: f_project = make_filter(fc2, "Project", "Project")
    with fc3: f_account = make_filter(fc3, "Account", "Account")
    with fc4: f_employee = make_filter(fc4, "Employee", "Employee")
    with fc5: f_freq = make_filter(fc5, "Frequency", "Frequency")

    st.markdown('</div>', unsafe_allow_html=True)

    # Apply filters
    fdf = df.copy()
    fdf["Submission Date"] = _parse_dates(fdf["Submission Date"])
    if f_week != "All weeks":
        week_start = week_start_map[f_week]
        week_end = week_start + pd.Timedelta(days=6)
        fdf = fdf[(fdf["Submission Date"] >= week_start) & (fdf["Submission Date"] <= week_end)]
    if f_project != "All": fdf = fdf[fdf["Project"] == f_project]
    if f_account != "All": fdf = fdf[fdf["Account"] == f_account]
    if f_employee != "All": fdf = fdf[fdf["Employee"] == f_employee]
    if f_freq != "All": fdf = fdf[fdf["Frequency"] == f_freq]

    total_responses = len(fdf)
    st.markdown(f"<p style='color:#8899AA;font-size:12px;text-align:right;margin-top:-10px;'>Showing {total_responses} of {len(df)} responses</p>", unsafe_allow_html=True)

    if fdf.empty:
        st.warning("No data matches the selected filters.")
        st.stop()

    # ── KPI Scorecards ────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Key Performance Indicators</div>', unsafe_allow_html=True)

    total_hours = fdf["Hours Saved"].sum()
    avg_satisfaction = fdf["Satisfaction"].mean()
    active_contributors = fdf["Email"].nunique()
    avg_hours_per_entry = fdf["Hours Saved"].mean()
    avg_confidence = fdf["Confidence"].mean()
    # Split semicolon-separated tools, explode, count individually
    tools_exploded = fdf["Tool"].dropna().str.split(";").explode().str.strip()
    top_tool = tools_exploded.value_counts().idxmax() if not tools_exploded.empty else "N/A"
    top_tool_pct = tools_exploded.value_counts(normalize=True).max() * 100 if not tools_exploded.empty else 0

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.markdown(kpi_card("Total Hours Saved",      f"{total_hours:.0f}h",         f"{total_responses} tracked tasks"), unsafe_allow_html=True)
    k2.markdown(kpi_card("Avg Satisfaction Score", f"{avg_satisfaction:.1f} / 10", f"out of 10  ·  {(fdf['Satisfaction'] >= 8).sum()} rated ≥8"), unsafe_allow_html=True)
    k3.markdown(kpi_card("Active Contributors",    f"{active_contributors}",       f"across {fdf['Project'].nunique()} projects"), unsafe_allow_html=True)
    k4.markdown(kpi_card("Avg Hours Saved / Entry",f"{avg_hours_per_entry:.1f}h",  f"max: {fdf['Hours Saved'].max():.0f}h saved in one task"), unsafe_allow_html=True)
    k5.markdown(kpi_card("Avg Confidence Level",   f"{avg_confidence:.1f} / 5",    "out of 5"), unsafe_allow_html=True)
    k6.markdown(kpi_card("Top AI Tool",            top_tool,                        f"{top_tool_pct:.0f}% of submissions", value_white=True, sub_teal=True), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 2: Hours by Project | AI Usage by Project | AI Tool Adoption ─────
    col_left, col_mid, col_right = st.columns([3, 3, 2])

    with col_left:
        st.markdown('<div class="section-header">Hours Saved by Project</div>', unsafe_allow_html=True)
        proj_data = fdf.groupby("Project")["Hours Saved"].sum().reset_index().sort_values("Hours Saved", ascending=False)
        fig_proj = px.bar(
            proj_data, x="Hours Saved", y="Project",
            orientation="h", color="Project",
            color_discrete_sequence=CHART_COLORS
        )
        fig_proj.update_layout(**PLOTLY_LAYOUT, height=420, showlegend=False)
        fig_proj.update_xaxes(color="#8899AA", gridcolor="#2A3B4C", title="Hours Saved")
        fig_proj.update_yaxes(color="#FFFFFF", tickfont=dict(size=11), categoryorder="total ascending", automargin=True)
        fig_proj.update_traces(hovertemplate="<b>%{y}</b><br>Hours Saved: %{x}<extra></extra>")
        st.plotly_chart(fig_proj, width="stretch")

    with col_mid:
        st.markdown('<div class="section-header">AI Usage by Project</div>', unsafe_allow_html=True)

        def freq_to_score(freq):
            if pd.isna(freq): return 0
            f = str(freq).lower().strip()
            if "multiple" in f or "3-4 times" in f: return 125
            elif "every day" in f or "daily" in f or "at least once" in f: return 100
            elif "3-4 days" in f or "3–4 days" in f: return 75
            elif "1-2 days" in f or "1–2 days" in f: return 40
            else: return 0

        usage_proj = fdf.copy()
        usage_proj["Usage Score"] = usage_proj["Frequency"].apply(freq_to_score)
        usage_proj_data = usage_proj.groupby("Project")["Usage Score"].mean().reset_index()
        usage_proj_data.columns = ["Project", "Avg AI Usage %"]
        usage_proj_data["Avg AI Usage %"] = usage_proj_data["Avg AI Usage %"].round(1)
        usage_proj_data["Usage Label"] = usage_proj_data["Avg AI Usage %"].apply(
            lambda x: ">100%" if x >= 125 else f"{x:.0f}%"
        )
        # Highest to lowest (descending) — categoryorder="total ascending" renders top-to-bottom
        usage_proj_data = usage_proj_data.sort_values("Avg AI Usage %", ascending=False)

        fig_usage = px.bar(
            usage_proj_data, x="Avg AI Usage %", y="Project",
            orientation="h", color="Project",
            color_discrete_sequence=CHART_COLORS,
            text="Usage Label"
        )
        fig_usage.update_layout(**PLOTLY_LAYOUT, height=420, showlegend=False)
        fig_usage.update_xaxes(color="#8899AA", gridcolor="#2A3B4C", title="Avg AI Usage %", range=[0, 145])
        fig_usage.update_yaxes(color="#FFFFFF", tickfont=dict(size=11), categoryorder="total ascending", automargin=True)
        fig_usage.update_traces(
            textposition="outside",
            textfont=dict(color="white", size=11),
            hovertemplate="<b>%{y}</b><br>Avg AI Usage: %{x:.0f}%<extra></extra>"
        )
        st.plotly_chart(fig_usage, width="stretch")

    with col_right:
        st.markdown('<div class="section-header">AI Tool Adoption</div>', unsafe_allow_html=True)
        tools_series = fdf["Tool"].dropna().str.split(";").explode().str.strip()
        tool_data = tools_series.value_counts().reset_index()
        tool_data.columns = ["Tool", "Count"]
        tool_data = tool_data.head(8)
        total_tool_count = tool_data["Count"].sum()
        tool_data["Pct"] = (tool_data["Count"] / total_tool_count * 100).round(1)
        tool_data["hover"] = tool_data.apply(
            lambda r: f"<b>{r['Tool']}</b><br>Users: {r['Count']}<br>Usage: {r['Pct']}%", axis=1
        )
        if not tool_data.empty:
            fig_donut = px.pie(
                tool_data, names="Tool", values="Count",
                hole=0.5,
                color_discrete_sequence=CHART_COLORS,
                custom_data=["hover"]
            )
            fig_donut.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#1A2B3C",
                font=dict(color="#FFFFFF", family="Arial"),
                margin=dict(l=10, r=10, t=60, b=10),
                height=420,
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02,
                    xanchor="center", x=0.5,
                    font=dict(color="#FFFFFF", size=10),
                    bgcolor="rgba(0,0,0,0)"
                )
            )
            fig_donut.update_traces(
                textfont=dict(color="white", size=11),
                textposition="inside",
                textinfo="percent",
                hovertemplate="%{customdata[0]}<extra></extra>"
            )
            st.plotly_chart(fig_donut, width="stretch")
        else:
            st.info("No tool data available.")

    # ── Row 3: Activities + Frequency + Trend + Blockers ─────────────────────
    col1, col2, col3 = st.columns([2, 2, 2])

    AXIS_STYLE = dict(color="#8A93B0", gridcolor="#333850", tickfont=dict(size=12, family="Source Sans Pro, Arial"))
    TICK_STYLE = dict(color="#FFFFFF", tickfont=dict(size=12, family="Source Sans Pro, Arial"), automargin=True)
    TITLE_FONT = dict(size=12, color="#8A93B0", family="Source Sans Pro, Arial")
    BAR_COLOR  = "#2FA8E8"   # professional steel blue for single-series bars

    with col1:
        st.markdown('<div class="section-header">Top Activities / Use Cases</div>', unsafe_allow_html=True)
        act_series = fdf["Activity"].dropna().str.split(";").explode().str.strip()
        act_data = act_series.value_counts().head(12).reset_index()
        act_data.columns = ["Activity", "Count"]
        act_data = act_data.sort_values("Count", ascending=True)
        act_data["color"] = [BAR_GRADIENT[i % len(BAR_GRADIENT)] for i in range(len(act_data))]
        fig_act = px.bar(act_data, x="Count", y="Activity", orientation="h",
                         color="color", color_discrete_map="identity")
        fig_act.update_layout(**{**PLOTLY_LAYOUT, "margin": dict(l=10, r=30, t=10, b=40)},
                              height=520, showlegend=False)
        fig_act.update_xaxes(**AXIS_STYLE, title=dict(text="Count", font=TITLE_FONT))
        fig_act.update_yaxes(**TICK_STYLE, title=dict(text="Activity", font=TITLE_FONT))
        fig_act.update_traces(
            marker_line_width=0,
            hovertemplate="<b>%{y}</b><br>Count: %{x}<extra></extra>"
        )
        st.plotly_chart(fig_act, width="stretch")

    with col2:
        st.markdown('<div class="section-header">Usage Frequency Breakdown</div>', unsafe_allow_html=True)
        freq_order = ["Multiple times per day", "Every day (at least once)", "3-4 days per week", "1-2 days per week"]
        freq_data = fdf["Frequency"].value_counts().reset_index()
        freq_data.columns = ["Frequency", "Count"]
        freq_data["sort_key"] = freq_data["Frequency"].apply(
            lambda x: freq_order.index(x) if x in freq_order else 99
        )
        freq_data = freq_data.sort_values("sort_key", ascending=False).drop(columns="sort_key")
        freq_data["color"] = [BAR_GRADIENT[i * 3 % len(BAR_GRADIENT)] for i in range(len(freq_data))]
        fig_freq = px.bar(freq_data, x="Count", y="Frequency", orientation="h",
                          color="color", color_discrete_map="identity")
        fig_freq.update_layout(**{**PLOTLY_LAYOUT, "margin": dict(l=10, r=30, t=10, b=40)},
                               height=210, showlegend=False)
        fig_freq.update_xaxes(**AXIS_STYLE, title=dict(text="Count", font=TITLE_FONT))
        fig_freq.update_yaxes(**TICK_STYLE, title=dict(text="", font=TITLE_FONT))
        fig_freq.update_traces(marker_line_width=0,
                               hovertemplate="<b>%{y}</b><br>Count: %{x}<extra></extra>")
        st.plotly_chart(fig_freq, width="stretch")

        st.markdown('<div class="section-header">Avg Satisfaction by Project</div>', unsafe_allow_html=True)
        sat_proj = fdf.groupby("Project")["Satisfaction"].mean().reset_index().sort_values("Satisfaction", ascending=True)
        sat_proj["Satisfaction"] = sat_proj["Satisfaction"].round(1)
        sat_proj["color"] = [BAR_GRADIENT[i % len(BAR_GRADIENT)] for i in range(len(sat_proj))]
        fig_sat = px.bar(sat_proj, x="Satisfaction", y="Project", orientation="h",
                         color="color", color_discrete_map="identity", text="Satisfaction")
        fig_sat.update_layout(**{**PLOTLY_LAYOUT, "margin": dict(l=10, r=50, t=10, b=40)},
                              height=310, showlegend=False)
        fig_sat.update_traces(
            textposition="outside",
            textfont=dict(color="#FFFFFF", size=11, family="Arial"),
            marker_line_width=0,
            hovertemplate="<b>%{y}</b><br>Avg Satisfaction: %{x}<extra></extra>"
        )
        fig_sat.update_xaxes(**AXIS_STYLE, range=[0, 12],
                             title=dict(text="Avg Score", font=TITLE_FONT))
        fig_sat.update_yaxes(**TICK_STYLE, title=dict(text="", font=TITLE_FONT))
        st.plotly_chart(fig_sat, width="stretch")

    with col3:
        st.markdown('<div class="section-header">Weekly Hours Saved Trend</div>', unsafe_allow_html=True)
        trend_df = fdf.copy()
        trend_df["Submission Date"] = _parse_dates(trend_df["Submission Date"])
        trend_df["WeekStart"] = trend_df["Submission Date"].dt.to_period("W").dt.to_timestamp()
        trend_df["WeekLabel"] = trend_df["WeekStart"].dt.strftime("W%W: %b %d")
        week_data = trend_df.groupby(["WeekStart", "WeekLabel"])["Hours Saved"].sum().reset_index()
        week_data = week_data.sort_values("WeekStart")
        week_data["color"] = [BAR_GRADIENT[i % len(BAR_GRADIENT)] for i in range(len(week_data))]
        fig_trend = px.bar(week_data, x="WeekLabel", y="Hours Saved",
                           color="color", color_discrete_map="identity")
        fig_trend.update_layout(**{**PLOTLY_LAYOUT, "margin": dict(l=10, r=10, t=10, b=50)},
                                height=250, showlegend=False)
        fig_trend.update_xaxes(**AXIS_STYLE, title=dict(text="Week", font=TITLE_FONT),
                               tickangle=-30)
        fig_trend.update_yaxes(**AXIS_STYLE, title=dict(text="Hours Saved", font=TITLE_FONT))
        fig_trend.update_traces(marker_line_width=0,
                                hovertemplate="<b>%{x}</b><br>Hours Saved: %{y}<extra></extra>")
        st.plotly_chart(fig_trend, width="stretch")

        st.markdown('<div class="section-header">Top Reported Blockers</div>', unsafe_allow_html=True)

        BLOCKER_CATEGORIES = {
            "Hallucinations / incorrect output": [
                "hallucin", "incorrect", "wrong", "inaccurate", "not correct",
                "not giving what", "not what we expect", "false", "fabricat"
            ],
            "API & context window limits": [
                "api limit", "context window", "token limit", "rate limit",
                "context limit", "window limit", "api limits"
            ],
            "Rapidly changing tools (learning curve)": [
                "changing tool", "learning curve", "change every", "new tool",
                "keep changing", "rapidly changing", "switching tool"
            ],
            "Trust overhead — manual review needed": [
                "manual review", "trust", "can't blindly", "cannot blindly",
                "review needed", "verify", "validate", "oversight"
            ],
            "Few use cases in legacy projects": [
                "legacy", "old code", "old project", "limited use case",
                "few use case", "no use case"
            ],
            "Tool suggestion quality inconsistency": [
                "inconsistent", "quality", "suggestion quality", "not consistent",
                "vary", "unpredictable"
            ],
            "Slow response / performance issues": [
                "slow", "too much time", "taking time", "latency", "timeout",
                "performance", "respond slow", "response time"
            ],
            "No blockers": [
                "no blocker", "none", "nothing", "no issue", "n/a", "na",
                "not any", "i don't see any", "no challenges"
            ],
        }

        def categorize_blocker(text):
            if pd.isna(text): return None
            text_lower = str(text).lower().strip()
            for category, keywords in BLOCKER_CATEGORIES.items():
                if any(kw in text_lower for kw in keywords):
                    return category
            return "Other"

        blocker_series = fdf["Blocker"].dropna().str.strip()
        categorized = blocker_series.apply(categorize_blocker)
        categorized = categorized[~categorized.isin(["No blockers", None])]
        blocker_data = categorized.value_counts().head(6).reset_index()
        blocker_data.columns = ["Blocker", "Count"]

        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        for _, row in blocker_data.iterrows():
            b1, b2 = st.columns([5, 1])
            b1.markdown(
                f"<p style='color:#CCDDEE;font-size:12px;font-family:Arial;margin:6px 0;line-height:1.5;'>• {row['Blocker']}</p>",
                unsafe_allow_html=True
            )
            b2.markdown(
                f"<p style='color:#00C2C7;font-size:13px;font-weight:700;font-family:Arial;margin:6px 0;text-align:right;'>{row['Count']}</p>",
                unsafe_allow_html=True
            )

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Employee Leaderboard ──────────────────────────────────────────────────
    st.markdown('<div class="section-header">Employee Leaderboard — Hours Saved</div>', unsafe_allow_html=True)

    # AI Usage % mapping from frequency
    def freq_to_usage(freq):
        if pd.isna(freq):
            return "0%"
        f = str(freq).lower().strip()
        if "multiple" in f or "3-4 times" in f or "3-4 time" in f:
            return ">100%"
        elif "every day" in f or "daily" in f or "at least once" in f:
            return "100%"
        elif "3-4 days" in f or "3–4 days" in f:
            return "75%"
        elif "1-2 days" in f or "1–2 days" in f:
            return "<50%"
        else:
            return "0%"

    # Get most frequent tool and frequency per employee
    tool_mode = fdf.groupby("Employee")["Tool"].agg(
        lambda x: x.dropna().str.split(";").explode().str.strip().value_counts().idxmax()
        if not x.dropna().empty else "N/A"
    )
    freq_mode = fdf.groupby("Employee")["Frequency"].agg(
        lambda x: x.value_counts().idxmax() if not x.dropna().empty else None
    )

    leaderboard = fdf.groupby("Employee").agg(
        Project=("Project", lambda x: x.value_counts().idxmax()),
        Hours_Saved=("Hours Saved", "sum"),
        Entries=("Email", "count"),
        Avg_Satisfaction=("Satisfaction", "mean"),
        Avg_Confidence=("Confidence", "mean")
    ).reset_index()

    leaderboard["Primary Tool"] = leaderboard["Employee"].map(tool_mode)
    leaderboard["Frequency"] = leaderboard["Employee"].map(freq_mode)
    leaderboard["AI Usage %"] = leaderboard["Frequency"].apply(freq_to_usage)
    leaderboard = leaderboard.sort_values("Hours_Saved", ascending=False).reset_index(drop=True)
    leaderboard.index += 1

    leaderboard["Hours_Saved"] = leaderboard["Hours_Saved"].apply(lambda x: f"{x:.0f}h")
    leaderboard["Avg_Satisfaction"] = leaderboard["Avg_Satisfaction"].apply(lambda x: f"{x:.1f}")
    leaderboard["Avg_Confidence"] = leaderboard["Avg_Confidence"].apply(lambda x: f"{x:.1f} / 5")

    leaderboard = leaderboard[["Employee", "Project", "Hours_Saved", "Entries",
                                "Avg_Satisfaction", "Avg_Confidence", "Primary Tool", "AI Usage %"]]
    leaderboard.columns = ["Employee", "Project", "Hours Saved", "Entries",
                           "Avg Satisfaction", "Avg Confidence", "Primary Tool", "AI Usage %"]
    leaderboard.index.name = "#"

    st.dataframe(
        leaderboard,
        width="stretch",
        height=400
    )

    # ── Footer ────────────────────────────────────────────────────────────────
    now = datetime.now().strftime("%b %d, %Y · %I:%M %p")
    st.markdown(f"<p style='color:#8899AA;font-size:11px;text-align:right;margin-top:8px;'>Last refreshed: {now}</p>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
