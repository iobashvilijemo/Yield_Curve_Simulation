import streamlit as st
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import numpy as np
from collections import defaultdict

# Define tenor mappings
tenor_to_years = {
    '3M': 0.25,
    '6M': 0.5,
    '1Y': 1.0,
    '2Y': 2.0,
    '3Y': 3.0,
    '4Y': 4.0,
    '5Y': 5.0,
    '7Y': 7.0
}

def simulate_yield_curve(base_curve, pivot_tenor, shift_value, short_end_factor, long_end_factor, short_end_cap, long_end_cap):
    pivot_year = tenor_to_years[pivot_tenor]
    pivot_rate = base_curve[pivot_tenor]
    simulated_curve = {}

    for tenor, original_rate in base_curve.items():
        t_year = tenor_to_years[tenor]
        delta_years = t_year - pivot_year

        if tenor == pivot_tenor:
            new_rate = pivot_rate + shift_value
        elif t_year < pivot_year:
            raw_change = shift_value + delta_years * short_end_factor
            capped_change = max(raw_change, short_end_cap)
            new_rate = original_rate + capped_change    
        else:
            raw_change = shift_value + delta_years * long_end_factor
            capped_change = min(raw_change, long_end_cap)
            new_rate = original_rate + capped_change
            

        simulated_curve[tenor] = round(new_rate, 6)

    return simulated_curve


def reverse_engineer_factors(base_curve, simulated_curve, pivot_tenor):
    tenor_to_years = {
        '3M': 0.25,
        '6M': 0.5,
        '1Y': 1.0,
        '2Y': 2.0,
        '3Y': 3.0,
        '4Y': 4.0,
        '5Y': 5.0,
        '7Y': 7.0
    }

    pivot_year = tenor_to_years[pivot_tenor]
    base_pivot_rate = base_curve[pivot_tenor]
    sim_pivot_rate = simulated_curve[pivot_tenor]

    # Calculate shift
    shift_value = sim_pivot_rate - base_pivot_rate

    # Prepare data for regression
    short_x, short_y = [], []
    long_x, long_y = [], []

    for tenor in base_curve:
        if tenor == pivot_tenor:
            continue
        t_year = tenor_to_years[tenor]
        delta_years = t_year - pivot_year
        base_rate = base_curve[tenor]
        sim_rate = simulated_curve[tenor]

        implied_change = sim_rate - (base_pivot_rate + shift_value)

        if t_year < pivot_year:
            short_x.append([delta_years])
            short_y.append(implied_change)
        else:
            long_x.append([delta_years])
            long_y.append(implied_change)

    # Linear regression for short and long ends
    short_model = LinearRegression().fit(short_x, short_y) if short_x else None
    long_model = LinearRegression().fit(long_x, long_y) if long_x else None

    short_end_factor = short_model.coef_[0] if short_model else 0.0
    long_end_factor = long_model.coef_[0] if long_model else 0.0

    # Estimate caps: compare predicted vs actual
    short_end_cap = float('-inf')
    long_end_cap = float('inf')
    
    changes = {}
    short_changes = defaultdict(int)
    long_changes = defaultdict(int)

    for tenor in base_curve:
        if tenor == pivot_tenor:
            continue
        t_year = tenor_to_years[tenor]
        delta_years = t_year - pivot_year

        predicted_change = shift_value + (
            delta_years * (short_end_factor if t_year < pivot_year else long_end_factor)
        )
        actual_change = simulated_curve[tenor] - base_pivot_rate
        
        changes[t_year] = actual_change
    
    for key, change in changes.items():
        if key < pivot_year:
            short_changes[round(change,8)] += 1
        elif key > pivot_year:
            long_changes[round(change,8)] += 1

    short_end_cap = next((val for val, count in short_changes.items() if count>1), float('-inf'))
    long_end_cap = next((val for val, count in long_changes.items() if count>1), float('inf'))       

        

    return {
        'pivot_tenor': pivot_tenor,
        'shift_value': round(shift_value, 6),
        'short_end_factor': round(short_end_factor, 6),
        'long_end_factor': round(long_end_factor, 6),
        'short_end_cap': round(short_end_cap, 6),
        'long_end_cap': round(long_end_cap, 6),
    }

def plot_curves(base_curve, simulated_curve):
    x = [tenor_to_years[t] for t in base_curve]
    y_base = [base_curve[t] for t in base_curve]
    y_sim = [simulated_curve[t] for t in base_curve]

    fig, ax = plt.subplots()
    ax.plot(x, y_base, label='Base Curve', marker='o')
    ax.plot(x, y_sim, label='Simulated Curve', marker='o', linestyle='--')
    ax.set_title('Yield Curve Comparison')
    ax.set_xlabel('Tenor (Years)')
    ax.set_ylabel('Yield')
    ax.legend()
    ax.grid(True)
    return fig

# Streamlit App
st.markdown(
    "<h1 style='text-align: center;'>📉 Yield Curve Simulation</h1>",
    unsafe_allow_html=True
)
col1, col2 = st.columns([0.04, 0.92])
with col1:
    st.markdown("⚙️", unsafe_allow_html=True)
with col2:
    option = st.selectbox("Choose Mode", ["Simulate Curve", "Reverse Engineer Factors"])
#option = st.selectbox("Choose Mode", ["Simulate Curve", "Reverse Engineer Factors"])

# Define and optionally override base curve
default_base_curve = {
    '3M': 0.03,
    '6M': 0.031,
    '1Y': 0.032,
    '2Y': 0.034,
    '3Y': 0.036,
    '4Y': 0.038,
    '5Y': 0.041,
    '7Y': 0.045
}

st.subheader("Base Curve Definition")
custom_base = {}
for tenor in default_base_curve:
    custom_base[tenor] = st.number_input(f"Base Yield for {tenor}", value=default_base_curve[tenor], step=0.0001, format="%.4f")

if option == "Simulate Curve":
    st.subheader("Input Parameters for Simulation")
    pivot_tenor = st.selectbox("Pivot Tenor", list(custom_base.keys()))
    shift = st.number_input("Shift Value", value=0.001, step=0.0001, format="%.6f")
    short_factor = st.number_input("Short End Factor", value=0.002, step=0.0001, format="%.6f")
    long_factor = st.number_input("Long End Factor", value=0.003, step=0.0001, format="%.6f")
    short_cap = st.number_input("Short End Cap", value=0.00, step=0.0001, format="%.6f")
    long_cap = st.number_input("Long End Cap", value=0.0015, step=0.0001, format="%.6f")

    if st.button("Simulate"):
        simulated = simulate_yield_curve(custom_base, pivot_tenor, shift, short_factor, long_factor, short_cap, long_cap)
        st.write("Recovered Factors:", simulated)
        st.pyplot(plot_curves(custom_base, simulated))

elif option == "Reverse Engineer Factors":
    st.subheader("Input Simulated Curve for Reverse Engineering")
    pivot_tenor = st.selectbox("Pivot Tenor", list(custom_base.keys()), key="pivot")
    sim_curve = {}
    for tenor in custom_base:
        sim_curve[tenor] = st.number_input(f"Simulated Yield for {tenor}", value=custom_base[tenor] + 0.001, step=0.0001, format="%.6f")

    if st.button("Reverse Engineer"):
        results = reverse_engineer_factors(custom_base, sim_curve, pivot_tenor)
        st.write("Recovered Factors:", results)
        st.pyplot(plot_curves(custom_base, sim_curve))
