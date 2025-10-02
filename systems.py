# -*- coding: utf-8 -*-
# systems.py
import logging
import random
from typing import List, Tuple
from models import Country, Alliance, Law, War, Parliament
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

# -------------------------
# Économie
# -------------------------
def simulate_economy_turn(countries: List[Country]):
    """
    Simule la croissance économique de tous les pays de manière réaliste.
    La croissance dépend de la consommation, de l'investissement, des dépenses publiques
    et de la balance commerciale (formule Y = C + I + G + (X-M)).
    """
    base_global_growth = random.uniform(0.001, 0.004) # Croissance mondiale de base par tour (semaine)
    energy_price_shock = random.uniform(-0.001, 0.001) # Choc sur les prix de l'énergie

    for country in countries:
        # --- 1. Calcul de la croissance (demande) ---
        # Consommation (C) : dépend de la confiance (opinion), du revenu disponible (impôts) et du chômage.
        consumption_growth = (country.approval - 0.5) * 0.005 - (country.tax_income - 0.2) * 0.01 - (country.unemployment - 0.05) * 0.02

        # Investissement (I) : dépend des impôts sur les sociétés, des impôts de production et du coût du crédit (taux d'intérêt).
        investment_growth = (0.25 - country.tax_corporate) * 0.01 - country.tax_production * 0.01 - (country.central_bank_rate - 0.025) * 0.1

        # Dépenses publiques (G) : impact du solde budgétaire sur la demande.
        gov_spending_growth = (country.budget_balance / (country.gdp / 52)) * 0.05

        # Balance commerciale (X-M)
        trade_growth = country.trade_balance / (country.gdp / 52) * 0.01 # Impact lissé sur la croissance hebdomadaire

        # Croissance de la demande = C + I + G + (X-M)
        demand_growth = consumption_growth + investment_growth + gov_spending_growth + trade_growth

        # La croissance réelle est un mélange entre la croissance potentielle (offre) et la croissance de la demande.
        weekly_potential_growth = country.potential_growth / 52
        growth = (weekly_potential_growth * 0.4) + (demand_growth * 0.6) + base_global_growth

        # --- 2. Calcul de l'inflation ---
        # Inflation de demande : si la croissance > potentiel, les prix montent.
        demand_pull_inflation = max(0, growth - weekly_potential_growth) * 1.5
        # Inflation par les coûts : si le chômage est bas, les salaires montent.
        cost_push_inflation = max(0, 0.05 - country.unemployment) * 0.5
        # Choc externe (énergie)
        external_shock_inflation = energy_price_shock

        # Calcul de l'inflation pour la semaine
        weekly_inflation = (demand_pull_inflation + cost_push_inflation + external_shock_inflation) / 52
        country.inflation = (country.inflation * 0.95) + (weekly_inflation * 52 * 0.05) # Lissage sur l'année

        # --- 3. Réaction de la Banque Centrale ---
        # La BC ajuste son taux directeur pour viser une inflation de 2%.
        inflation_gap = country.inflation - 0.02
        unemployment_gap = country.unemployment - 0.05
        # Règle de Taylor simplifiée :
        rate_adjustment = (inflation_gap * 1.5 - unemployment_gap * 0.5) / 52 # Ajustement hebdomadaire
        country.central_bank_rate = max(0, country.central_bank_rate + rate_adjustment)
        country.central_bank_rate = (country.central_bank_rate * 0.98) + (max(0, country.central_bank_rate + rate_adjustment) * 0.02) # Lissage
        
        # Mise à jour de l'économie
        previous_gdp = country.gdp
        country.grow_economy(growth) # Applique la croissance au PIB

        # La croissance affecte le chômage : une forte croissance le réduit, une récession l'augmente.
        country.unemployment -= (growth - 0.002) * 0.5 # 0.002 est le seuil de croissance pour stabiliser l'emploi

        # L'inflation élevée est impopulaire
        country.approval -= max(0, country.inflation - 0.03) * 0.01

        country.clamp_attributes()


def trigger_event(world: List[Country], alliances: List[Alliance]) -> str:
    """Déclenche un événement mondial ou local plus réaliste."""
    event_type = random.choice([
        "economic_boom", "financial_crisis", "tech_breakthrough",
        "political_scandal", "natural_disaster", "diplomatic_summit"
    ])

    if event_type == "economic_boom" and len(world) > 1:
        country = random.choice(world)
        country.potential_growth += 0.005
        country.approval += 0.05
        return f"Boom économique en {country.name} ! La croissance potentielle et l'opinion publique augmentent."

    elif event_type == "financial_crisis":
        for country in world:
            country.gdp *= 0.98
            country.unemployment += 0.015
            country.approval -= 0.08
        return "Crise financière mondiale ! Le PIB de tous les pays chute de 2% et le chômage augmente."

    elif event_type == "tech_breakthrough":
        country = random.choice(world)
        country.potential_growth += 0.01
        return f"Percée technologique majeure en {country.name} ! La croissance potentielle à long terme est améliorée."

    elif event_type == "political_scandal":
        country = random.choice(world)
        country.approval -= 0.15
        return f"Scandale de corruption majeur éclate en {country.name}, l'opinion publique s'effondre (-15%)."

    elif event_type == "natural_disaster":
        country = random.choice(world)
        country.gdp *= 0.99
        country.treasury -= country.gdp * 0.01 # Coût de la reconstruction
        return f"Catastrophe naturelle en {country.name}. Le PIB est affecté et le gouvernement doit financer la reconstruction."

    elif event_type == "diplomatic_summit" and len(world) > 2:
        c1, c2 = random.sample(world, 2)
        relation_change = random.randint(15, 30)
        c1.set_relation(c2.name, c1.relations.get(c2.name, 0) + relation_change)
        c2.set_relation(c1.name, c2.relations.get(c1.name, 0) + relation_change)
        return f"Sommet diplomatique réussi entre {c1.name} et {c2.name}. Leurs relations s'améliorent de {relation_change} points."

    return None

def trigger_political_event(country: Country) -> str:
    """Déclenche un événement politique interne."""
    if not country.political_parties:
        return None
    event_type = random.choice(["scandal", "defection"])
    if event_type == "scandal":
        target_party = random.choice(country.political_parties)
        target_party.scandal_count += 1
        target_party.support *= 0.90 # Perte de 10% de soutien
        target_party.credibility *= 0.85 # Perte de 15% de crédibilité
        return f"Un scandale de financement éclabousse le parti '{target_party.name}', qui perd en crédibilité et en soutien."
    elif event_type == "defection":
        # Logique de défection à implémenter
        return "Une figure politique de premier plan menace de quitter son parti, créant des tensions internes."
    return None


def simulate_election(country: Country, player_party_name: str, initial_election: bool = False) -> Tuple[bool, List[str]]:
    """Simule une élection présidentielle et législative."""
    log = []
    total_support = 0
    
    if not initial_election:
        # Ajuster le soutien de chaque parti en fonction de la performance du gouvernement
        for party in country.political_parties:
            if party.name == country.leader_party:
                # Le parti au pouvoir est jugé sur le bilan
                performance_mod = (country.approval - 0.5) * 0.2 # Bonus/malus de 20% basé sur l'opinion
                performance_mod -= (country.unemployment - 0.07) * 0.5 # Malus si chômage > 7%
                performance_mod += country.growth * 2 # Bonus pour la croissance
                party.support = max(0.05, party.support * (1 + performance_mod))
            else:
                # L'opposition profite ou pâtit de la situation
                party.support *= (1 - (country.approval - 0.5) * 0.1)
    
    total_support = sum(p.support for p in country.political_parties)

    # Normaliser les scores pour que le total fasse 100%
    for party in country.political_parties:
        party.support /= total_support

    # Simuler le résultat de l'élection
    log.append("Résultats de l'élection :")
    
    # --- Allocation des sièges avec la méthode du plus fort reste pour garantir 577 sièges ---
    total_seats = country.parliament.total_seats
    # Calculer le nombre exact de sièges (avec décimales) pour chaque parti
    exact_seats = {p.name: p.support * total_seats for p in country.political_parties}
    # Attribuer la partie entière des sièges
    allocated_seats = {p.name: int(exact_seats[p.name]) for p in country.political_parties}
    
    # Calculer le nombre de sièges restants à distribuer
    remaining_seats = total_seats - sum(allocated_seats.values())
    
    # Trier les partis par la partie décimale la plus grande
    remainders = {p.name: exact_seats[p.name] - allocated_seats[p.name] for p in country.political_parties}
    sorted_parties_by_remainder = sorted(remainders.keys(), key=lambda p_name: remainders[p_name], reverse=True)
    
    # Distribuer les sièges restants un par un
    for i in range(remaining_seats):
        party_to_get_seat = sorted_parties_by_remainder[i]
        allocated_seats[party_to_get_seat] += 1
        
    country.parliament.seats_distribution = allocated_seats
    for party_name, seats in sorted(allocated_seats.items(), key=lambda item: item[1], reverse=True):
        party_support = next(p.support for p in country.political_parties if p.name == party_name)
        log.append(f"  - {party_name}: {party_support*100:.1f}% des voix ({seats} sièges)")

    # Déterminer le vainqueur
    winner = max(country.political_parties, key=lambda p: p.support)
    country.leader_party = winner.name # Mettre à jour le parti au pouvoir
    player_won = (winner.name == player_party_name)
    
    if not initial_election:
        if player_won:
            log.append(f"\nFélicitations, vous avez été réélu !")
        else:
            log.append(f"\nLe parti '{winner.name}' a remporté l'élection.")
    return player_won, log

def simulate_opposition_campaign(country: Country):
    """Simule les actions des partis d'opposition pendant une campagne."""
    if not country.is_campaign_active:
        return

    # La faiblesse du gouvernement est un score basé sur l'impopularité, le chômage et l'inflation
    gov_weakness = (0.5 - country.approval) + (country.unemployment - 0.07) * 2 + (country.inflation - 0.03) * 2

    total_gain = 0
    for party in country.political_parties:
        if party.name != country.leader_party:
            # Chaque parti d'opposition gagne un peu de soutien de base + un bonus si le gouvernement est faible
            base_gain = random.uniform(0.0005, 0.0015)
            weakness_gain = max(0, gov_weakness * random.uniform(0.005, 0.01))
            gain = base_gain + weakness_gain
            party.support += gain
            total_gain += gain

    # Le parti au pouvoir perd le soutien gagné par l'opposition
    player_party = next((p for p in country.political_parties if p.name == country.leader_party), None)
    if player_party:
        player_party.support = max(0, player_party.support - total_gain)


def simulate_parliament_vote(country: Country, law: Law) -> bool:
    """Simule le vote d'une loi au parlement."""
    votes_for = 0
    law_domain = law.domain

    # Chaque parti vote en fonction de sa position sur le domaine de la loi
    for party_name, seats in country.parliament.seats_distribution.items():
        party = next((p for p in country.political_parties if p.name == party_name), None)
        if not party:
            continue

        # La position du parti sur le domaine de la loi (-1 à +1)
        stance = party.stances.get(law_domain, 0)

        # La probabilité de voter "pour" est basée sur cette position
        # 0.5 de base, modulé par la position idéologique
        vote_chance = 0.5 + (stance * 0.45) # Stance a un fort impact

        if random.random() < vote_chance:
            votes_for += seats
            
    return votes_for > (country.parliament.total_seats / 2)

def form_coalition(country: Country, player_party_name: str, player_conceded: bool = False) -> Tuple[bool, str]:
    """Tente de former une coalition gouvernementale après une élection sans majorité absolue."""
    log = ""
    # Le parti arrivé en tête a la main pour former une coalition
    leading_party_name = max(country.parliament.seats_distribution, key=country.parliament.seats_distribution.get)
    leading_party = next((p for p in country.political_parties if p.name == leading_party_name), None)
    
    # Si le joueur est en tête et n'a pas concédé, il a la main
    if leading_party_name == player_party_name and not player_conceded:
        # Logique simplifiée : on s'allie avec le parti le plus proche idéologiquement
        player_stances = leading_party.stances
        best_partner = None
        highest_compatibility = -100

        for party in country.political_parties:
            if party.name == player_party_name: continue # type: ignore
            compatibility = sum(player_stances.get(k, 0) * party.stances.get(k, 0) for k in player_stances)
            if compatibility > highest_compatibility:
                highest_compatibility = compatibility
                best_partner = party
        
        log = f"Vous tentez de former une coalition avec '{best_partner.name}'." # type: ignore
        country.leader_party = player_party_name # Le joueur prend la tête du gouvernement
        return True, log
    # Si l'IA est en tête, elle forme une coalition de son côté
    else:
        log = f"Le parti '{leading_party_name}' a formé une coalition et prend la tête du gouvernement."
        country.leader_party = leading_party_name
        return False, log

# -------------------------
# Diplomatie
# & Guerre
# -------------------------
def create_alliance(alliances: List[Alliance], a_type: str, members: List[str], 
                   duration: int, strength: int) -> Alliance:
    """Crée une nouvelle alliance avec un nom logique"""
    new_id = max([a.id for a in alliances], default=0) + 1
    # Création du nom logique
    name = f"{a_type.capitalize()} - {' & '.join(members)}"
    alliance = Alliance(id=new_id, type=a_type, members=members, 
                       strength=strength, turns_left=duration)
    alliance.name = name  # Ajout dynamique du champ name
    alliances.append(alliance)
    return alliance


def dissolve_alliance(alliances: List[Alliance], alliance_id: int) -> bool:
    """Dissout une alliance"""
    for a in alliances:
        if a.id == alliance_id:
            a.active = False
            return True
    return False


def tick_alliances(alliances: List[Alliance]):
    """Réduit la durée des alliances d'un tour"""
    for a in alliances:
        if a.active:
            a.turns_left -= 1
            if a.turns_left <= 0:
                a.active = False


def update_relations(world: List[Country], alliances: List[Alliance]):
    """
    Met à jour les relations diplomatiques :
    - Drift naturel vers 0
    - Bonus des alliances
    - Fluctuations aléatoires
    """
    for c in world:
        for other_name, val in list(c.relations.items()):
            # Drift naturel vers neutralité
            if val > 0:
                val -= 1
            elif val < 0:
                val += 1
            val += random.randint(-1, 1)
            c.set_relation(other_name, val)
    # Bonus des alliances actives
    for a in alliances:
        if a.active:
            for m1 in a.members:
                for m2 in a.members:
                    if m1 == m2:
                        continue
                    c1 = next((c for c in world if c.name == m1), None)
                    if c1:
                        current = c1.relations.get(m2, 0)
                        c1.set_relation(m2, current + int(a.strength / 2))

def start_war(attacker: Country, defender: Country, world: List[Country], alliances: List[Alliance], wars: List[War]) -> Tuple[War, str]:
    """Déclenche une nouvelle guerre entre deux pays."""
    # Marquer les pays comme étant en guerre
    attacker.at_war_with.append(defender.name)
    defender.at_war_with.append(attacker.name)

    # Identifier les alliés militaires
    attacker_allies = [m for a in alliances if a.type == "military" and a.active and attacker.name in a.members for m in a.members if m != attacker.name]
    defender_allies = [m for a in alliances if a.type == "military" and a.active and defender.name in a.members for m in a.members if m != defender.name]

    # Créer l'objet War
    new_war_id = max([w.id for w in wars], default=0) + 1
    war = War(
        id=new_war_id,
        attacker_leader=attacker.name,
        defender_leader=defender.name,
        start_turn=0, # Sera mis à jour par le moteur de jeu
        attacker_allies=list(set(attacker_allies)),
        defender_allies=list(set(defender_allies))
    )
    wars.append(war)

    # Conséquences diplomatiques et politiques
    attacker.approval -= 0.10 # Impopularité de la guerre
    defender.approval += 0.05 # Union sacrée

    attacker_camp = [attacker.name] + war.attacker_allies
    defender_camp = [defender.name] + war.defender_allies

    for c1_name in attacker_camp:
        for c2_name in defender_camp:
            c1 = find_country(world, c1_name)
            c2 = find_country(world, c2_name)
            if c1 and c2:
                c1.set_relation(c2.name, c1.relations.get(c2.name, 0) - 50)
                c2.set_relation(c1.name, c2.relations.get(c1.name, 0) - 50)

    log_msg = f"💥 {attacker.name} a déclaré la guerre à {defender.name} ! "
    if war.attacker_allies: log_msg += f"Alliés de l'attaquant : {', '.join(war.attacker_allies)}. "
    if war.defender_allies: log_msg += f"Alliés du défenseur : {', '.join(war.defender_allies)}."
    return war, log_msg

def simulate_war_turn(war: War, world: List[Country]) -> str:
    """Simule un tour de guerre."""
    # Calcul des forces
    attacker_camp = [find_country(world, name) for name in [war.attacker_leader] + war.attacker_allies]
    defender_camp = [find_country(world, name) for name in [war.defender_leader] + war.defender_allies]
    
    attacker_power = sum(c.military_power for c in attacker_camp if c)
    defender_power = sum(c.military_power for c in defender_camp if c)

    # Déterminer l'avantage
    advantage = (attacker_power - defender_power) / max(attacker_power, defender_power, 1)
    
    if advantage > 0.2:
        narrative = f"Les forces de {war.attacker_leader} prennent l'avantage."
        war.attacker_dominance_turns += 1
        war.defender_dominance_turns = 0
    elif advantage < -0.2:
        narrative = f"Les forces de {war.defender_leader} repoussent l'offensive."
        war.defender_dominance_turns += 1
        war.attacker_dominance_turns = 0
    else:
        narrative = "Le front est stable, la guerre d'usure continue."
        war.attacker_dominance_turns = 0
        war.defender_dominance_turns = 0

    # Appliquer les effets économiques et sociaux
    for camp in [attacker_camp, defender_camp]:
        for country in camp:
            if not country: continue
            country.gdp *= (1 - random.uniform(0.005, 0.02) * war.intensity)
            country.treasury -= random.uniform(5, 20) * war.intensity
            country.unemployment += random.uniform(0.005, 0.01) * war.intensity
            country.approval -= random.uniform(0.01, 0.03) * war.intensity
            country.war_weariness += 0.02 # 2% par tour
            country.clamp_attributes()

    # Conditions de fin de guerre
    attacker_leader = find_country(world, war.attacker_leader)
    defender_leader = find_country(world, war.defender_leader)

    if attacker_leader.war_weariness > 0.8 or attacker_leader.treasury < 0:
        resolve_war(war, world, winner=defender_leader, loser=attacker_leader)
        return f"Capitulation de {attacker_leader.name} ! {defender_leader.name} a gagné la guerre."
    if defender_leader.war_weariness > 0.8 or defender_leader.treasury < 0:
        resolve_war(war, world, winner=attacker_leader, loser=defender_leader)
        return f"Capitulation de {defender_leader.name} ! {attacker_leader.name} a gagné la guerre."
    if war.attacker_dominance_turns >= 5:
        resolve_war(war, world, winner=attacker_leader, loser=defender_leader)
        return f"Victoire militaire décisive pour {attacker_leader.name} !"
    if war.defender_dominance_turns >= 5:
        resolve_war(war, world, winner=defender_leader, loser=attacker_leader)
        return f"Victoire militaire décisive pour {defender_leader.name} !"

    return narrative

def resolve_war(war: War, world: List[Country], winner: Country, loser: Country):
    """Gère la fin d'une guerre."""
    war.status = "finished"
    
    # Nettoyer les listes at_war_with
    for country in world:
        country.at_war_with = []
        country.war_weariness = 0

    # Réparations
    reparations = loser.gdp * random.uniform(0.1, 0.3)
    loser.treasury -= reparations
    winner.treasury += reparations

    # Conséquences
    loser.approval -= 0.20
    loser.debt += loser.gdp * 0.20
    loser.unemployment += 0.05
    
    war_duration = 1 # A récupérer depuis le game engine
    if war_duration < 26:
        winner.approval += 0.10
    else:
        winner.approval -= 0.05
    
    winner.clamp_attributes()
    loser.clamp_attributes()


# -------------------------
# Helpers
# -------------------------
def find_country(world: List[Country], name: str) -> Country:
    """Trouve un pays par son nom (insensible à la casse)"""
    return next((c for c in world if c.name.lower() == name.lower()), None)

def ai_take_turn(country: Country, world: List[Country], alliances: List[Alliance]):
    """L'IA gère le tour d'un pays non joueur."""
    try:
        import random
        actions = ["collect_taxes", "adjust_tax", "propose_treaty", "diplomatic_mission"]
        # Retirer les actions destructives aléatoires pour éviter le chaos
        
        action = random.choice(actions)
        others = [c for c in world if c.name != country.name]
        if not others:
            return
        target = random.choice(others)
        
        if action == "collect_taxes":
            country.collect_taxes()
        elif action == "adjust_tax":
            tax_type = random.choice(["revenu", "societes", "tva", "social", "production"])
            change = random.choice([0.01, -0.01])
            country.adjust_tax(tax_type, change)
        elif action == "propose_treaty":
            rel = country.relations.get(target.name, 0)
            if country.treasury >= 30 and rel > -20:  # Seulement si relations pas trop mauvaises
                treaty_type = random.choice(["military", "trade", "science"])
                if treaty_type == "military":
                    dur, strg = 8, 25
                elif treaty_type == "trade":
                    dur, strg = 6, 15
                else:
                    dur, strg = 5, 12
                country.treasury -= 30
                target.treasury -= 15
                alliance = create_alliance(alliances, treaty_type, [country.name, target.name], duration=dur, strength=strg)
                country.set_relation(target.name, country.relations.get(target.name, 0) + strg)
                target.set_relation(country.name, target.relations.get(country.name, 0) + strg)
        elif action == "diplomatic_mission":
            if country.treasury >= 20:
                country.treasury -= 20
                rel = country.relations.get(target.name, 0)
                chance = 0.5 + (rel / 200)
                if random.random() < chance:
                    country.set_relation(target.name, country.relations.get(target.name, 0) + 10)
                    target.set_relation(country.name, target.relations.get(country.name, 0) + 10)
    except Exception as e:
        # Log silencieux pour l'IA, pour ne pas interrompre le jeu principal
        logging.warning(f"Erreur dans ai_take_turn pour {country.name}: {e}")

def ai_opposition_turn(country: Country):
    """L'IA des partis d'opposition mène des actions."""
    gov_party = next((p for p in country.political_parties if p.name == country.leader_party), None)
    if not gov_party: return

    for party in country.political_parties:
        if party.name == country.leader_party: continue

        # Les partis extrêmes sont plus agressifs
        aggressiveness = 0.1
        if "Extrême" in party.ideology:
            aggressiveness = 0.3
        
        if random.random() < aggressiveness:
            # Action simple : critiquer le gouvernement
            gov_party.support = max(0, gov_party.support - 0.002)
            party.support += 0.001
