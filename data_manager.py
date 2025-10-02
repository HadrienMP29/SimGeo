# -*- coding: utf-8 -*-
# data_manager.py
import json
import os
from datetime import date
import random
from typing import List, Optional, TYPE_CHECKING
from models import Country
from game_data import FRENCH_PARTIES

if TYPE_CHECKING:
    from game_engine import Game # Pour la résolution des types

SAVES_DIR = "saves"


def ensure_saves_dir():
    if not os.path.exists(SAVES_DIR):
        os.makedirs(SAVES_DIR)


def get_save_path(save_name: str) -> str:
    ensure_saves_dir()
    return os.path.join(SAVES_DIR, f"{save_name}.json")


def list_saves() -> List[str]:
    """Liste les noms de sauvegardes disponibles"""
    ensure_saves_dir()
    return [f[:-5] for f in os.listdir(SAVES_DIR) if f.endswith(".json")]


def create_world() -> List[Country]:
    """Crée le monde initial en chargeant les données depuis un fichier JSON."""
    try:
        with open("countries_data.json", "r", encoding="utf-8") as f:
            key_countries_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("⚠️ Erreur: Fichier 'countries_data.json' introuvable ou invalide. Le monde ne sera pas créé.")
        return []

    world = []

    world = [Country(name=name, population=d["pop"], gdp=d["gdp"], approval=d["approval"], treasury=d["treasury"], unemployment=d["unemployment"], debt=d["debt"], growth=d["growth"], exports=d["exports"], imports=d["imports"]) for name, d in key_countries_data.items()]
    
    # Initialiser les partis politiques pour la France
    france_country = next((c for c in world if c.name == "France"), None)
    if france_country:
        france_country.political_parties = [p for p in FRENCH_PARTIES]

    # Initialiser les relations à 0
    # S'assurer que la France est le premier pays pour être le pays joueur
    france_idx = next((i for i, c in enumerate(world) if c.name == "France"), 0)
    world.insert(0, world.pop(france_idx))

    for c1 in world:
        for c2 in world:
            if c1.name != c2.name:
                c1.relations[c2.name] = 0

    return world


def save_game_named(save_name: str, game_state: 'Game'):
    """Sauvegarde la partie dans un fichier JSON nommé"""
    ensure_saves_dir()
    path = get_save_path(save_name)
    with open(path, "w", encoding="utf-8") as f:
        # On utilise une méthode to_dict sur l'objet Game pour la sérialisation
        json.dump(game_state.to_dict(), f, indent=2, ensure_ascii=False)
    print(f"💾 Partie sauvegardée sous le nom '{save_name}' !")


def load_game_named(save_name: str) -> Optional['Game']:
    """Charge une partie depuis un fichier JSON nommé"""
    from game_engine import Game # Import local pour éviter une dépendance circulaire
    path = get_save_path(save_name)
    if not os.path.exists(path):
        print(f"Aucune sauvegarde trouvée sous le nom '{save_name}'.")
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Game.from_dict(data)


def delete_save(save_name: str) -> bool:
    """Supprime une sauvegarde par son nom"""
    path = get_save_path(save_name)
    if os.path.exists(path):
        os.remove(path)
        print(f"Sauvegarde '{save_name}' supprimée.")
        return True
    print(f"Sauvegarde '{save_name}' introuvable.")
    return False
