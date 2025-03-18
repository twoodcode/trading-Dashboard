import pandas as pd
import streamlit as st

# Streamlit Dashboard UI
st.set_page_config(layout="wide")
st.title("📊 Multi-Instrument Range Finder - Playbook Generator")

# ---- FILE UPLOAD SECTION ----
st.sidebar.header("📂 Upload CSV Files for Each Instrument")

instruments = ["Instrument 1", "Instrument 2", "Instrument 3", "Instrument 4"]
timeframes = ["1 Year", "6 Months", "3 Months", "1 Month"]

# Dictionary to store uploaded files and instrument names
instrument_data = {}
instrument_labels = {}

for instrument in instruments:
    with st.sidebar.expander(f"➕ {instrument}"):
        # Editable instrument name
        new_label = st.text_input(f"Rename {instrument}", instrument, key=f"label_{instrument}")
        instrument_labels[instrument] = new_label

        instrument_data[instrument] = {}

        for timeframe in timeframes:
            uploaded_file = st.file_uploader(f"Upload {new_label} - {timeframe} CSV", type=["csv"], key=f"{instrument}_{timeframe}")
            if uploaded_file is not None:
                df = pd.read_csv(uploaded_file)

                # Detect date column dynamically
                date_columns = [col for col in df.columns if 'date' in col.lower() or 'day' in col.lower()]
                if date_columns:
                    df.rename(columns={date_columns[0]: 'Date'}, inplace=True)

                instrument_data[instrument][timeframe] = df

# ---- PLAYBOOK GENERATOR (Individual Tables per Instrument) ----
st.subheader("📖 Playbook Generator")

# Numeric input for filtering minimum strike rate (default 75%)
min_strike_rate = st.number_input("Minimum Strike Rate for Playbook", min_value=50, max_value=100, value=75, step=1)

# Store combined data
all_instruments_data = []

for instrument, data in instrument_data.items():
    label = instrument_labels[instrument]  # Use user-defined label
    if all(timeframe in data for timeframe in timeframes):  # Ensure all 4 timeframes are uploaded
        st.subheader(f"📌 {label}")

        # Load necessary columns
        df = data["1 Month"].copy()
        required_columns = ['Date', 'RangeStart', 'RangeEnd', 'StrikeRate']
        for col in required_columns:
            if col not in df.columns:
                df[col] = "N/A"  # Fill missing columns with "N/A" for display

        # Rename strike rate column
        merged_ranges = df.rename(columns={'StrikeRate': 'Strike_1M'})

        for timeframe, column_name in zip(["3 Months", "6 Months", "1 Year"], ["Strike_3M", "Strike_6M", "Strike_1Y"]):
            if timeframe in data and 'StrikeRate' in data[timeframe].columns and 'Date' in data[timeframe].columns:
                merged_ranges = merged_ranges.merge(
                    data[timeframe][['Date', 'RangeStart', 'RangeEnd', 'StrikeRate']].rename(columns={'StrikeRate': column_name}),
                    on=['Date', 'RangeStart', 'RangeEnd'], how='inner'
                )

        # Define weight distribution
        weights = {'Strike_1M': 0.1, 'Strike_3M': 0.2, 'Strike_6M': 0.3, 'Strike_1Y': 0.4}

        # Compute weighted strike rate
        merged_ranges['Weighted_Strike'] = (
            merged_ranges['Strike_1M'] * weights['Strike_1M'] +
            merged_ranges['Strike_3M'] * weights['Strike_3M'] +
            merged_ranges['Strike_6M'] * weights['Strike_6M'] +
            merged_ranges['Strike_1Y'] * weights['Strike_1Y']
        )

        # Filter based on strike rate threshold
        merged_ranges = merged_ranges[merged_ranges['Weighted_Strike'] >= min_strike_rate]

        # Add instrument classification
        merged_ranges['Instrument'] = label

        # Store for combined table
        all_instruments_data.append(merged_ranges[['Instrument', 'Date', 'RangeStart', 'RangeEnd', 'Strike_1M', 'Strike_3M', 'Strike_6M', 'Strike_1Y', 'Weighted_Strike']])

        # ---- Individual Table View ----
        st.dataframe(merged_ranges[['Instrument', 'Date', 'RangeStart', 'RangeEnd', 'Strike_1M', 'Strike_3M', 'Strike_6M', 'Strike_1Y', 'Weighted_Strike']])

# ---- Combined Table for All Instruments ----
if all_instruments_data:
    st.subheader("📊 Combined Playbook for All Instruments")
    combined_df = pd.concat(all_instruments_data).reset_index(drop=True)
    st.dataframe(combined_df)
