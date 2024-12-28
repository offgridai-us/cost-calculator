"""Module for handling user inputs in the Streamlit app."""

import streamlit as st
from typing import Dict
import pandas as pd

from charts import create_capacity_chart

def create_input_sections(unique_values) -> Dict:
    """Create all input sections in the Streamlit app."""
    st.title("Solar Datacenter LCOE Calculator", anchor=False)
    
    # System Capacity Inputs
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        datacenter_load = st.number_input("Data Center Demand (MW)", 
                                          value=100, 
                                          min_value=0,
                                          step=100,
                                          format="%d")
    with col2:
        solar_pv_capacity = st.selectbox(
            "Solar PV Capacity (MW-DC)",
            options=unique_values['solar_capacities'],
            index=2
        )
    with col3:
        bess_max_power = st.selectbox(
            "BESS Max Power (MW), 4h store",
            options=unique_values['bess_capacities'],
            index=2
        )
    with col4:
        generator_capacity = st.selectbox(
            "Generator Capacity (MW)",
            options=unique_values['generator_capacities'],
            index=2
        )
    
    # Display capacity chart
    st.plotly_chart(
        create_capacity_chart(datacenter_load, solar_pv_capacity, bess_max_power, generator_capacity),
        use_container_width=True
    )
    
    # Non-megawatt configuration inputs
    col1, col2 = st.columns(2)
    with col1:
        location = st.selectbox("Location", options=unique_values['locations'])
    with col2:
        generator_type = st.selectbox("Generator Type", ["Gas Engine", "Gas Turbine", "Diesel Generator"], index=0)
    
    # Financial Inputs
    with st.expander("Financial Inputs"):
        col1, col2 = st.columns(2)
        with col1:
            lcoe = st.number_input("LCOE ($/MWh)", value=107.35, format="%.2f")
            cost_of_debt = st.number_input("Cost of Debt (%)", value=7.5, min_value=0.0, max_value=100.0)
            leverage = st.number_input("Leverage (%)", value=70.0, min_value=0.0, max_value=100.0)
            debt_term = st.number_input("Debt Term (years)", value=20, min_value=1)
            cost_of_equity = st.number_input("Cost of Equity (%)", value=11.0, min_value=0.0, max_value=100.0)
            investment_tax_credit_pct = st.number_input("Investment Tax Credit (%)", value=30.0, min_value=0.0, max_value=100.0)
            combined_tax_rate = st.number_input("Combined Tax Rate (%)", value=21.0, min_value=0.0, max_value=100.0)
        
        with col2:
            # Create default MACRS depreciation schedule (20 years)
            if 'depreciation_schedule' not in st.session_state:
                st.session_state.depreciation_schedule = pd.DataFrame({
                    'Year': range(1, 21),
                    'Depreciation (%)': [
                        20.0,  # Year 1
                        32.0,  # Year 2
                        19.20,  # Year 3
                        11.52,  # Year 4
                        11.52,  # Year 5
                        5.76,   # Year 6
                        0.0,    # Year 7
                        0.0,    # Year 8
                        0.0,    # Year 9
                        0.0,    # Year 10
                        0.0,    # Year 11
                        0.0,    # Year 12
                        0.0,    # Year 13
                        0.0,    # Year 14
                        0.0,    # Year 15
                        0.0,    # Year 16
                        0.0,    # Year 17
                        0.0,    # Year 18
                        0.0,    # Year 19
                        0.0     # Year 20
                    ]
                })
            
            # Display editable depreciation schedule
            edited_depreciation = st.data_editor(
                st.session_state.depreciation_schedule,
                column_config={
                    "Year": st.column_config.NumberColumn(
                        "Year",
                        help="Year of depreciation",
                        min_value=1,
                        max_value=20,
                        step=1,
                        disabled=True
                    ),
                    "Depreciation (%)": st.column_config.NumberColumn(
                        "Depreciation (%)",
                        help="Percentage of total CAPEX to depreciate in this year",
                        min_value=0.0,
                        max_value=100.0,
                        step=0.1,
                        format="%.1f%%"
                    )
                },
                hide_index=True,
                width=400
            )
            
            # Update session state with edited values
            st.session_state.depreciation_schedule = edited_depreciation
    
    # CAPEX Inputs
    with st.expander("CAPEX Inputs"):
        construction_time = st.number_input("Construction Time (years)", value=2, min_value=1)
        
        # Solar PV
        st.subheader("Solar PV")
        col1, col2 = st.columns(2)
        with col1:
            pv_modules = st.number_input("Modules ($/W)", value=0.220, format="%.3f")
            pv_inverters = st.number_input("Inverters ($/W)", value=0.050, format="%.3f")
            pv_racking = st.number_input("Racking and Foundations ($/W)", value=0.180, format="%.3f")
        with col2:
            pv_balance_system = st.number_input("Balance of System ($/W)", value=0.120, format="%.3f")
            pv_labor = st.number_input("Labor ($/W)", value=0.200, format="%.3f")
    
        # BESS
        st.subheader("Battery Energy Storage System")
        col1, col2 = st.columns(2)
        with col1:
            bess_units = st.number_input("BESS Units ($/kWh)", value=200, format="%d")
            bess_balance_of_system = st.number_input("Balance of System ($/kWh)", value=40, format="%d")
        with col2:
            bess_labor = st.number_input("Labor ($/kWh)", value=20, format="%d")

        # Generators
        st.subheader("Generators")
        col1, col2 = st.columns(2)
        with col1:
            gensets = st.number_input("Gensets ($/kW)", value=800, format="%d")
            gen_balance_of_system = st.number_input("Balance of System ($/kW)", value=200, format="%d")
        with col2:
            gen_labor = st.number_input("Labor ($/kW)", value=150, format="%d")

        # System Integration
        st.subheader("System Integration")
        col1, col2 = st.columns(2)
        with col1:
            si_microgrid = st.number_input("Microgrid Switchgear, Transformers, etc. ($/kW)", value=300, format="%d")
            si_controls = st.number_input("Controls ($/kW)", value=50, format="%d")
        with col2:
            si_labor = st.number_input("System Integration Labor ($/kW)", value=60, format="%d")

        # Soft Costs
        st.subheader("Soft Costs (CAPEX)")
        col1, col2 = st.columns(2)
        with col1:
            soft_costs_general_conditions = st.number_input("General Conditions (%)", value=0.50, format="%.2f")
            soft_costs_epc_overhead = st.number_input("EPC Overhead (%)", value=5.00, format="%.2f")
            soft_costs_design_engineering = st.number_input("Design, Engineering, and Surveys (%)", value=0.50, format="%.2f")
        with col2:
            soft_costs_permitting = st.number_input("Permitting & Inspection (%)", value=0.05, format="%.2f")
            soft_costs_startup = st.number_input("Startup & Commissioning (%)", value=0.25, format="%.2f")
            soft_costs_insurance = st.number_input("Insurance (%)", value=0.50, format="%.2f")
            soft_costs_taxes = st.number_input("Taxes (%)", value=5.00, format="%.2f")
    
    # O&M Inputs
    with st.expander("O&M Inputs"):
        col1, col2 = st.columns(2)
        
        # Column 1: Asset-specific O&M
        with col1:
            st.subheader("Operations and Maintenance")
            fuel_price = st.number_input("Fuel Price ($/MMBtu)", value=5.00, format="%.2f")
            solar_om_fixed = st.number_input("Solar Fixed O&M ($/kW)", value=11, format="%d")
            bess_om_fixed = st.number_input("BESS Fixed O&M ($/kW)", value=2.5, format="%.1f")
            generator_om_fixed = st.number_input("Generator Fixed O&M ($/kW)", value=10, format="%d")
            generator_om_variable = st.number_input("Generator Variable O&M ($/kWh)", value=0.025, format="%.3f")
            bos_om_fixed = st.number_input("Balance of System Fixed O&M ($/kW-load)", value=6.0, format="%.1f")
            soft_om_pct = st.number_input("Soft O&M (% of hard capex)", value=0.25, format="%.2f")
            
        # Column 2: System-wide O&M and Escalators
        with col2:
            st.subheader("Escalators")
            om_escalator = st.number_input("O&M Escalator (% p.a.)", value=2.50, format="%.2f")
            fuel_escalator = st.number_input("Fuel Escalator (% p.a.)", value=3.00, format="%.2f")

    return {
        'location': location,
        'datacenter_load_mw': datacenter_load,
        'solar_pv_capacity_mw': solar_pv_capacity,
        'bess_max_power_mw': bess_max_power,
        'generator_capacity_mw': generator_capacity,
        'generator_type': generator_type,
        'generator_om_fixed_dollar_per_kw': generator_om_fixed,
        'generator_om_variable_dollar_per_kwh': generator_om_variable,
        'fuel_price_dollar_per_mmbtu': fuel_price,
        'fuel_escalator_pct': fuel_escalator,
        'solar_om_fixed_dollar_per_kw': solar_om_fixed,
        'bess_om_fixed_dollar_per_kw': bess_om_fixed,
        'bos_om_fixed_dollar_per_kw_load': bos_om_fixed,
        'soft_om_pct': soft_om_pct,
        'om_escalator_pct': om_escalator,
        'lcoe_dollar_per_mwh': lcoe,
        'cost_of_debt_pct': cost_of_debt,
        'leverage_pct': leverage,
        'debt_term_years': debt_term,
        'cost_of_equity_pct': cost_of_equity,
        'investment_tax_credit_pct': investment_tax_credit_pct,
        'combined_tax_rate_pct': combined_tax_rate,
        'construction_time_years': construction_time,
        'depreciation_schedule': edited_depreciation['Depreciation (%)'].tolist(),
        # Solar PV CAPEX
        'pv_modules': pv_modules,
        'pv_inverters': pv_inverters,
        'pv_racking': pv_racking,
        'pv_balance_system': pv_balance_system,
        'pv_labor': pv_labor,
        # BESS CAPEX
        'bess_units': bess_units,
        'bess_balance_of_system': bess_balance_of_system,
        'bess_labor': bess_labor,
        # Generator CAPEX
        'gensets': gensets,
        'gen_balance_of_system': gen_balance_of_system,
        'gen_labor': gen_labor,
        # System Integration CAPEX
        'si_microgrid': si_microgrid,
        'si_controls': si_controls,
        'si_labor': si_labor,
        # Soft Costs
        'soft_costs_general_conditions': soft_costs_general_conditions,
        'soft_costs_epc_overhead': soft_costs_epc_overhead,
        'soft_costs_design_engineering': soft_costs_design_engineering,
        'soft_costs_permitting': soft_costs_permitting,
        'soft_costs_startup': soft_costs_startup,
        'soft_costs_insurance': soft_costs_insurance,
        'soft_costs_taxes': soft_costs_taxes
    } 