import sqlite3
import pandas as pd
import streamlit as st
import time

DB_NAME = "telemetry.db"

st.set_page_config(
    page_title="CQRS Telemetry Engine Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📊 CQRS Engine Real-Time Telemetry")

refresh_rate = st.sidebar.slider("Refresh rate (seconds)", 1, 10, 2)


def fetch_metrics():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            query_summary = """
                SELECT 
                    COUNT(*) as total_requests,
                    AVG(response_time_ms) as avg_latency
                FROM api_logs
            """
            df_summary = pd.read_sql_query(query_summary, conn)

            query_distribution = """
                SELECT status_code, COUNT(*) as count 
                FROM api_logs 
                GROUP BY status_code
            """
            df_dist = pd.read_sql_query(query_distribution, conn)

            query_timeline = """
                SELECT timestamp, response_time_ms, path 
                FROM api_logs 
                ORDER BY id DESC 
                LIMIT 100
            """
            df_timeline = pd.read_sql_query(query_timeline, conn)
            if not df_timeline.empty:
                df_timeline['timestamp'] = pd.to_datetime(df_timeline['timestamp'])
                df_timeline = df_timeline.sort_values('timestamp')

            return df_summary, df_dist, df_timeline
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


placeholder = st.empty()

while True:
    df_summary, df_dist, df_timeline = fetch_metrics()

    with placeholder.container():
        if df_summary.empty or df_summary["total_requests"].iloc[0] == 0:
            st.warning(
                "No telemetry data found in telemetry.db yet. Start sending API traffic to populate the dashboard.")
        else:
            total_reqs = int(df_summary["total_requests"].iloc[0])
            avg_lat = float(df_summary["avg_latency"].iloc[0])

            kpi1, kpi2 = st.columns(2)
            kpi1.metric(label="Total Processed Requests", value=f"{total_reqs:,}")
            kpi2.metric(label="Average Latency", value=f"{avg_lat:.2f} ms")

            st.markdown("---")

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📈 Latency Timeline (Last 100 Requests)")
                if not df_timeline.empty:
                    st.line_chart(data=df_timeline, x="timestamp", y="response_time_ms", use_container_width=True)
                else:
                    st.text("Insufficient data for line chart.")

            with col2:
                st.subheader("🛑 Status Code Distribution")
                if not df_dist.empty:
                    df_dist_chart = df_dist.set_index("status_code")
                    st.bar_chart(df_dist_chart, use_container_width=True)
                else:
                    st.text("Insufficient data for bar chart.")

            st.subheader("📋 Recent Telemetry Log Output")
            if not df_timeline.empty:
                st.dataframe(
                    df_timeline.sort_values('timestamp', ascending=False),
                    use_container_width=True
                )

    time.sleep(refresh_rate)