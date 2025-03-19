import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")
st.title("📊 Range Finder - Playbook Generator")

# Sidebar
st.sidebar.header("📂 CSV File Upload")
num_instruments = st.sidebar.number_input("Number of Instruments", 1, 10, 3)
timeframes = ["1 Year", "6 Months", "3 Months", "1 Month"]

instrument_data, instrument_labels = {}, {}

for i in range(1, num_instruments + 1):
    with st.sidebar.expander(f"Instrument {i}"):
        name = st.text_input(f"Rename Instrument {i}", f"Instrument_{i}")
        instrument_labels[f"Instrument_{i}"] = name
        instrument_data[name] = {}

        for timeframe in timeframes:
            uploaded_file = st.file_uploader(f"{name} - {timeframe}", type=["csv"], key=f"{name}_{timeframe}")
            if uploaded_file:
                df = pd.read_csv(uploaded_file)
                if "DayOfWeek" in df.columns:
                    df.rename(columns={"DayOfWeek": "Date"}, inplace=True)
                required_columns = ["Date", "RangeStart", "RangeEnd", "StrikeRate", "AvgMAE", "AvgRangePerc"]
                df = df[[col for col in required_columns if col in df.columns]]
                instrument_data[name][timeframe] = df

st.subheader("📖 Playbook Generator")

# Filters
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    min_strike_rate = st.number_input("Min Strike Rate", min_value=0, max_value=100, value=75, step=1)
with col2:
    max_strike_rate = st.number_input("Max Strike Rate", min_value=0, max_value=100, value=100, step=1)
with col3:
    risk_filter = st.selectbox("Risk Level", ["All", "Low", "Moderate", "High"])

combined_data = []

for instrument, data in instrument_data.items():
    if all(tf in data for tf in timeframes):
        merged_df = data["1 Month"].rename(columns={
            'StrikeRate': 'Strike_1M', 'AvgMAE': 'AvgMAE_1M', 'AvgRangePerc': 'AvgRangePerc_1M'
        })

        # Merge additional timeframes
        mapping = {
            "3 Months": {"StrikeRate": "Strike_3M", "AvgMAE": "AvgMAE_3M", "AvgRangePerc": "AvgRangePerc_3M"},
            "6 Months": {"StrikeRate": "Strike_6M"},
            "1 Year": {"StrikeRate": "Strike_1Y"}
        }

        for tf, cols in mapping.items():
            df_merge = data[tf].rename(columns=cols)
            merged_df = merged_df.merge(df_merge, on=["Date", "RangeStart", "RangeEnd"], how="left")

        # Weighted Strike Rate
        weights = {"Strike_1M": 0.1, "Strike_3M": 0.2, "Strike_6M": 0.3, "Strike_1Y": 0.4}
        merged_df["Weighted_Strike"] = sum(merged_df[col].fillna(0) * weight for col, weight in weights.items())

        # MAE vs Range Ratio & Risk Level
        merged_df["MAE_Range_Ratio_1M"] = (merged_df["AvgMAE_1M"] / merged_df["AvgRangePerc_1M"]) * 100

        def risk_level(x):
            if x < 80: return "Low"
            if x <= 120: return "Moderate"
            return "High"

        merged_df["Risk_Level"] = merged_df["MAE_Range_Ratio_1M"].apply(risk_level)

        # Apply Filters
        filtered_df = merged_df[(merged_df["Weighted_Strike"] >= min_strike_rate) & (merged_df["Weighted_Strike"] <= max_strike_rate)]
        if risk_filter != "All":
            filtered_df = filtered_df[filtered_df["Risk_Level"] == risk_filter]

        filtered_df.insert(0, "Instrument", instrument)
        filtered_df = filtered_df[[
            "Instrument", "Date", "RangeStart", "RangeEnd", "AvgMAE_1M", "AvgMAE_3M", "AvgRangePerc_1M", "AvgRangePerc_3M", 
            "Strike_1M", "Strike_3M", "Strike_6M", "Strike_1Y", "Weighted_Strike", "Risk_Level"
        ]]
        combined_data.append(filtered_df)

        st.subheader(f"{instrument}")
        st.dataframe(filtered_df.sort_values("Weighted_Strike", ascending=False))

# Combined Table
if combined_data:
    st.subheader("📊 Combined Playbook")
    combined_df = pd.concat(combined_data).sort_values(by="Weighted_Strike", ascending=False).reset_index(drop=True)
    st.dataframe(combined_df)
