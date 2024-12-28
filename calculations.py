"""Financial calculations and proforma generation."""

import pandas as pd
from typing import Dict, Optional, Union, Tuple

_BESS_HRS_STORAGE = 4

_POWERFLOW_COLUMNS_TO_ASSIGN = [
    # 'Solar Output - Raw (MWh)',
    'Solar Output - Net (MWh)',
    # 'BESS Throughput (MWh)',
    'BESS Net Output (MWh)',
    'Generator Output (MWh)',
    'Generator Fuel Input (MMBtu)',
    'Load Served (MWh)'
]


_EXCLUDE_FROM_NPV = [
    'Fuel Unit Cost', 'Solar Fixed O&M Rate', 'Battery Fixed O&M Rate',
    'Generator Fixed O&M Rate', 'Generator Variable O&M Rate', 'BOS Fixed O&M Rate',
    'Soft O&M Rate', 'LCOE', 'Debt Outstanding, Yr Start', 'Depreciation Schedule'
]

_CALCULATE_TOTALS = [
    'Solar Output - Net (MWh)', 'BESS Net Output (MWh)', 'Generator Output (MWh)',
    'Generator Fuel Input (MMBtu)', 'Load Served (MWh)'
]


def calculate_capex(inputs: Dict) -> Dict[str, float]:
    """Calculate CAPEX subtotals for each system component.
    
    Args:
        inputs (Dict): Dictionary containing all input parameters
        
    Returns:
        Dict[str, float]: CAPEX subtotals by component in $M
    """
    
    # Calculate Solar CAPEX
    solar_capex = inputs['solar_pv_capacity_mw'] * 1_000_000 * (
        inputs['pv_modules'] + 
        inputs['pv_inverters'] + 
        inputs['pv_racking'] + 
        inputs['pv_balance_system'] + 
        inputs['pv_labor']
    )
    
    # Calculate BESS CAPEX
    bess_system_mwh = inputs['bess_max_power_mw'] * _BESS_HRS_STORAGE
    bess_capex = bess_system_mwh * 1000 * (
        inputs['bess_units'] + 
        inputs['bess_balance_of_system'] + 
        inputs['bess_labor']
    )
    
    # Calculate Generator CAPEX
    generator_capex = inputs['generator_capacity_mw'] * 1000 * (
        inputs['gensets'] + 
        inputs['gen_balance_of_system'] + 
        inputs['gen_labor']
    )
    
    # Calculate System Integration CAPEX
    system_integration_capex = inputs['datacenter_load_mw'] * 1000 * (
        inputs['si_microgrid'] + 
        inputs['si_controls'] + 
        inputs['si_labor']
    )
    
    # Calculate total hard costs
    total_hard_costs = (
        solar_capex +
        bess_capex +
        generator_capex +
        system_integration_capex
    )
    
    # Calculate soft costs
    soft_costs = total_hard_costs * (
        inputs['soft_costs_general_conditions'] +
        inputs['soft_costs_epc_overhead'] +
        inputs['soft_costs_design_engineering'] +
        inputs['soft_costs_permitting'] +
        inputs['soft_costs_startup'] +
        inputs['soft_costs_insurance'] +
        inputs['soft_costs_taxes']
    ) / 100
    
    # Return as millions
    return {
        'solar': solar_capex / 1_000_000,
        'bess': bess_capex / 1_000_000,
        'generator': generator_capex / 1_000_000,
        'system_integration': system_integration_capex / 1_000_000,
        'soft_costs': soft_costs / 1_000_000
    }

def calculate_npv(values: pd.Series, discount_rate: float, construction_time_years: int) -> float:
    """Calculate NPV of a series of cash flows.
    
    Args:
        values (pd.Series): Series of cash flows indexed by year
        discount_rate (float): Annual discount rate in percentage (e.g., 11.0 for 11%)
        construction_time_years (int): Number of years to shift the cash flows back by
    Returns:
        float: Net Present Value of the cash flows
    """
    values = values.astype(float).fillna(0)
    years = values.index.astype(float) + construction_time_years
    
    return sum(values / (1 + discount_rate/100)**years)

def calculate_pro_forma(
    simulation_data: pd.DataFrame,
    datacenter_load_mw: Union[int, float],
    solar_pv_capacity_mw: Union[int, float],
    bess_max_power_mw: Union[int, float],
    generator_capacity_mw: Union[int, float],
    # CAPEX inputs (in $M)
    solar_capex: float,
    bess_capex: float,
    generator_capex: float,
    system_integration_capex: float,
    soft_costs_capex: float,
    # O&M inputs
    generator_om_fixed_dollar_per_kw: float,
    generator_om_variable_dollar_per_kwh: float,
    fuel_price_dollar_per_mmbtu: float,
    fuel_escalator_pct: float,
    solar_om_fixed_dollar_per_kw: float,
    bess_om_fixed_dollar_per_kw: float,
    bos_om_fixed_dollar_per_kw_load: float,
    soft_om_pct: float,
    om_escalator_pct: float,
    # Financial inputs
    lcoe_dollar_per_mwh: float,
    depreciation_schedule: pd.DataFrame,
    investment_tax_credit_pct: float,
    cost_of_debt_pct: float = 7.5,
    leverage_pct: float = 70.0,
    debt_term_years: int = 20,
    cost_of_equity_pct: float = 11.0,
    combined_tax_rate_pct: float = 21.0,
    construction_time_years: int = 2,
) -> Optional[pd.DataFrame]:
    """
    Calculate the proforma financial model for a solar datacenter project.
    
    Args:
        simulation_data (pd.DataFrame): Pre-filtered powerflow simulation data
        solar_pv_capacity_MW (Union[int, float]): Solar PV capacity in MW-DC
        bess_max_power_MW (Union[int, float]): Battery storage power capacity in MW
        generator_capacity_MW (Union[int, float]): Natural gas generator capacity in MW
        generator_om_fixed_dollar_per_kW (float): Fixed O&M cost for generator in $/kW
        generator_om_variable_dollar_per_MWh (float): Variable O&M cost for generator in $/MWh
        fuel_price_dollar_per_MMBtu (float): Fuel price in $/MMBtu
        fuel_escalator_pct (float): Annual fuel price escalation rate in %
        solar_om_fixed_dollar_per_kW (float): Fixed O&M cost for solar in $/kW
        bess_om_fixed_dollar_per_kW (float): Fixed O&M cost for battery in $/kW
        bos_om_fixed_dollar_per_kW_load (float): Fixed O&M cost for BOS in $/kW-load
        soft_om_pct (float): Soft O&M cost as a percentage of total CAPEX
        om_escalator_pct (float): Annual O&M cost escalation rate in %
        cost_of_debt_pct (float, optional): Cost of debt in %. Defaults to 7.5.
        leverage_pct (float, optional): Project leverage in %. Defaults to 70.0.
        debt_term_years (int, optional): Debt term in years. Defaults to 20.
        cost_of_equity_pct (float, optional): Cost of equity in %. Defaults to 11.0.
        investment_tax_credit_pct (float, optional): Investment tax credit in %. Defaults to 30.0.
        combined_tax_rate_pct (float, optional): Combined tax rate in %. Defaults to 21.0.
        construction_time_years (int, optional): Construction time in years. Defaults to 2.
        depreciation_schedule (pd.DataFrame): Depreciation schedule
    
    Returns:
        pd.DataFrame: Proforma financial model with years as index and metrics as columns.
    """
    # Create years index (-1 to 20)
    years = list(range(-1, 21))
    proforma = pd.DataFrame(index=years)
    proforma.index.name = 'Year'
    
    # Populate operating years with powerflow model outputs
    for year in simulation_data['Operating Year'].unique():
        year_data = simulation_data[simulation_data['Operating Year'] == year].iloc[0]
        proforma.loc[year, 'Operating Year'] = year
        for column in _POWERFLOW_COLUMNS_TO_ASSIGN:
            proforma.loc[year, column] = year_data[column]
    
    # Calculate key financial values
    total_hard_capex = solar_capex + bess_capex + generator_capex + system_integration_capex
    total_capex = total_hard_capex + soft_costs_capex
    total_debt = total_capex * (leverage_pct / 100)
    interest_rate = cost_of_debt_pct / 100
    
    # Calculate fixed debt service payment
    # PMT = PV * r * (1 + r)^n / ((1 + r)^n - 1)
    fixed_debt_payment = total_debt * interest_rate * (1 + interest_rate)**debt_term_years / ((1 + interest_rate)**debt_term_years - 1)
    
    # Calculate Federal Investment Tax Credit amount
    # ITC applicability on soft costs is the same as the proportion of hard capex that's renewable
    renewable_proportion_of_hard_capex = (solar_capex + bess_capex) / total_hard_capex
    tax_credit_amount = total_capex * renewable_proportion_of_hard_capex * (investment_tax_credit_pct / 100)
    # IRS rule: we have to reduce depreciable basis by half the tax credit amount
    amount_that_is_depreciable = total_capex - tax_credit_amount / 2

    # Initialize debt & ITC values for year 1
    proforma.loc[1, 'Debt Outstanding, Yr Start'] = total_debt
    proforma.loc[1, 'Federal ITC'] = tax_credit_amount

    ###### CONSTRUCTION PERIOD ######
    construction_years = range(-construction_time_years + 1, 1)
    capex_per_year = total_capex / construction_time_years
    
    proforma.loc[construction_years, 'Capital Expenditure'] = -1.0 * capex_per_year
    proforma.loc[construction_years, 'Debt Contribution'] = capex_per_year * (leverage_pct / 100)  # Debt portion
    proforma.loc[construction_years, 'Equity Capex'] = -1.0 * capex_per_year * (1 - leverage_pct / 100)  # Equity portion

    ###### OPERATING PERIOD ######
    operating_years = proforma.index > 0
    operating_years_zero_indexed = proforma.index[operating_years] - 1

    # Calculate escalation factors for all years
    om_escalation = (1 + om_escalator_pct/100)**operating_years_zero_indexed
    fuel_escalation = (1 + fuel_escalator_pct/100)**operating_years_zero_indexed

    ### Unit Rates ###
    # Calculate unit rates for all operating years
    proforma.loc[operating_years, 'Fuel Unit Cost'] = -1.0 * fuel_price_dollar_per_mmbtu * fuel_escalation
    proforma.loc[operating_years, 'Solar Fixed O&M Rate'] = -1.0 * solar_om_fixed_dollar_per_kw * om_escalation
    proforma.loc[operating_years, 'Battery Fixed O&M Rate'] = -1.0 * bess_om_fixed_dollar_per_kw * om_escalation
    proforma.loc[operating_years, 'Generator Fixed O&M Rate'] = -1.0 * generator_om_fixed_dollar_per_kw * om_escalation
    proforma.loc[operating_years, 'Generator Variable O&M Rate'] = -1.0 * generator_om_variable_dollar_per_kwh * om_escalation
    proforma.loc[operating_years, 'BOS Fixed O&M Rate'] = -1.0 * bos_om_fixed_dollar_per_kw_load * om_escalation
    proforma.loc[operating_years, 'Soft O&M Rate'] = -1.0 * soft_om_pct * om_escalation

    # Calculate Fixed O&M Cost
    proforma.loc[operating_years, 'Fixed O&M Cost'] = (
        (proforma.loc[operating_years, 'Solar Fixed O&M Rate'] * solar_pv_capacity_mw * 1000 +
         proforma.loc[operating_years, 'Battery Fixed O&M Rate'] * bess_max_power_mw * 1000 +
         proforma.loc[operating_years, 'Generator Fixed O&M Rate'] * generator_capacity_mw * 1000 +
         proforma.loc[operating_years, 'BOS Fixed O&M Rate'] * datacenter_load_mw * 1000) / 1_000_000 +
        proforma.loc[operating_years, 'Soft O&M Rate'] / 100 * total_hard_capex
    )

    # Calculate Fuel Cost
    proforma.loc[operating_years, 'Fuel Cost'] = (
        proforma.loc[operating_years, 'Fuel Unit Cost'] * 
        proforma.loc[operating_years, 'Generator Fuel Input (MMBtu)']
    ) / 1_000_000
    
    # Calculate Variable O&M Cost
    proforma.loc[operating_years, 'Variable O&M Cost'] = (
        proforma.loc[operating_years, 'Generator Variable O&M Rate'] * 
        proforma.loc[operating_years, 'Generator Output (MWh)'] * 1000
    ) / 1_000_000

    # Calculate total operating costs
    proforma.loc[operating_years, 'Total Operating Costs'] = (
        proforma.loc[operating_years, 'Fuel Cost'] +
        proforma.loc[operating_years, 'Fixed O&M Cost'] +
        proforma.loc[operating_years, 'Variable O&M Cost']
    )

    ### Earnings ###
    # Set LCOE from input and calculate Revenue
    proforma.loc[operating_years, 'LCOE'] = lcoe_dollar_per_mwh
    proforma.loc[operating_years, 'Revenue'] = (
        lcoe_dollar_per_mwh * 
        proforma.loc[operating_years, 'Load Served (MWh)']
    ) / 1_000_000

    # Calculate EBITDA (Revenue - Total Operating Costs)
    proforma.loc[operating_years, 'EBITDA'] = (
        proforma.loc[operating_years, 'Revenue'] + 
        proforma.loc[operating_years, 'Total Operating Costs']
    )

    ### Debt, Tax, Capital ###
    for year in [y for y in years if y > 0]:
        # Interest expense is rate * start of period balance
        proforma.loc[year, 'Interest Expense'] = -1.0 * proforma.loc[year, 'Debt Outstanding, Yr Start'] * interest_rate
        # Total debt service is the fixed payment
        proforma.loc[year, 'Debt Service'] = -1.0 * fixed_debt_payment
        # Principal is the difference between total payment and interest
        proforma.loc[year, 'Principal Payment'] = proforma.loc[year, 'Debt Service'] - proforma.loc[year, 'Interest Expense']
        
        if year < debt_term_years:  # If it's not the last year, update debt for next year
            proforma.loc[year+1, 'Debt Outstanding, Yr Start'] = proforma.loc[year, 'Debt Outstanding, Yr Start'] + proforma.loc[year, 'Principal Payment']
        
        # Calculate depreciation amount
        proforma.loc[year, 'Depreciation Schedule'] = depreciation_schedule[year-1] if year <= len(depreciation_schedule) else 0
        proforma.loc[year, 'Depreciation (MACRS)'] = -1.0 * (proforma.loc[year, 'Depreciation Schedule'] / 100) * amount_that_is_depreciable

        # Calculate taxable income and tax benefit/liability
        proforma.loc[year, 'Taxable Income'] = (
            proforma.loc[year, 'EBITDA'] + 
            proforma.loc[year, 'Depreciation (MACRS)'] + 
            proforma.loc[year, 'Interest Expense']  # This is from the Debt section
        )
        proforma.loc[year, 'Interest Expense (Tax)'] = proforma.loc[year, 'Interest Expense']  # Copy for display in Tax section

    tax_on_income = proforma['Taxable Income'] * (combined_tax_rate_pct / 100)
    proforma['Tax Benefit (Liability)'] = -1.0 * tax_on_income + proforma['Federal ITC'].fillna(0)

    # Calculate After-Tax Net Equity Cash Flow
    proforma['After-Tax Net Equity Cash Flow'] = (
        proforma['EBITDA'].fillna(0) +
        proforma['Debt Service'].fillna(0) +
        proforma['Tax Benefit (Liability)'].fillna(0) +
        proforma['Equity Capex'].fillna(0)
    )

    # Calculate NPVs for financial metrics
    for col in proforma.columns:
        # For consumption metrics, just sum, don't discount
        if col in _CALCULATE_TOTALS:
            proforma.loc['NPV', col] = proforma.loc[proforma.index != 'NPV', col].sum()
        # Don't calculate NPV or total for these columns
        elif col in _EXCLUDE_FROM_NPV:
            proforma.loc['NPV', col] = None
        # Calculate NPV for everything else
        elif col not in ['Operating Year']:
            values = proforma.loc[proforma.index != 'NPV', col].fillna(0)
            proforma.loc['NPV', col] = calculate_npv(values, cost_of_equity_pct, construction_time_years)

    return proforma.round(2)
