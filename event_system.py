# -*- coding: utf-8 -*-
# event_system.py

import random
from typing import List
from models import Country, Alliance

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
        country.treasury -= country.gdp * 0.01
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
    
    target_party = random.choice(country.political_parties)
    target_party.scandal_count += 1
    target_party.support *= 0.90
    target_party.credibility *= 0.85
    return f"Un scandale de financement éclabousse le parti '{target_party.name}', qui perd en crédibilité et en soutien."