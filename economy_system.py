# -*- coding: utf-8 -*-
# economy_system.py

import random
from typing import List
from models import Country

def calculate_budget(country: Country):
    """Calcule le budget de l'État, met à jour le trésor et la dette."""
    total_revenue = country.collect_taxes()

    weekly_interest_rate = country.calculate_interest_rate()
    interest_payment = country.debt * weekly_interest_rate
    total_expenses = (country.gdp * country.government_spending) / 52 + interest_payment

    country.budget_balance = total_revenue - total_expenses

    if country.budget_balance >= 0:
        debt_repayment = country.budget_balance * 0.5
        country.debt = max(0, country.debt - debt_repayment)
        country.treasury += (country.budget_balance - debt_repayment)
    else:
        country.debt -= country.budget_balance
        country.treasury += country.budget_balance

def simulate_economy_turn(countries: List[Country]):
    """Simule la croissance économique de tous les pays."""
    base_global_growth = random.uniform(0.001, 0.004)
    energy_price_shock = random.uniform(-0.001, 0.001)

    for country in countries:
        # --- 1. Calcul de la croissance (demande) ---
        consumption_growth = (country.approval - 0.5) * 0.005 - (country.tax_income - 0.2) * 0.01 - (country.unemployment - 0.05) * 0.01
        investment_growth = (0.25 - country.tax_corporate) * 0.01 - country.tax_production * 0.01 - (country.central_bank_rate - 0.025) * 0.1
        gov_spending_growth = (country.budget_balance / (country.gdp / 52)) * 0.05
        trade_growth = country.trade_balance / (country.gdp / 52) * 0.001

        demand_growth = consumption_growth + investment_growth + gov_spending_growth + trade_growth

        weekly_potential_growth = country.potential_growth / 52
        growth = (weekly_potential_growth * 0.5) + (demand_growth * 0.5) + base_global_growth

        # --- 2. Calcul de l'inflation ---
        demand_pull_inflation = max(0, growth - weekly_potential_growth) * 1.5
        cost_push_inflation = max(0, 0.05 - country.unemployment) * 0.5
        external_shock_inflation = energy_price_shock

        weekly_inflation = (demand_pull_inflation + cost_push_inflation + external_shock_inflation) / 52
        country.inflation = (country.inflation * 0.95) + (weekly_inflation * 52 * 0.05)

        # --- 3. Réaction de la Banque Centrale ---
        inflation_gap = country.inflation - 0.02
        unemployment_gap = country.unemployment - 0.05
        rate_adjustment = (inflation_gap * 1.5 - unemployment_gap * 0.5) / 52
        country.central_bank_rate = max(0, country.central_bank_rate + rate_adjustment)
        country.central_bank_rate = (country.central_bank_rate * 0.98) + (max(0, country.central_bank_rate + rate_adjustment) * 0.02)
        
        # --- 4. Mise à jour de l'économie ---
        country.grow_economy(growth)
        country.unemployment -= (growth - 0.002) * 0.5
        country.approval -= max(0, country.inflation - 0.03) * 0.01

        country.clamp_attributes()