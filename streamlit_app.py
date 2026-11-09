"""
PL Capital — AI Portfolio Analytics Dashboard
Enterprise financial analytics web application powered by Streamlit, Plotly,
SQLite, and Google Gemini with native function calling.

Pages:
1. Overview: Executive metrics, sector distribution, risk profiles & portfolio AUM
2. AI Portfolio Assistant: Multi-turn conversational chatbot with tool inspection
3. Sector Exposure Analytics: Precision equity-only exposure calculator with Plotly charts
4. Portfolio Explorer: Holdings, asset allocations, risk metrics & performance data
5. Agent Evaluation: 10/10 Ground Truth Benchmark scorecard, reports & Q7/Q8 findings
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.config import DatabaseConfig
from database.connection import DatabaseManager
from database.validator import DatabaseValidator
from tools.sql_tool import SQLQueryTool
from tools.exposure_calculator import ExposureCalculator
from agent.portfolio_agent import PortfolioAgent
from agent.llm_client import GeminiClient
from evaluation.evaluator import AgentEvaluator


# ==============================================================================
# STREAMLIT CONFIGURATION & DARK NAVY / CHARCOAL THEME
# ==============================================================================
st.set_page_config(
    page_title="PL Capital | AI Portfolio Analytics",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Financial Theme Styling
st.markdown("""
<style>
    /* Dark Navy & Charcoal Theme - Force Explicit Contrast */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0B1120 !important;
        color: #F8FAFC !important;
    }
    
    /* Ensure high contrast for all standard textual elements */
    .stMarkdown, .stText, p, span, label, div {
        color: #F8FAFC;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #F8FAFC !important;
        font-weight: 700;
    }
    
    /* Headers */
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.025em;
        color: #F8FAFC !important;
        margin-bottom: 0.25rem;
    }
    .main-subtitle {
        font-size: 1.05rem;
        color: #94A3B8 !important;
        margin-bottom: 1.25rem;
        font-weight: 400;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #0F172A !important;
        border-right: 1px solid #1E293B;
    }
    [data-testid="stSidebar"] * {
        color: #E2E8F0 !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        color: #F8FAFC !important;
    }

    /* Metrics Cards */
    div[data-testid="stMetric"] {
        background-color: #1E293B !important;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 14px 18px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    div[data-testid="stMetricLabel"] {
        color: #94A3B8 !important;
        font-weight: 600;
        font-size: 0.9rem;
    }
    div[data-testid="stMetricValue"] {
        color: #38BDF8 !important;
        font-size: 1.8rem;
        font-weight: 700;
    }
    
    /* Status Badges */
    .badge-live {
        background-color: #064E3B;
        color: #6EE7B7 !important;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-mock {
        background-color: #1E3A8A;
        color: #93C5FD !important;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-warn {
        background-color: #78350F;
        color: #FCD34D !important;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    /* Expanders & Containers */
    .streamlit-expanderHeader {
        background-color: #1E293B !important;
        border-radius: 6px;
        color: #E2E8F0 !important;
    }
    
    /* Tables and Dataframes */
    div[data-testid="stTable"] {
        background-color: #1E293B !important;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# CACHED BACKEND SINGLETONS & PROVISIONING
# ==============================================================================
@st.cache_resource
def get_database_manager() -> DatabaseManager:
    """Provides cached DatabaseManager instance and ensures schema/data presence."""
    db = DatabaseManager()
    try:
        # Check if tables exist; auto-seed if needed
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT count(*) FROM sqlite_master WHERE type='table';")
            tbl_count = c.fetchone()[0]
        if tbl_count < 9:
            from database.schema import initialize_schema
            from database.ingestion import CSVIngestionService
            initialize_schema(db_manager=db)
            CSVIngestionService(db_manager=db).ingest_all()
    except Exception as e:
        logger.warning(f"Database readiness check encountered: {e}")
    return db


@st.cache_resource
def get_portfolio_agent(_db: DatabaseManager) -> PortfolioAgent:
    """Provides cached PortfolioAgent orchestrator."""
    return PortfolioAgent(db_manager=_db)


@st.cache_resource
def get_exposure_calculator(_db: DatabaseManager) -> ExposureCalculator:
    """Provides cached ExposureCalculator tool."""
    return ExposureCalculator(db_manager=_db)


@st.cache_resource
def get_sql_tool(_db: DatabaseManager) -> SQLQueryTool:
    """Provides cached SQLQueryTool."""
    return SQLQueryTool(db_manager=_db)


db_manager = get_database_manager()
portfolio_agent = get_portfolio_agent(db_manager)
exposure_calc = get_exposure_calculator(db_manager)
sql_tool = get_sql_tool(db_manager)


# ==============================================================================
# SIDEBAR NAVIGATION & SYSTEM HEALTH
# ==============================================================================
with st.sidebar:
    st.markdown("### 🏛️ **PL CAPITAL**")
    st.caption("AI Portfolio Analytics Platform")
    st.divider()

    # Page Navigation Selection
    page = st.radio(
        "Navigation",
        [
            "📊 Executive Overview",
            "💬 AI Portfolio Assistant",
            "🎯 Sector Exposure Analytics",
            "🔍 Portfolio Explorer",
            "🧪 Benchmark & Ground Truth"
        ],
        index=0
    )

    st.divider()
    st.markdown("#### **System Diagnostics**")
    
    # SQLite Status
    fk_on = db_manager.is_foreign_keys_enabled()
    st.markdown(f"**Database:** `portfolio_database.db`")
    st.markdown(f"**Foreign Keys:** {'🟢 Enforced' if fk_on else '🔴 Inactive'}")
    
    # Gemini Status
    llm_active = portfolio_agent.llm_client.is_configured
    if llm_active:
        st.markdown(f"**Gemini Model:** `{portfolio_agent.llm_client.model}`")
        st.markdown('**Mode:** <span class="badge-live">LIVE GEMINI API</span>', unsafe_allow_html=True)
    else:
        st.markdown(f"**Gemini Model:** `{portfolio_agent.llm_client.model}`")
        st.markdown('**Mode:** <span class="badge-mock">OFFLINE / MOCK ACTIVE</span>', unsafe_allow_html=True)
        st.caption("*(Set GEMINI_API_KEY in .env for live Gemini calls)*")

    st.divider()
    st.caption("PL Capital AI Engineer Assessment — 2026")


# ==============================================================================
# TOP HEADER & RENDERING DIAGNOSTICS
# ==============================================================================
st.title("🏛️ PL Capital — AI Portfolio Analytics Agent")
st.caption(
    "Intelligent financial analytics system powered by Google Gemini, "
    "precision SQL security validation, and sector exposure calculations."
)

# Top Status Indicators
diag_c1, diag_c2, diag_c3, diag_c4 = st.columns(4)
diag_c1.info(f"📁 **DB:** `portfolio_database.db` ({'🟢 FK On' if fk_on else '🔴 FK Off'})")
if llm_active:
    diag_c2.success(f"🤖 **Model:** `{portfolio_agent.llm_client.model}` (LIVE)")
else:
    diag_c2.info(f"🤖 **Model:** `{portfolio_agent.llm_client.model}` (MOCK)")
diag_c3.info(f"📑 **View:** {page}")
diag_c4.success("🟢 **System Online**")
st.divider()


# ==============================================================================
# PAGE 1: EXECUTIVE OVERVIEW
# ==============================================================================
if page == "📊 Executive Overview":
    st.markdown("### 📈 Executive Portfolio Overview")

    try:
        # Fetch Real Data from SQLite
        with db_manager.get_connection() as conn:
            df_p = pd.read_sql_query("SELECT * FROM portfolios", conn)
            df_s = pd.read_sql_query("""
                SELECT s.*, sec.sector_name 
                FROM securities s 
                LEFT JOIN sectors sec ON s.sector_id = sec.sector_id
            """, conn)
            df_tx = pd.read_sql_query("""
                SELECT t.transaction_id, p.portfolio_name, s.symbol, t.transaction_type, 
                       t.quantity, t.price, (t.quantity * t.price) as total_amount, t.transaction_date
                FROM transactions t
                JOIN portfolios p ON t.portfolio_id = p.portfolio_id
                JOIN securities s ON t.security_id = s.security_id
                ORDER BY t.transaction_date DESC LIMIT 5
            """, conn)

        total_portfolios = len(df_p)
        active_portfolios = len(df_p[df_p["status"] == "Active"])
        total_securities = len(df_s)
        total_aum = df_p["total_aum"].sum()

        # Metric Cards Row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Portfolios", f"{total_portfolios}", f"{active_portfolios} Active")
        m2.metric("Active Portfolios", f"{active_portfolios}", f"{(active_portfolios/total_portfolios*100):.0f}% of total")
        m3.metric("Tracked Securities", f"{total_securities}", f"{df_s['asset_type'].value_counts().get('Stock', 0)} Stocks / {df_s['asset_type'].value_counts().get('Bond', 0)} Bonds")
        m4.metric("Total AUM", f"${total_aum:,.0f}", "Across 13 Portfolios")

        st.divider()

        # Charts Row
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.markdown("#### **Securities Distribution by Sector**")
            df_sector_counts = df_s["sector_name"].value_counts().reset_index()
            df_sector_counts.columns = ["Sector", "Count"]

            fig_sec = px.bar(
                df_sector_counts,
                x="Count",
                y="Sector",
                orientation="h",
                color="Count",
                color_continuous_scale="Blues",
                title="Securities Count by Industry Sector"
            )
            fig_sec.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0B1120",
                plot_bgcolor="#1E293B",
                margin=dict(l=10, r=10, t=35, b=10),
                height=340,
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_sec, width="stretch")

        with chart_col2:
            st.markdown("#### **Portfolio Distribution by Target Risk Level**")
            df_risk_aum = df_p.groupby("target_risk_level")["total_aum"].sum().reset_index()

            fig_risk = px.pie(
                df_risk_aum,
                names="target_risk_level",
                values="total_aum",
                hole=0.45,
                color="target_risk_level",
                color_discrete_map={"High": "#EF4444", "Medium": "#F59E0B", "Low": "#10B981"},
                title="AUM Allocation by Risk Profile"
            )
            fig_risk.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0B1120",
                plot_bgcolor="#1E293B",
                margin=dict(l=10, r=10, t=35, b=10),
                height=340
            )
            st.plotly_chart(fig_risk, width="stretch")

        # Portfolio AUM Comparison
        st.markdown("#### **Portfolio Assets Under Management (AUM) Breakdown**")
        fig_aum = px.bar(
            df_p.sort_values(by="total_aum", ascending=True),
            x="total_aum",
            y="portfolio_name",
            orientation="h",
            color="target_risk_level",
            color_discrete_map={"High": "#EF4444", "Medium": "#F59E0B", "Low": "#10B981"},
            labels={"total_aum": "AUM ($ USD)", "portfolio_name": "Portfolio Name"},
            title="Total Assets Under Management by Portfolio"
        )
        fig_aum.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0B1120",
            plot_bgcolor="#1E293B",
            margin=dict(l=10, r=10, t=35, b=10),
            height=400
        )
        st.plotly_chart(fig_aum, width="stretch")

        # Recent Activity
        st.markdown("#### **Recent Portfolio Transactions**")
        df_tx_display = df_tx.copy()
        df_tx_display["price"] = df_tx_display["price"].apply(lambda p: f"${p:,.2f}")
        df_tx_display["total_amount"] = df_tx_display["total_amount"].apply(lambda a: f"${a:,.2f}")
        df_tx_display.columns = ["ID", "Portfolio", "Symbol", "Type", "Quantity", "Price", "Total Value", "Date"]
        st.table(df_tx_display)

    except Exception as page_err:
        st.error(f"⚠️ Error rendering Executive Overview: {page_err}")
        st.exception(page_err)


# ==============================================================================
# PAGE 2: AI PORTFOLIO ASSISTANT
# ==============================================================================
elif page == "💬 AI Portfolio Assistant":
    st.markdown("### 💬 AI Portfolio Assistant")
    st.markdown(
        "Ask natural-language questions about portfolios, holdings, sector exposures, performance, or risk metrics. "
        "The agent autonomously classifies user intent and orchestrates between the **SQL Query Tool** and **Exposure Calculator Tool**."
    )

    try:
        # Session State Setup
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        if "session_conv_id" not in st.session_state:
            st.session_state.session_conv_id = f"st_session_{int(time.time())}"

        # Suggested Prompts
        st.markdown("**Suggested Questions:**")
        q_cols = st.columns(5)
        selected_suggestion = None
        if q_cols[0].button("📊 Portfolios in Total"):
            selected_suggestion = "How many portfolios do we have in total?"
        if q_cols[1].button("🟢 Active Portfolios"):
            selected_suggestion = "What are the names of all active portfolios?"
        if q_cols[2].button("💻 Tech Securities"):
            selected_suggestion = "Which securities are in the Technology sector?"
        if q_cols[3].button("🏆 Top 5 Holdings"):
            selected_suggestion = "Show me the top 5 holdings by cost basis in the Growth Equity Fund"
        if q_cols[4].button("⚡ Sector Exposure"):
            selected_suggestion = "What are the sector exposures for the Tech Innovation Fund?"

        # Conversation Display
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if "envelope" in msg and msg["envelope"]:
                    env = msg["envelope"]
                    tool_selected = env.get("selected_tool", "none")
                    time_ms = env.get("execution_time_ms", 0.0)
                    
                    with st.expander(f"🔍 Tool Details: `{tool_selected}` ({time_ms:.1f} ms)"):
                        mode_label = "LIVE GEMINI" if portfolio_agent.llm_client.is_configured else "OFFLINE / MOCK DETERMINISTIC"
                        st.markdown(f"**Execution Engine:** `{mode_label}`")
                        st.markdown(f"**Selected Tool:** `{tool_selected}`")
                        st.markdown(f"**Execution Status:** `{env.get('status')}`")
                        
                        tool_data = env.get("tool_execution", {})
                        if "generated_sql" in tool_data and tool_data["generated_sql"]:
                            st.markdown("**Generated SQL Statement:**")
                            st.code(tool_data["generated_sql"], language="sql")
                            if "rows" in tool_data and tool_data["rows"]:
                                cols = tool_data.get("columns", [])
                                df_sql_res = pd.DataFrame(tool_data["rows"], columns=cols if cols else None)
                                st.dataframe(df_sql_res, width="stretch")

                        elif "sector_exposures" in tool_data and tool_data["sector_exposures"]:
                            st.markdown(f"**Portfolio:** `{tool_data.get('portfolio_name')}`")
                            b_ex = tool_data.get('excluded_bonds', tool_data.get('bonds_excluded', 0))
                            st.markdown(f"**Excluded Bonds:** `{b_ex}`")
                            df_exp_res = pd.DataFrame(tool_data["sector_exposures"])
                            st.dataframe(df_exp_res, width="stretch")

        # Chat Input
        user_input = st.chat_input("Ask a portfolio or exposure question...")
        if selected_suggestion:
            user_input = selected_suggestion

        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing query and orchestrating tools..."):
                    response_envelope = portfolio_agent.answer_question(
                        question=user_input,
                        conversation_id=st.session_state.session_conv_id
                    )

                    st.markdown(response_envelope["answer"])

                    # Expandable Tool Execution Box
                    with st.expander(f"🔍 Tool Details: `{response_envelope.get('selected_tool')}` ({response_envelope.get('execution_time_ms', 0):.1f} ms)"):
                        mode_label = "LIVE GEMINI" if portfolio_agent.llm_client.is_configured else "OFFLINE / MOCK DETERMINISTIC"
                        st.markdown(f"**Execution Engine:** `{mode_label}`")
                        st.markdown(f"**Selected Tool:** `{response_envelope.get('selected_tool')}`")
                        st.markdown(f"**Execution Status:** `{response_envelope.get('status')}`")
                        
                        tool_data = response_envelope.get("tool_execution", {})
                        if "generated_sql" in tool_data and tool_data["generated_sql"]:
                            st.markdown("**Generated SQL Statement:**")
                            st.code(tool_data["generated_sql"], language="sql")
                            if "rows" in tool_data and tool_data["rows"]:
                                cols = tool_data.get("columns", [])
                                df_sql_res = pd.DataFrame(tool_data["rows"], columns=cols if cols else None)
                                st.dataframe(df_sql_res, width="stretch")

                        elif "sector_exposures" in tool_data and tool_data["sector_exposures"]:
                            st.markdown(f"**Portfolio:** `{tool_data.get('portfolio_name')}`")
                            b_ex = tool_data.get('excluded_bonds', tool_data.get('bonds_excluded', 0))
                            st.markdown(f"**Excluded Bonds:** `{b_ex}`")
                            df_exp_res = pd.DataFrame(tool_data["sector_exposures"])
                            st.dataframe(df_exp_res, width="stretch")

            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response_envelope["answer"],
                "envelope": response_envelope
            })

        # Reset Conversation Button
        if st.session_state.chat_history:
            if st.button("🗑️ Reset Conversation Memory"):
                portfolio_agent.conversation_manager.clear_history(st.session_state.session_conv_id)
                st.session_state.chat_history = []
                st.rerun()

    except Exception as page_err:
        st.error(f"⚠️ Error in AI Portfolio Assistant: {page_err}")
        st.exception(page_err)


# ==============================================================================
# PAGE 3: SECTOR EXPOSURE ANALYTICS
# ==============================================================================
elif page == "🎯 Sector Exposure Analytics":
    st.markdown("### 🎯 Portfolio Sector Exposure Calculator")
    st.markdown(
        "Calculates normalized equity sector allocations for any portfolio in accordance with assessment specifications. "
        "**Bond holdings are strictly excluded** from the numerator and denominator."
    )

    try:
        with db_manager.get_connection() as conn:
            df_p_list = pd.read_sql_query("SELECT portfolio_id, portfolio_name, status, total_aum FROM portfolios ORDER BY portfolio_name", conn)

        c_sel, c_btn = st.columns([3, 1])
        with c_sel:
            target_portfolio = st.selectbox(
                "Select Portfolio to Calculate Exposure:",
                options=df_p_list["portfolio_name"].tolist(),
                index=df_p_list["portfolio_name"].tolist().index("Tech Innovation Fund") if "Tech Innovation Fund" in df_p_list["portfolio_name"].tolist() else 0
            )
        with c_btn:
            st.write("")
            st.write("")
            run_calc = st.button("⚡ Calculate Exposure", type="primary")

        if run_calc or target_portfolio:
            try:
                exp_data = exposure_calc.calculate_exposure(target_portfolio)

                # Metric Cards
                ec1, ec2, ec3, ec4 = st.columns(4)
                ec1.metric("Eligible Equities", f"{exp_data['total_equity_holdings']}")
                bonds_ex = exp_data.get('excluded_bonds', exp_data.get('bonds_excluded', 0))
                ec2.metric(
                    "Excluded Bonds",
                    f"{bonds_ex}",
                    delta="Excluded per Rules" if bonds_ex > 0 else "None",
                    delta_color="inverse"
                )
                ec3.metric("Distinct Sectors", f"{len(exp_data['sector_exposures'])}")
                ec4.metric("Normalized Exposure", f"{exp_data['total_exposure_percentage']:.1f}%")

                st.divider()

                # Charts and Tables
                col_chart, col_table = st.columns([3, 2])

                with col_chart:
                    st.markdown("#### **Sector Allocation Distribution**")
                    if exp_data["sector_exposures"]:
                        df_chart = pd.DataFrame(exp_data["sector_exposures"])
                        fig_donut = px.pie(
                            df_chart,
                            names="sector",
                            values="exposure_percentage",
                            hole=0.45,
                            color_discrete_sequence=px.colors.qualitative.Prism,
                            title=f"{target_portfolio} — Sector Breakdown"
                        )
                        fig_donut.update_traces(textposition="inside", textinfo="percent+label")
                        fig_donut.update_layout(
                            template="plotly_dark",
                            paper_bgcolor="#0B1120",
                            plot_bgcolor="#1E293B",
                            margin=dict(l=10, r=10, t=35, b=10),
                            height=350
                        )
                        st.plotly_chart(fig_donut, width="stretch")

                        # Horizontal Bar Chart
                        fig_hbar = px.bar(
                            df_chart.sort_values(by="exposure_percentage", ascending=True),
                            x="exposure_percentage",
                            y="sector",
                            orientation="h",
                            labels={"exposure_percentage": "Exposure (%)", "sector": "Sector"},
                            color="exposure_percentage",
                            color_continuous_scale="Teal",
                            title="Sector Exposure Percentages"
                        )
                        fig_hbar.update_layout(
                            template="plotly_dark",
                            paper_bgcolor="#0B1120",
                            plot_bgcolor="#1E293B",
                            margin=dict(l=10, r=10, t=35, b=10),
                            height=250,
                            coloraxis_showscale=False
                        )
                        st.plotly_chart(fig_hbar, width="stretch")
                    else:
                        st.warning(f"Portfolio '{target_portfolio}' contains zero eligible equity holdings.")

                with col_table:
                    st.markdown("#### **Sector Weights Table**")
                    if exp_data["sector_exposures"]:
                        df_exp_table = pd.DataFrame(exp_data["sector_exposures"])
                        df_exp_table.columns = ["Sector", "Raw Weight", "Exposure (%)"]
                        df_exp_table["Exposure (%)"] = df_exp_table["Exposure (%)"].apply(lambda p: f"{p:.2f}%")
                        df_exp_table["Raw Weight"] = df_exp_table["Raw Weight"].apply(lambda w: f"{w:.4f}")
                        st.table(df_exp_table)
                    else:
                        st.info("No equity sector exposure to display.")

                # Holdings Breakdown
                st.markdown("#### **Complete Portfolio Holdings & Asset Classification**")
                with db_manager.get_connection() as conn:
                    df_holdings = pd.read_sql_query("""
                        SELECT h.holding_id, s.symbol, s.company_name, sec.sector_name,
                               s.asset_type, h.quantity, s.current_price, h.current_weight
                        FROM holdings h
                        JOIN securities s ON h.security_id = s.security_id
                        LEFT JOIN sectors sec ON s.sector_id = sec.sector_id
                        JOIN portfolios p ON h.portfolio_id = p.portfolio_id
                        WHERE p.portfolio_name = ?
                        ORDER BY s.asset_type DESC, h.current_weight DESC;
                    """, conn, params=[target_portfolio])

                st.dataframe(df_holdings, width="stretch")
                st.caption("Holdings with Asset Type 'Bond' are excluded by the calculation engine.")

            except Exception as e:
                st.error(f"Exposure Calculation Error: {e}")

    except Exception as page_err:
        st.error(f"⚠️ Error rendering Sector Exposure Analytics: {page_err}")
        st.exception(page_err)


# ==============================================================================
# PAGE 4: PORTFOLIO EXPLORER
# ==============================================================================
elif page == "🔍 Portfolio Explorer":
    st.markdown("### 🔍 Portfolio & Holdings Explorer")
    st.markdown("Inspect granular holdings, asset allocation breakdowns, risk profiles, and performance history for any portfolio.")

    try:
        with db_manager.get_connection() as conn:
            df_all_portfolios = pd.read_sql_query("SELECT * FROM portfolios ORDER BY portfolio_name", conn)

        selected_exp_p = st.selectbox(
            "Select Portfolio to Inspect:",
            options=df_all_portfolios["portfolio_name"].tolist(),
            index=0
        )

        p_data = df_all_portfolios[df_all_portfolios["portfolio_name"] == selected_exp_p].iloc[0]
        p_id = int(p_data["portfolio_id"])

        # Metadata Row
        meta_c1, meta_c2, meta_c3, meta_c4 = st.columns(4)
        meta_c1.metric("Status", p_data["status"])
        meta_c2.metric("Target Risk", p_data["target_risk_level"])
        meta_c3.metric("Benchmark Index", p_data["benchmark_index"])
        meta_c4.metric("Total AUM", f"${p_data['total_aum']:,.2f}")

        st.markdown(f"**Strategy Type:** `{p_data['strategy_type']}` | **Inception / Creation Date:** `{p_data['creation_date']}`")
        st.divider()

        # Query Holdings & Asset Allocation
        with db_manager.get_connection() as conn:
            df_p_holdings = pd.read_sql_query("""
                SELECT h.holding_id, s.symbol, s.company_name, sec.sector_name,
                       s.asset_type, h.quantity, s.current_price, 
                       (h.quantity * s.current_price) as market_value,
                       h.cost_basis, h.current_weight
                FROM holdings h
                JOIN securities s ON h.security_id = s.security_id
                LEFT JOIN sectors sec ON s.sector_id = sec.sector_id
                WHERE h.portfolio_id = ?
                ORDER BY market_value DESC;
            """, conn, params=[p_id])

            df_p_perf = pd.read_sql_query("""
                SELECT * FROM portfolio_performance 
                WHERE portfolio_id = ? 
                ORDER BY performance_date DESC LIMIT 5;
            """, conn, params=[p_id])

            df_p_risk = pd.read_sql_query("""
                SELECT * FROM risk_metrics 
                WHERE portfolio_id = ? 
                ORDER BY calculation_date DESC LIMIT 1;
            """, conn, params=[p_id])

        # Visualizations
        p_chart1, p_chart2 = st.columns(2)
        with p_chart1:
            st.markdown("#### **Asset Type Breakdown**")
            df_asset_type = df_p_holdings.groupby("asset_type")["market_value"].sum().reset_index()
            fig_asset = px.pie(
                df_asset_type,
                names="asset_type",
                values="market_value",
                hole=0.4,
                color="asset_type",
                color_discrete_map={"Stock": "#38BDF8", "Bond": "#F59E0B"},
                title="Equity vs Fixed Income Allocation"
            )
            fig_asset.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0B1120",
                plot_bgcolor="#1E293B",
                margin=dict(l=10, r=10, t=35, b=10),
                height=300
            )
            st.plotly_chart(fig_asset, width="stretch")

        with p_chart2:
            st.markdown("#### **Sector Allocation (All Holdings)**")
            df_p_sectors = df_p_holdings.groupby("sector_name")["market_value"].sum().reset_index()
            fig_sec_holdings = px.pie(
                df_p_sectors,
                names="sector_name",
                values="market_value",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel,
                title="Market Value by Sector"
            )
            fig_sec_holdings.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0B1120",
                plot_bgcolor="#1E293B",
                margin=dict(l=10, r=10, t=35, b=10),
                height=300
            )
            st.plotly_chart(fig_sec_holdings, width="stretch")

        # Holdings Table
        st.markdown("#### **Detailed Portfolio Holdings**")
        df_display_holdings = df_p_holdings.copy()
        df_display_holdings["current_price"] = df_display_holdings["current_price"].apply(lambda p: f"${p:,.2f}")
        df_display_holdings["market_value"] = df_display_holdings["market_value"].apply(lambda v: f"${v:,.2f}")
        df_display_holdings["cost_basis"] = df_display_holdings["cost_basis"].apply(lambda c: f"${c:,.2f}")
        df_display_holdings["current_weight"] = df_display_holdings["current_weight"].apply(lambda w: f"{w:.4f}")
        st.dataframe(df_display_holdings, width="stretch")

        # Risk & Performance Tabs
        if not df_p_perf.empty or not df_p_risk.empty:
            st.markdown("#### **Risk & Performance Metrics**")
            t_perf, t_risk = st.tabs(["Performance History", "Risk Metrics"])
            with t_perf:
                if not df_p_perf.empty:
                    st.dataframe(df_p_perf, width="stretch")
                else:
                    st.info("No performance records found.")
            with t_risk:
                if not df_p_risk.empty:
                    st.dataframe(df_p_risk, width="stretch")
                else:
                    st.info("No risk metric calculations found.")

    except Exception as page_err:
        st.error(f"⚠️ Error rendering Portfolio Explorer: {page_err}")
        st.exception(page_err)


# ==============================================================================
# PAGE 5: AGENT EVALUATION & BENCHMARK SCORECARD
# ==============================================================================
elif page == "🧪 Benchmark & Ground Truth":
    st.markdown("### 🧪 Agent Evaluation & Benchmark Reporting")
    st.markdown(
        "Evaluates the end-to-end performance of `PortfolioAgent` across all 10 questions in `ground_truth_dataset.json`. "
        "Separately tracks Text-to-SQL (Q1–Q8), Exposure Calculator (Q9–Q10), and Overall metrics."
    )

    try:
        bench_c1, bench_c2 = st.columns([2, 4])
        with bench_c1:
            eval_mode_choice = st.radio(
                "Evaluation Mode:",
                ["Mock / Offline (Deterministic)", "Live Gemini API (Requires API Key)"],
                index=0
            )
            chosen_mode = "mock" if "Mock" in eval_mode_choice else "live"

            btn_run_eval = st.button("🚀 Run Full Benchmark", type="primary")

        with bench_c2:
            if chosen_mode == "live":
                if not portfolio_agent.llm_client.is_configured:
                    st.warning("⚠️ GEMINI_API_KEY is not configured in `.env`. Live evaluation cannot run without an API key.")
                else:
                    st.info(f"🟢 Gemini API is configured for model `{portfolio_agent.llm_client.model}`.")
            else:
                st.info("ℹ️ Running in deterministic offline mock mode. Tests full orchestration and database oracle without calling Gemini.")

        # Execution trigger
        if btn_run_eval:
            with st.spinner(f"Running 10-question evaluation in [{chosen_mode.upper()}] mode..."):
                try:
                    eval_agent = None if chosen_mode == "mock" else portfolio_agent
                    evaluator_instance = AgentEvaluator(
                        db_manager=db_manager,
                        agent=eval_agent,
                        mode=chosen_mode
                    )
                    summary_res = evaluator_instance.run_benchmark()
                    st.session_state.eval_summary = summary_res
                    st.success(f"Benchmark completed successfully! All artifacts exported to evaluation/results/")
                except Exception as e:
                    st.error(f"Evaluation Error: {e}")

        # Load from Session State or Cached Disk Artifacts
        active_summary = getattr(st.session_state, "eval_summary", None)
        if not active_summary:
            results_file = PROJECT_ROOT / "evaluation" / "results" / "benchmark_results.json"
            if results_file.is_file():
                with open(results_file, "r", encoding="utf-8") as f:
                    active_summary = json.load(f)

        if active_summary:
            ov_m = active_summary["overall_metrics"]
            sq_m = active_summary["sql_metrics"]
            ex_m = active_summary["exposure_metrics"]

            st.divider()

            # Summary Metrics
            sm1, sm2, sm3, sm4 = st.columns(4)
            sm1.metric("Tool Routing Accuracy", ov_m["routing_accuracy"], delta="100% Routing" if "10/10" in ov_m["routing_accuracy"] else None)
            sm2.metric("Execution Success Rate", ov_m["execution_success_rate"], delta="100% Exec" if "10/10" in ov_m["execution_success_rate"] else None)
            sm3.metric("Data / Calculation Accuracy", ov_m["data_accuracy"], delta="100% Data Match" if "10/10" in ov_m["data_accuracy"] else None)
            sm4.metric("Average Latency", f"{ov_m['average_latency_ms']} ms", delta=f"{ov_m['total_runtime_ms']} ms Total")

            st.markdown(f"**Evaluation Mode:** `{ov_m['evaluation_mode']}` | **Benchmark Status:** **{'PASSED (10/10)' if ov_m['all_passed'] else 'FAILED'}**")

            st.divider()

            # Category Breakdown
            sc_col1, sc_col2 = st.columns(2)
            with sc_col1:
                st.markdown("#### **Text-to-SQL Performance (Q1 – Q8)**")
                st.table(pd.DataFrame([
                    {"Metric": "Tool Routing Accuracy", "Score": sq_m["tool_selection_accuracy"]},
                    {"Metric": "SQL Generation Success", "Score": sq_m["sql_generation_success_rate"]},
                    {"Metric": "SQL Execution Success", "Score": sq_m["sql_execution_success_rate"]},
                    {"Metric": "Semantic Data Correctness", "Score": sq_m["sql_result_correctness"]},
                    {"Metric": "Average Execution Latency", "Score": f"{sq_m['average_latency_ms']} ms"}
                ]))

            with sc_col2:
                st.markdown("#### **Exposure Calculator Performance (Q9 – Q10)**")
                st.table(pd.DataFrame([
                    {"Metric": "Tool Routing Accuracy", "Score": ex_m["tool_selection_accuracy"]},
                    {"Metric": "Calculation Success Rate", "Score": ex_m["calculation_success_rate"]},
                    {"Metric": "Sector Exposure Correctness", "Score": ex_m["sector_exposure_correctness"]},
                    {"Metric": "Bond Exclusion Correctness", "Score": ex_m["bond_exclusion_correctness"]},
                    {"Metric": "Average Calculation Latency", "Score": f"{ex_m['average_latency_ms']} ms"}
                ]))

            # Question-by-Question Table
            st.markdown("#### **Detailed Question-by-Question Scorecard**")
            scorecard_display = []
            for row in active_summary["scorecard"]:
                scorecard_display.append({
                    "ID": f"Q{row['id']}",
                    "Difficulty": row["difficulty"].capitalize(),
                    "Type": row["type"],
                    "Expected Tool": row["expected_tool"],
                    "Actual Tool": row["actual_tool"],
                    "Routing": "✅ PASS" if row["tool_routing_pass"] else "❌ FAIL",
                    "Exec": "✅ PASS" if row["execution_success"] else "❌ FAIL",
                    "Data Accuracy": "✅ PASS" if row["data_accuracy_pass"] else "❌ FAIL",
                    "Time (ms)": f"{row['execution_time_ms']:.2f}",
                    "Status": "PASS" if row.get("overall_pass") else "FAIL"
                })
            st.dataframe(pd.DataFrame(scorecard_display), width="stretch")

            # Deep Dive: Q7 & Q8 Investigation
            with st.expander("🔬 Deep Dive: Q7 & Q8 Database Discrepancy Investigation"):
                st.markdown("""
                ### **Mandatory Investigation Summary**
                - **Question 7 (Tech holdings percentage across portfolios):**
                  - **Database Truth:** Exactly **8 portfolios** hold Technology stocks.
                  - **Ground Truth SQL:** Uses an `INNER JOIN` between `portfolio_tech_value` and `portfolio_total_value`, strictly returning 8 records.
                  - **Root Cause:** Prior Phase 4 reports mistakenly cited '10 portfolios' by conflating the total active portfolio count (10) with tech-holding portfolios (8).
                - **Question 8 (Portfolios with >5 sectors):**
                  - **Database Truth:** Exactly **1 portfolio** (`Total Stock Market Index Fund`) has 6 distinct equity sectors. All other portfolios have <= 4 sectors.
                  - **Ground Truth SQL:** Contains `HAVING COUNT(DISTINCT sec.sector_id) > 5`, returning strictly 1 row.
                  - **Root Cause:** Prior Phase 4 text mentioning '2 portfolios' was a narrative typo.
                """)

            # Download Artifacts
            st.markdown("#### **Exported Benchmark Artifacts**")
            dl_c1, dl_c2, dl_c3 = st.columns(3)
            res_folder = PROJECT_ROOT / "evaluation" / "results"
            if (res_folder / "benchmark_results.json").is_file():
                with open(res_folder / "benchmark_results.json", "r", encoding="utf-8") as f:
                    dl_c1.download_button("📥 Download JSON Results", f.read(), file_name="benchmark_results.json", mime="application/json")
            if (res_folder / "benchmark_results.csv").is_file():
                with open(res_folder / "benchmark_results.csv", "r", encoding="utf-8") as f:
                    dl_c2.download_button("📥 Download CSV Results", f.read(), file_name="benchmark_results.csv", mime="text/csv")
            if (res_folder / "benchmark_summary.md").is_file():
                with open(res_folder / "benchmark_summary.md", "r", encoding="utf-8") as f:
                    dl_c3.download_button("📥 Download Markdown Summary", f.read(), file_name="benchmark_summary.md", mime="text/markdown")

    except Exception as page_err:
        st.error(f"⚠️ Error rendering Benchmark & Ground Truth: {page_err}")
        st.exception(page_err)
