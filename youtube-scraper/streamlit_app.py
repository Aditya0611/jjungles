import streamlit as st
import pandas as pd
import plotly.express as px
from src.supabase_storage import fetch_trends, fetch_scraping_logs
from src.config import get_config

st.set_page_config(page_title="YouTube Trends Dashboard", layout="wide")

st.title("YouTube Scraper Dashboard")
st.markdown("Monitor trending hashtags, sentiment, and scraping performance.")

# Sidebar Filters
st.sidebar.header("Filters")
platform_filter = st.sidebar.selectbox("Platform", ["All", "youtube", "tiktok", "instagram", "twitter/x"], index=0)
min_engagement = st.sidebar.slider("Min Engagement Score", 0, 100, 0)
days_back = st.sidebar.slider("Days Back", 1, 30, 7)

# Helper to load data
@st.cache_data(ttl=300)
def load_data(table_name, limit=1000, platform="All", min_score=0):
    if table_name == "trends":
        data = fetch_trends(limit=limit, platform=platform, min_score=min_score)
    elif table_name == "scraping_logs":
        data = fetch_scraping_logs(limit=limit)
    else:
        data = []
    
    return pd.DataFrame(data)

# Tabs
tab1, tab2 = st.tabs(["Trending Analytics", "Scraping Logs"])

with tab1:
    st.header("Trending Hashtags Analytics")
    
    # Load Trends Data
    try:
        df_trends = load_data("trends", limit=2000, platform=platform_filter, min_score=min_engagement)
        
        if not df_trends.empty:
            # Stats metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Hashtags Tracked", len(df_trends))
            with col2:
                st.metric("Avg Engagement Score", f"{df_trends['engagement_score'].mean():.1f}")
            with col3:
                positive_ratio = (df_trends['sentiment_label'] == 'positive').mean() * 100
                st.metric("Positive Sentiment %", f"{positive_ratio:.1f}%")

            # Top Hashtags Bar Chart
            st.subheader("Top Hashtags by Engagement")
            top_engaged = df_trends.nlargest(10, "engagement_score")
            fig_bar = px.bar(
                top_engaged, 
                x="topic_hashtag", 
                y="engagement_score", 
                color="sentiment_label",
                title="Top 10 Hashtags by Engagement Score & Sentiment",
                hover_data=["views", "posts"]
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # Sentiment Distribution
            st.subheader("Sentiment Distribution")
            fig_pie = px.pie(df_trends, names='sentiment_label', title='Overall Sentiment Distribution')
            st.plotly_chart(fig_pie)

            # Raw Data
            st.subheader("Recent Data")
            st.dataframe(df_trends[['scraped_at', 'topic_hashtag', 'engagement_score', 'sentiment_label', 'views', 'posts', 'platform']])
        else:
            st.info("No trend data found in database.")
            
    except Exception as e:
        st.error(f"Error loading trends data: {e}")

with tab2:
    st.header("Scraper Execution Logs")
    
    try:
        df_logs = load_data("scraping_logs", limit=100)
        
        if not df_logs.empty:
            # Status Metrics
            success_count = len(df_logs[df_logs['status'] == 'success'])
            fail_count = len(df_logs[df_logs['status'] == 'failure'])
            
            c1, c2 = st.columns(2)
            c1.metric("Successful Runs", success_count)
            c2.metric("Failed Runs", fail_count)

            # Timeline
            st.subheader("Execution History")
            fig_line = px.scatter(df_logs, x="created_at", y="duration_seconds", color="status", size="items_collected", hover_data=["error_message"])
            st.plotly_chart(fig_line, use_container_width=True)
            
            # Logs Table
            st.dataframe(df_logs)
        else:
            st.info("No scraping logs found.")
            
    except Exception as e:
        st.error(f"Error loading logs: {e}")
