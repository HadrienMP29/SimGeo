# -*- coding: utf-8 -*-
# ai_system.py

import random
import logging
from typing import List
from models import Country, Alliance
from diplomacy_system import create_alliance

def ai_take_turn(country: Country, world: List[Country], alliances: List[Alliance]):
    """L'IA gère le tour d'un pays non joueur."""
    try:
        actions = ["adjust_tax", "propose_treaty", "diplomatic_mission"]
        
        action = random.choice(actions)
        others = [c for c in world if c.name != country.name]
        if not others:
            return
        target = random.choice(others)
        
        if action == "adjust_tax":
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
        logging.warning(f"Erreur dans ai_take_turn pour {country.name}: {e}")

def ai_opposition_turn(country: Country):
    """L'IA des partis d'opposition mène des actions."""
    gov_party = next((p for p in country.political_parties if p.name == country.leader_party), None)
    if not gov_party: return

    for party in country.political_parties:
        if party.name == country.leader_party: continue

        aggressiveness = 0.1
        if "Extrême" in party.ideology:
            aggressiveness = 0.3
        
        if random.random() < aggressiveness:
            gov_party.support = max(0, gov_party.support - 0.002)
            party.support += 0.001