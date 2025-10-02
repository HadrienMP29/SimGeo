# -*- coding: utf-8 -*-
# war_system.py

import random
from typing import List, Tuple
from models import Country, Alliance, War

def find_country(world: List[Country], name: str) -> Country:
    """Trouve un pays par son nom (insensible à la casse)"""
    return next((c for c in world if c.name.lower() == name.lower()), None)

def start_war(attacker: Country, defender: Country, world: List[Country], alliances: List[Alliance], wars: List[War]) -> Tuple[War, str]:
    """Déclenche une nouvelle guerre entre deux pays."""
    attacker.at_war_with.append(defender.name)
    defender.at_war_with.append(attacker.name)

    attacker_allies = [m for a in alliances if a.type == "military" and a.active and attacker.name in a.members for m in a.members if m != attacker.name]
    defender_allies = [m for a in alliances if a.type == "military" and a.active and defender.name in a.members for m in a.members if m != defender.name]

    new_war_id = max([w.id for w in wars], default=0) + 1
    war = War(
        id=new_war_id,
        attacker_leader=attacker.name,
        defender_leader=defender.name,
        start_turn=0,
        attacker_allies=list(set(attacker_allies)),
        defender_allies=list(set(defender_allies))
    )
    wars.append(war)

    attacker.approval -= 0.10
    defender.approval += 0.05

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
    attacker_camp = [find_country(world, name) for name in [war.attacker_leader] + war.attacker_allies]
    defender_camp = [find_country(world, name) for name in [war.defender_leader] + war.defender_allies]
    
    attacker_power = sum(c.military_power for c in attacker_camp if c)
    defender_power = sum(c.military_power for c in defender_camp if c)

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

    for camp in [attacker_camp, defender_camp]:
        for country in camp:
            if not country: continue
            country.gdp *= (1 - random.uniform(0.005, 0.02) * war.intensity)
            country.treasury -= random.uniform(5, 20) * war.intensity
            country.unemployment += random.uniform(0.005, 0.01) * war.intensity
            country.approval -= random.uniform(0.01, 0.03) * war.intensity
            country.war_weariness += 0.02
            country.clamp_attributes()

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
        resolve_war(war, world, winner=defender_leader, loser=defender_leader)
        return f"Victoire militaire décisive pour {defender_leader.name} !"

    return narrative

def resolve_war(war: War, world: List[Country], winner: Country, loser: Country):
    """Gère la fin d'une guerre."""
    war.status = "finished"
    
    for country in world:
        country.at_war_with = []
        country.war_weariness = 0

    reparations = loser.gdp * random.uniform(0.1, 0.3)
    loser.treasury -= reparations
    winner.treasury += reparations

    loser.approval -= 0.20
    loser.debt += loser.gdp * 0.20
    loser.unemployment += 0.05
    
    winner.approval += 0.10
    
    winner.clamp_attributes()
    loser.clamp_attributes()