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

# ─── Dark Theme CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0D1B2A; color: #FFFFFF; }
    [data-testid="stAppViewContainer"] { background-color: #0D1B2A; }
    [data-testid="stHeader"] { background-color: #0D1B2A; }
    section[data-testid="stSidebar"] { background-color: #0D1B2A; }

    /* KPI Cards */
    .kpi-card {
        background-color: #1A2B3C;
        border: 1px solid #2A3B4C;
        border-radius: 8px;
        padding: 16px 20px;
        text-align: left;
    }
    .kpi-label {
        font-size: 10px;
        color: #8899AA;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .kpi-value {
        font-size: 32px;
        font-weight: 700;
        color: #00C2C7;
        line-height: 1.1;
    }
    .kpi-sub {
        font-size: 11px;
        color: #8899AA;
        margin-top: 4px;
    }

    /* Section headers */
    .section-header {
        font-size: 11px;
        font-weight: 600;
        color: #8899AA;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 8px;
        padding-bottom: 4px;
        border-bottom: 1px solid #2A3B4C;
    }

    /* Dashboard header */
    .dash-header {
        background-color: #1A2B3C;
        border-radius: 8px;
        padding: 14px 20px;
        margin-bottom: 16px;
        border: 1px solid #2A3B4C;
    }
    .dash-title {
        font-size: 20px;
        font-weight: 700;
        color: #FFFFFF;
    }
    .dash-subtitle {
        font-size: 11px;
        color: #8899AA;
        margin-top: 2px;
    }

    /* Filter bar */
    .filter-bar {
        background-color: #1A2B3C;
        border-radius: 8px;
        padding: 10px 16px;
        margin-bottom: 16px;
        border: 1px solid #2A3B4C;
    }

    /* Selectbox styling */
    .stSelectbox > div > div {
        background-color: #1A2B3C !important;
        color: #FFFFFF !important;
        border: 1px solid #2A3B4C !important;
    }
    .stSelectbox label { color: #8899AA !important; font-size: 11px !important; }

    /* Table styling */
    .stDataFrame { background-color: #1A2B3C; }
    thead tr th {
        background-color: #0D1B2A !important;
        color: #8899AA !important;
        font-size: 11px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    tbody tr td { color: #FFFFFF !important; font-size: 13px !important; }
    tbody tr:hover td { background-color: #2A3B4C !important; }

    /* Divider */
    hr { border-color: #2A3B4C; }

    /* Metric delta */
    [data-testid="stMetricDelta"] { color: #00C2C7; }

    /* Plotly chart background fix */
    .js-plotly-plot { background-color: transparent !important; }

    /* Refresh button */
    .stButton > button {
        background-color: #00C2C7;
        color: #0D1B2A;
        font-weight: 700;
        border: none;
        border-radius: 6px;
        padding: 6px 16px;
    }
    .stButton > button:hover { background-color: #00A8AD; }

    /* Hide streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─── Constants ───────────────────────────────────────────────────────────────
SHEET_ID = "1pBTpsIqJzK6CyhLIQz8H8wKSI3xLQzxa74L-JISFPvc"
CALCULATED_SHEET = "Calculated"

CHART_COLORS = [
    "#00C2C7", "#4B9FE1", "#7B61FF", "#FF6B6B", "#FFB347",
    "#98D85B", "#FF8C94", "#A8E6CF", "#FFD3B6", "#DCEDC1"
]

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#1A2B3C",
    font=dict(color="#FFFFFF", family="Arial"),
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FFFFFF", size=11)
    )
)

# ─── Data Loading ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=900)  # 15-minute cache
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
    df["Submission Date"] = pd.to_datetime(df["Submission Date"], errors="coerce")

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
def kpi_card(label, value, sub=""):
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
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
    st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
    fc1, fc2, fc3, fc4, fc5, fc6 = st.columns(6)

    def make_filter(col, label, field):
        options = ["All"] + sorted(df[field].dropna().unique().tolist())
        return col.selectbox(label, options, key=field)

    with fc1: f_week = make_filter(fc1, "Week", "Week")
    with fc2: f_project = make_filter(fc2, "Project", "Project")
    with fc3: f_tool = make_filter(fc3, "Tool", "Tool")
    with fc4: f_account = make_filter(fc4, "Account", "Account")
    with fc5: f_employee = make_filter(fc5, "Employee", "Employee")
    with fc6: f_freq = make_filter(fc6, "Frequency", "Frequency")

    st.markdown('</div>', unsafe_allow_html=True)

    # Apply filters
    fdf = df.copy()
    if f_week != "All": fdf = fdf[fdf["Week"] == f_week]
    if f_project != "All": fdf = fdf[fdf["Project"] == f_project]
    if f_tool != "All": fdf = fdf[fdf["Tool"] == f_tool]
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
    top_tool = fdf["Tool"].value_counts().idxmax() if not fdf["Tool"].isna().all() else "N/A"
    top_tool_pct = fdf["Tool"].value_counts(normalize=True).max() * 100 if not fdf["Tool"].isna().all() else 0

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.markdown(kpi_card("Total Hours Saved", f"{total_hours:.0f}h", f"{total_responses} tracked tasks"), unsafe_allow_html=True)
    k2.markdown(kpi_card("Avg Satisfaction Score", f"{avg_satisfaction:.1f} / 10", f"{(fdf['Satisfaction'] >= 8).sum()} rated ≥8"), unsafe_allow_html=True)
    k3.markdown(kpi_card("Active Contributors", f"{active_contributors}", f"across {fdf['Project'].nunique()} projects"), unsafe_allow_html=True)
    k4.markdown(kpi_card("Avg Hours Saved / Entry", f"{avg_hours_per_entry:.1f}h", f"max: {fdf['Hours Saved'].max():.0f}h saved in one task"), unsafe_allow_html=True)
    k5.markdown(kpi_card("Avg Confidence Level", f"{avg_confidence:.1f} / 5", "out of 5"), unsafe_allow_html=True)
    k6.markdown(kpi_card("Top AI Tool", top_tool, f"{top_tool_pct:.0f}% of submissions"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 2: Hours by Project + Tool Adoption ───────────────────────────────
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown('<div class="section-header">Hours Saved by Project</div>', unsafe_allow_html=True)
        proj_data = fdf.groupby("Project")["Hours Saved"].sum().reset_index().sort_values("Hours Saved", ascending=True)
        fig_proj = px.bar(
            proj_data, x="Hours Saved", y="Project",
            orientation="h",
            color="Project",
            color_discrete_sequence=CHART_COLORS
        )
        fig_proj.update_layout(**PLOTLY_LAYOUT, height=380, showlegend=False)
        fig_proj.update_xaxes(color="#8899AA", gridcolor="#2A3B4C")
        fig_proj.update_yaxes(color="#FFFFFF", tickfont=dict(size=11))
        st.plotly_chart(fig_proj, use_container_width=True)

    with col_right:
        st.markdown('<div class="section-header">AI Tool Adoption</div>', unsafe_allow_html=True)
        tool_data = fdf["Tool"].value_counts().reset_index()
        tool_data.columns = ["Tool", "Count"]
        fig_donut = px.pie(
            tool_data, names="Tool", values="Count",
            hole=0.5,
            color_discrete_sequence=CHART_COLORS
        )
        fig_donut.update_layout(**PLOTLY_LAYOUT, height=380,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                       font=dict(color="#FFFFFF", size=10)))
        fig_donut.update_traces(textfont_color="white", textfont_size=11)
        st.plotly_chart(fig_donut, use_container_width=True)

    # ── Row 3: Activities + Frequency + Trend + Blockers ─────────────────────
    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        st.markdown('<div class="section-header">Top Activities / Use Cases</div>', unsafe_allow_html=True)
        act_data = fdf["Activity"].value_counts().head(12).reset_index()
        act_data.columns = ["Activity", "Count"]
        act_data = act_data.sort_values("Count", ascending=True)
        fig_act = px.bar(act_data, x="Count", y="Activity", orientation="h",
                        color_discrete_sequence=[CHART_COLORS[0]])
        fig_act.update_layout(**PLOTLY_LAYOUT, height=420, showlegend=False)
        fig_act.update_xaxes(color="#8899AA", gridcolor="#2A3B4C")
        fig_act.update_yaxes(color="#FFFFFF", tickfont=dict(size=10))
        st.plotly_chart(fig_act, use_container_width=True)

    with col2:
        st.markdown('<div class="section-header">Usage Frequency Breakdown</div>', unsafe_allow_html=True)
        freq_data = fdf["Frequency"].value_counts().reset_index()
        freq_data.columns = ["Frequency", "Count"]
        freq_data = freq_data.sort_values("Count", ascending=True)
        fig_freq = px.bar(freq_data, x="Count", y="Frequency", orientation="h",
                         color_discrete_sequence=[CHART_COLORS[1]])
        fig_freq.update_layout(**PLOTLY_LAYOUT, height=180, showlegend=False)
        fig_freq.update_xaxes(color="#8899AA", gridcolor="#2A3B4C")
        fig_freq.update_yaxes(color="#FFFFFF", tickfont=dict(size=11))
        st.plotly_chart(fig_freq, use_container_width=True)

        st.markdown('<div class="section-header">Avg Satisfaction by Project</div>', unsafe_allow_html=True)
        sat_proj = fdf.groupby("Project")["Satisfaction"].mean().reset_index().sort_values("Satisfaction", ascending=True)
        sat_proj["Satisfaction"] = sat_proj["Satisfaction"].round(1)
        fig_sat = px.bar(sat_proj, x="Satisfaction", y="Project", orientation="h",
                        color_discrete_sequence=[CHART_COLORS[2]],
                        text="Satisfaction")
        fig_sat.update_layout(**PLOTLY_LAYOUT, height=220, showlegend=False)
        fig_sat.update_traces(textposition="outside", textfont=dict(color="white", size=10))
        fig_sat.update_xaxes(color="#8899AA", gridcolor="#2A3B4C", range=[0, 11])
        fig_sat.update_yaxes(color="#FFFFFF", tickfont=dict(size=10))
        st.plotly_chart(fig_sat, use_container_width=True)

    with col3:
        st.markdown('<div class="section-header">Weekly Hours Saved Trend</div>', unsafe_allow_html=True)
        week_data = fdf.groupby("Week")["Hours Saved"].sum().reset_index().sort_values("Week")
        fig_trend = px.bar(week_data, x="Week", y="Hours Saved",
                          color_discrete_sequence=[CHART_COLORS[0]])
        fig_trend.update_layout(**PLOTLY_LAYOUT, height=200, showlegend=False)
        fig_trend.update_xaxes(color="#8899AA", tickfont=dict(size=10))
        fig_trend.update_yaxes(color="#8899AA", gridcolor="#2A3B4C")
        st.plotly_chart(fig_trend, use_container_width=True)

        st.markdown('<div class="section-header">Top Reported Blockers</div>', unsafe_allow_html=True)
        blocker_data = fdf["Blocker"].value_counts().head(6).reset_index()
        blocker_data.columns = ["Blocker", "Count"]
        for _, row in blocker_data.iterrows():
            b1, b2 = st.columns([4, 1])
            b1.markdown(f"<p style='color:#FFFFFF;font-size:12px;margin:2px 0;'>• {row['Blocker']}</p>", unsafe_allow_html=True)
            b2.markdown(f"<p style='color:#00C2C7;font-size:12px;font-weight:700;margin:2px 0;text-align:right;'>{row['Count']}</p>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Employee Leaderboard ──────────────────────────────────────────────────
    lb1, lb2 = st.columns([4, 1])
    lb1.markdown('<div class="section-header">Employee Leaderboard — Hours Saved</div>', unsafe_allow_html=True)

    leaderboard = fdf.groupby(["Employee", "Project", "Tool"]).agg(
        Hours_Saved=("Hours Saved", "sum"),
        Entries=("Email", "count"),
        Avg_Satisfaction=("Satisfaction", "mean"),
        Avg_Confidence=("Confidence", "mean")
    ).reset_index().sort_values("Hours_Saved", ascending=False).reset_index(drop=True)

    leaderboard.index += 1
    leaderboard["Hours_Saved"] = leaderboard["Hours_Saved"].apply(lambda x: f"{x:.0f}h")
    leaderboard["Avg_Satisfaction"] = leaderboard["Avg_Satisfaction"].apply(lambda x: f"{x:.1f}")
    leaderboard["Avg_Confidence"] = leaderboard["Avg_Confidence"].apply(lambda x: f"{x:.1f} / 5")
    leaderboard.columns = ["#", "Employee", "Project", "Primary Tool", "Hours Saved", "Entries", "Avg Satisfaction", "Avg Confidence"]
    leaderboard = leaderboard.set_index("#")

    with lb2:
        csv = fdf.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Export CSV",
            data=csv,
            file_name=f"genai_dashboard_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    st.dataframe(
        leaderboard,
        use_container_width=True,
        height=400
    )

    # ── Footer ────────────────────────────────────────────────────────────────
    now = datetime.now().strftime("%b %d, %Y · %I:%M %p")
    st.markdown(f"<p style='color:#8899AA;font-size:11px;text-align:right;margin-top:8px;'>Last refreshed: {now}</p>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
