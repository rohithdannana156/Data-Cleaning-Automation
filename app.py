import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import re
import io
import csv

# Cleaning Functions
def standardize_column_names(df):
    df = df.copy()
    df.columns = [re.sub(r'\s+', '_', col.lower()) for col in df.columns]
    return df

def convert_data_types(df):
    df = df.copy()
    date_pattern = r'^\d{4}-\d{2}-\d{2}$|^\d{2}/\d{2}/\d{4}$'
    for col in df.columns:
        if df[col].dtype == 'object':
            numeric_attempt = pd.to_numeric(df[col], errors='coerce')
            if numeric_attempt.notna().sum() > 0:
                df[col] = numeric_attempt
            if df[col].dtype == 'object':
                mask = df[col].astype(str).str.match(date_pattern, na=False)
                if mask.any():
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    df[col] = df[col].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else 'NaN')
        df[col] = df[col].fillna('NaN')
    return df

def handle_missing_values(df):
    df = df.copy()
    # Replace string "NaN" with real missing values
    df.replace("NaN", np.nan, inplace=True)
    for col in df.columns:
        if df[col].isna().any():
            if df[col].dtype in ['int64', 'float64']:
                df[col] = df[col].fillna(round(df[col].mean()))
            else:
                df[col] = df[col].fillna(df[col].mode().iloc[0])
    return df

def convert_back_to_integer(df):
    df = df.copy()
    numeric_cols = df.select_dtypes(include=['float64']).columns
    for col in numeric_cols:
        if (df[col].dropna() == df[col].dropna().astype(int)).all():
            df[col] = df[col].astype('int64')
    return df

def remove_outliers(df):
    df = df.copy()
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]
    return df

def drop_duplicates_ignore_case(df):
    df_copy = df.copy()

    # Identify text columns only (ignore numeric index/ID columns)
    object_cols = df_copy.select_dtypes(include='object').columns

    # Remove leading/trailing spaces from all text columns
    for col in object_cols:
        df_copy[col] = df_copy[col].str.strip()

    # Create lowercase versions for duplicate detection only
    temp_df = df_copy[object_cols].apply(lambda col: col.str.lower().str.strip())

    # Create duplicate mask
    duplicate_mask = temp_df.duplicated()

    # Remove duplicates using mask, preserving original case
    df_copy = df_copy[~duplicate_mask]

    return df_copy

def process_csv(df, options):
    df = df.copy()

    if options['dropDuplicates']:
        df = drop_duplicates_ignore_case(df)
    if options['standardizeColumns']:
        df = standardize_column_names(df)
    if options['handleMissing']:
        df = handle_missing_values(df)
    if options['convertTypes']:
        df = convert_data_types(df)
        # Convert float columns back to int if no decimal part
        df = convert_back_to_integer(df)
    if options['removeOutliers']:
        df = remove_outliers(df)
    return df

# Analysis Section
def show_data_analysis(df):
    st.subheader("📊 Data Analysis")

    numeric_df = df.select_dtypes(include=['int64', 'float64'])
    categorical_df = df.select_dtypes(include=['object'])

    # Bar Chart
    if not categorical_df.empty:
        st.markdown("**Bar Chart**")
        bar_col = st.selectbox("Select column for bar chart", categorical_df.columns, key='bar')
        fig, ax = plt.subplots()
        df[bar_col].value_counts().plot(kind='bar', ax=ax)
        ax.set_title(f"Bar Chart of {bar_col}")
        st.pyplot(fig)

    # Pie Chart
    if not categorical_df.empty:
        st.markdown("**Pie Chart**")
        pie_col = st.selectbox("Select column for pie chart", categorical_df.columns, key='pie')
        fig, ax = plt.subplots()
        df[pie_col].value_counts().plot(kind='pie', autopct='%1.1f%%', ax=ax)
        ax.set_ylabel('')
        ax.set_title(f"Pie Chart of {pie_col}")
        st.pyplot(fig)

    # Histogram
    if not numeric_df.empty:
        st.markdown("**Histogram**")
        hist_col = st.selectbox("Select column for histogram", numeric_df.columns, key='hist')
        fig, ax = plt.subplots()
        sns.histplot(df[hist_col], kde=True, ax=ax)
        ax.set_title(f"Histogram of {hist_col}")
        st.pyplot(fig)

    # Line Chart
    if not numeric_df.empty:
        st.markdown("**Line Chart**")
        line_col = st.selectbox("Select column for line chart (Y-axis)", numeric_df.columns, key='line')
        fig, ax = plt.subplots()
        df[line_col].plot(kind='line', ax=ax)
        ax.set_title(f"Line Chart of {line_col}")
        ax.set_xlabel("Index")
        ax.set_ylabel(line_col)
        st.pyplot(fig)

    # Scatter Plot
    if len(numeric_df.columns) >= 2:
        st.markdown("**Scatter Plot**")
        scatter_x = st.selectbox("X-axis", numeric_df.columns, key='scatter_x')
        scatter_y = st.selectbox("Y-axis", numeric_df.columns, key='scatter_y')
        fig, ax = plt.subplots()
        sns.scatterplot(x=df[scatter_x], y=df[scatter_y], ax=ax)
        ax.set_title(f"Scatter Plot: {scatter_x} vs {scatter_y}")
        st.pyplot(fig)

    if numeric_df.empty and categorical_df.empty:
        st.warning("No numeric or categorical columns available for visualizations.")

# Main App
st.title("📂 Data Cleaning Automation")

uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, quoting=csv.QUOTE_ALL)
        st.subheader("🔍 Original Data Preview (First 10 Rows)")
        st.dataframe(df.head(10))

        tabs = st.tabs(["🧹 Data Cleaning", "📊 Data Analysis"])

        with tabs[0]:
            st.sidebar.header("🧼 Select Cleaning Options")
            options = {
                'dropDuplicates': st.sidebar.checkbox("Drop Duplicates"),
                'standardizeColumns': st.sidebar.checkbox("Standardize Column Names"),
                'handleMissing': st.sidebar.checkbox("Handle Missing Values"),
                'convertTypes': st.sidebar.checkbox("Convert Data Types"),
                'removeOutliers': st.sidebar.checkbox("Remove Outliers")
            }

            if st.sidebar.button("🚀 Clean Data"):
                cleaned_df = process_csv(df, options)
                st.success("✅ Data cleaned successfully!")
                st.subheader("✅ Cleaned Data Preview (First 10 Rows)")
                st.dataframe(cleaned_df.head(10))

                csv_buffer = io.StringIO()
                cleaned_df.to_csv(csv_buffer, index=False)
                st.download_button("⬇️ Download Cleaned CSV", data=csv_buffer.getvalue(),
                                   file_name="cleaned_data.csv", mime="text/csv")

                st.session_state["cleaned_df"] = cleaned_df

        with tabs[1]:
            if "cleaned_df" in st.session_state:
                show_data_analysis(st.session_state["cleaned_df"])
            else:
                st.warning("Please clean the data first using the 'Data Cleaning' tab.")

    except Exception as e:
        st.error(f"❌ Error: {e}")
