# -*- coding: utf-8 -*-
# politics_system.py

import random
from typing import List, Tuple
from models import Country, Law
from game_data import LAWS

def get_available_laws():
    """Retourne la liste des lois disponibles."""
    return LAWS

def find_law_by_id(law_id: int):
    """Trouve une loi par son id."""
    return next((law for law in LAWS if law.id == law_id), None)

def apply_law_to_country(country: Country, law_id: int):
    """Applique une loi à un pays."""
    law = find_law_by_id(law_id)
    if law:
        country.apply_law(law)
        return True
    return False

def remove_law_from_country(country: Country, law_id: int):
    """Retire une loi d'un pays."""
    law = find_law_by_id(law_id)
    if law:
        country.remove_law(law)
        return True
    return False

def get_laws_by_domain():
    """Retourne un dict {domaine: [lois]}"""
    domains = {}
    for law in LAWS:
        domains.setdefault(law.domain, []).append(law)
    return domains

def simulate_election(country: Country, player_party_name: str, initial_election: bool = False) -> Tuple[bool, List[str]]:
    """Simule une élection présidentielle et législative."""
    log = []
    
    if not initial_election:
        for party in country.political_parties:
            if party.name == country.leader_party:
                performance_mod = (country.approval - 0.5) * 0.2 - (country.unemployment - 0.07) * 0.5 + country.growth * 2
                party.support = max(0.05, party.support * (1 + performance_mod))
            else:
                party.support *= (1 - (country.approval - 0.5) * 0.1)
    
    total_support = sum(p.support for p in country.political_parties)
    for party in country.political_parties:
        party.support /= total_support

    log.append("Résultats de l'élection :")
    
    total_seats = country.parliament.total_seats
    exact_seats = {p.name: p.support * total_seats for p in country.political_parties}
    allocated_seats = {p.name: int(exact_seats[p.name]) for p in country.political_parties}
    
    remaining_seats = total_seats - sum(allocated_seats.values())
    remainders = {p.name: exact_seats[p.name] - allocated_seats[p.name] for p in country.political_parties}
    sorted_parties_by_remainder = sorted(remainders.keys(), key=lambda p_name: remainders[p_name], reverse=True)
    
    for i in range(remaining_seats):
        party_to_get_seat = sorted_parties_by_remainder[i]
        allocated_seats[party_to_get_seat] += 1
        
    country.parliament.seats_distribution = allocated_seats
    for party_name, seats in sorted(allocated_seats.items(), key=lambda item: item[1], reverse=True):
        party_support = next(p.support for p in country.political_parties if p.name == party_name)
        log.append(f"  - {party_name}: {party_support*100:.1f}% des voix ({seats} sièges)")

    winner = max(country.political_parties, key=lambda p: p.support)
    country.leader_party = winner.name
    player_won = (winner.name == player_party_name)
    
    if not initial_election:
        log.append(f"\nLe parti '{winner.name}' a remporté l'élection.")
    return player_won, log

def simulate_opposition_campaign(country: Country):
    """Simule les actions des partis d'opposition pendant une campagne."""
    if not country.is_campaign_active:
        return

    gov_weakness = (0.5 - country.approval) + (country.unemployment - 0.07) * 2 + (country.inflation - 0.03) * 2
    total_gain = 0
    for party in country.political_parties:
        if party.name != country.leader_party:
            gain = random.uniform(0.0005, 0.0015) + max(0, gov_weakness * random.uniform(0.005, 0.01))
            party.support += gain
            total_gain += gain

    player_party = next((p for p in country.political_parties if p.name == country.leader_party), None)
    if player_party:
        player_party.support = max(0, player_party.support - total_gain)

def simulate_parliament_vote(country: Country, law: Law) -> bool:
    """Simule le vote d'une loi au parlement."""
    votes_for = 0
    law_domain = law.domain

    for party_name, seats in country.parliament.seats_distribution.items():
        party = next((p for p in country.political_parties if p.name == party_name), None)
        if not party: continue

        stance = party.stances.get(law_domain, 0)
        vote_chance = 0.5 + (stance * 0.45)

        if random.random() < vote_chance:
            votes_for += seats
            
    return votes_for > (country.parliament.total_seats / 2)

def form_coalition(country: Country, player_party_name: str, player_conceded: bool = False) -> Tuple[bool, str]:
    """Tente de former une coalition gouvernementale."""
    leading_party_name = max(country.parliament.seats_distribution, key=country.parliament.seats_distribution.get)
    
    if leading_party_name == player_party_name and not player_conceded:
        # Le joueur a la main, mais la logique de formation est dans le game_engine
        return True, "Vous avez la main pour former une coalition."
    else:
        # L'IA forme une coalition
        log = f"Le parti '{leading_party_name}' a formé une coalition et prend la tête du gouvernement."
        country.leader_party = leading_party_name
        return False, log

def simulate_party_economy(country: Country):
    """Simule l'économie de chaque parti politique (revenus, dépenses)."""
    
    # Population en âge de voter (approximation)
    voting_population = country.population * 0.7 

    for party in country.political_parties:
        # --- 1. Calcul des revenus hebdomadaires ---
        
        # Revenus des cotisations
        weekly_fee_income = (party.members_count * party.membership_fee) / 52 / 1_000_000 # en M€

        # Financement public (simplifié)
        # Basé sur le nombre de sièges au parlement
        seats = country.parliament.seats_distribution.get(party.name, 0)
        # Ex: 50 000 € par an et par siège -> ~960 € par semaine
        public_funding_weekly = (seats * 50000) / 52 / 1_000_000 # en M€

        total_income = weekly_fee_income + public_funding_weekly

        # --- 2. Calcul des dépenses hebdomadaires ---
        # Dépenses de fonctionnement de base + coût par élu
        party.expenses = 0.1 + (seats * 0.005) # 0.1 M€ de base + 5k€ par siège
        total_expenses = party.expenses

        # --- 3. Mise à jour des fonds ---
        party.funds += total_income - total_expenses
        party.funds = max(0, party.funds) # Les fonds ne peuvent être négatifs

        # --- 4. Évolution du nombre d'adhérents ---
        # Taux de base d'adhésion parmi les sympathisants
        base_membership_rate = 0.02 # 2% des sympathisants sont adhérents
        # Une cotisation élevée décourage l'adhésion
        fee_penalty = max(0, (party.membership_fee - 50) / 5000) # Pénalité si > 50€
        
        target_members = voting_population * party.support * (base_membership_rate - fee_penalty)
        # Lissage pour une évolution progressive
        party.members_count = int(party.members_count * 0.98 + target_members * 0.02)