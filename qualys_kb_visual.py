import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Set page to wide mode
st.set_page_config(page_title="Qualys KB Dashboard", layout="wide")

@st.cache_data
def load_and_clean_data():
    # Load the CSV
    df = pd.read_csv('qualys_kb.csv')
    
    # 1. ROBUST DATE CLEANING
    # Format: 03/16/2005 at 02:00:00 AM (GMT-0600)
    for col in ['Published', 'Modified']:
        # Split out the timezone, remove the word 'at', and parse
        clean_date_str = df[col].astype(str).str.split(' \(').str[0].str.replace(' at ', ' ')
        df[col + '_Cleaned'] = pd.to_datetime(clean_date_str, errors='coerce')

    # 2. ROBUST CVSS CLEANING
    # Removes the leading quote and handles the dash '-' values
    for col in ['CVSS Base', 'CVSS3.1 Base']:
        df[col] = (
            df[col].astype(str)
            .str.replace("'", "")  # Remove leading quote
            .replace("-", "0")     # Convert dash to zero
            .pipe(pd.to_numeric, errors='coerce')
            .fillna(0)
        )
    
    return df

try:
    df = load_and_clean_data()

    # --- 1. NUMBERS (METRICS) ---
    st.title("🛡️ Qualys KnowledgeBase Analytics")
    
    # Logic for "Published in last 30 days"
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_qids = len(df[df['Published_Cleaned'] >= thirty_days_ago])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total QIDs", f"{len(df):,}")
    m2.metric("New (Last 30 Days)", f"{recent_qids:,}")
    m3.metric("Avg CVSS 3.1", f"{df[df['CVSS3.1 Base'] > 0]['CVSS3.1 Base'].mean():.2f}")
    m4.metric("High/Critical (CVSS 7+)", f"{len(df[df['CVSS3.1 Base'] >= 7]):,}")

    st.divider()

    # --- 2. VISUALS ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 QID Distribution by Category")
        # Top 15 Categories for a clean visual
        cat_counts = df['Category'].value_counts().head(15).reset_index()
        cat_counts.columns = ['Category', 'Count']
        fig_bar = px.bar(cat_counts, x='Count', y='Category', orientation='h', color='Count')
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.subheader("🔥 Top 10 CVSS 3.1 Base Scores")
        # Sorting for the top 10 highest scores
        top_10 = df.nlargest(10, 'CVSS3.1 Base')[['Title', 'CVSS3.1 Base', 'QID']]
        fig_top = px.bar(top_10, x='CVSS3.1 Base', y='Title', orientation='h', 
                         color='CVSS3.1 Base', text='QID', color_continuous_scale='Reds')
        fig_top.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_top, use_container_width=True)

    # --- 3. SEARCH & TABLE ---
    st.divider()
    st.subheader("🔍 KnowledgeBase Explorer")

    # Search inputs in a row
    with st.container():
        s_col1, s_col2, s_col3 = st.columns([1, 2, 1])
        with s_col1:
            search_qid = st.text_input("Search by QID", placeholder="e.g., 105142")
        with s_col2:
            search_title = st.text_input("Search by Title", placeholder="e.g., IIS Server")
        with s_col3:
            st.write("##") # Alignment space
            search_clicked = st.button("Search KB", use_container_width=True)

    # Filtering Logic
    filtered_df = df.copy()
    if search_clicked:
        if search_qid:
            filtered_df = filtered_df[filtered_df['QID'].astype(str).str.contains(search_qid.strip())]
        if search_title:
            filtered_df = filtered_df[filtered_df['Title'].str.contains(search_title.strip(), case=False, na=False)]

    # Display Table
    if search_clicked and (search_qid or search_title):
        st.write(f"Showing {len(filtered_df)} results for your search:")
        st.dataframe(filtered_df.drop(columns=['Published_Cleaned', 'Modified_Cleaned']), use_container_width=True)
    else:
        st.write("### Preview: Top 10 Rows (Entire CSV)")
        # Cleaned display (remove the internal datetime columns used for sorting)
        st.dataframe(df.drop(columns=['Published_Cleaned', 'Modified_Cleaned']).head(10), use_container_width=True)

except Exception as e:
    st.error(f"Error loading or processing data: {e}")
    st.info("Check if your CSV is named 'qualys_kb.csv' and is in the same folder.")