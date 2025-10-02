# -*- coding: utf-8 -*-
# diplomacy_system.py

import random
from typing import List
from models import Country, Alliance

def create_alliance(alliances: List[Alliance], a_type: str, members: List[str], 
                   duration: int, strength: int) -> Alliance:
    """Crée une nouvelle alliance avec un nom logique"""
    new_id = max([a.id for a in alliances], default=0) + 1
    name = f"{a_type.capitalize()} - {' & '.join(members)}"
    alliance = Alliance(id=new_id, type=a_type, members=members, 
                       strength=strength, turns_left=duration, name=name)
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
    """Met à jour les relations diplomatiques."""
    for c in world:
        for other_name, val in list(c.relations.items()):
            if val > 0:
                val -= 1
            elif val < 0:
                val += 1
            val += random.randint(-1, 1)
            c.set_relation(other_name, val)
    
    for a in alliances:
        if a.active:
            for m1 in a.members:
                for m2 in a.members:
                    if m1 == m2: continue
                    c1 = next((c for c in world if c.name == m1), None)
                    if c1:
                        current = c1.relations.get(m2, 0)
                        c1.set_relation(m2, current + int(a.strength / 2))