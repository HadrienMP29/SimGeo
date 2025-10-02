# -*- coding: utf-8 -*-
# game_engine.py
import random
from datetime import date, timedelta
from typing import List, Optional

from data_manager import create_world, save_game_named, load_game_named
from models import Country, Alliance, War, asdict

from economy_system import simulate_economy_turn, calculate_budget
from politics_system import (
    simulate_election, simulate_opposition_campaign, form_coalition, simulate_party_economy, 
)
from diplomacy_system import create_alliance, tick_alliances, update_relations
from war_system import start_war, simulate_war_turn
from event_system import trigger_event, trigger_political_event
from ai_system import ai_take_turn, ai_opposition_turn


class Game:
    """
    Cette classe centralise l'état et la logique principale du jeu.
    Elle agit comme le "moteur" du jeu, indépendamment de l'interface (console ou GUI).
    """

    def __init__(self):
        self.turn: int = 1
        self.start_date: date = date(2024, 1, 1)
        self.world: List[Country] = []
        self.alliances: List[Alliance] = []
        self.wars: List[War] = []
        self.player_country: Optional[Country] = None
        self.player_party_name: str = "Renaissance"
        self.player_is_in_power: bool = True
        self.approval_history: list = []
        self.game_state: str = "RUNNING" # "RUNNING", "COALITION_NEGOTIATION"
        self.gdp_history: list = []
        self.treasury_history: list = []
        self.inflation_history: list = []
        self.unemployment_history: list = []
        self.debt_history: list = []
        self.growth_history: list = []
        self.log_messages: List[str] = []
        self.next_election_turn: int = 260 # 5 ans * 52 semaines
        self.campaign_period: int = 26 # 26 semaines = 6 mois

    def start_new_game(self, chosen_party_name: str = "Renaissance"):
        """Initialise une nouvelle partie."""
        self.world = create_world()
        self.alliances = []
        self.wars = []
        self.start_date = date(2024, 1, 1)
        # On commence directement en période de campagne pour la première élection
        self.next_election_turn = self.campaign_period
        self.turn = 1 # Le tour 1 est donc à 26 semaines de l'élection
        self.player_country = self.world[0]  # La France est le premier pays par défaut
        self.player_country.leader_party = chosen_party_name
        self.player_party_name = chosen_party_name # On garde en mémoire le parti du joueur
        self.approval_history = [self.player_country.approval]
        self.gdp_history = [self.player_country.gdp]
        self.treasury_history = [self.player_country.treasury]
        self.inflation_history = [self.player_country.inflation]
        self.unemployment_history = [self.player_country.unemployment]
        self.debt_history = [self.player_country.debt]
        self.growth_history = [self.player_country.growth]

        # --- Mise en place politique initiale ---
        # Simule une élection pour distribuer les sièges et déterminer qui est au pouvoir.
        player_won, results_log = simulate_election(self.player_country, self.player_party_name, initial_election=True)
        self.player_is_in_power = player_won

        self.log("\n--- Début de la législature ---")
        for line in results_log: self.log(line)

        if self.player_is_in_power:
            self.log("\nVotre parti a remporté les élections ! Vous êtes à la tête du gouvernement.")
        else:
            self.log(f"\nVotre parti est dans l'opposition. Le parti '{self.player_country.leader_party}' forme le gouvernement.")

    def get_current_date(self) -> date:
        """Calcule la date actuelle en fonction du tour."""
        return self.start_date + timedelta(weeks=self.turn - 1)

    def load_game(self) -> bool:
        """Charge une partie sauvegardée."""
        # Par défaut, charge la sauvegarde la plus récente
        # Pour l'instant, on utilise un nom fixe pour la sauvegarde rapide
        return self.load_game_by_name("quick_save")

    def load_game_by_name(self, name: str) -> bool:
        """Charge une partie depuis une sauvegarde nommée."""
        loaded_data = load_game_named(name)
        if loaded_data: # loaded_data est maintenant un objet Game
            # On met à jour l'état de l'objet actuel avec les données chargées
            self.__dict__.update(loaded_data.__dict__)
            # Il faut s'assurer que player_country est bien une référence à un objet dans self.world
            self.player_country = next((c for c in self.world if c.name == "France"), None)

            self.log(f"📄 Partie '{name}' chargée.")
            return True
        return False

    def save_game(self):
        """Sauvegarde la partie actuelle."""
        # Sauvegarde rapide avec un nom par défaut
        self.save_game_by_name("quick_save")

    def save_game_by_name(self, name: str):
        """Sauvegarde la partie actuelle sous un nom donné."""
        if not self.player_country:
            self.log("❌ Impossible de sauvegarder, aucune partie en cours.")
            return
        save_game_named(name, self)
        self.log(f"💾 Partie sauvegardée sous le nom '{name}'.")

    def next_turn(self):
        """Passe au tour suivant et exécute la logique de fin de tour."""
        if not self.world:
            return
        if self.game_state == "COALITION_NEGOTIATION":
            self.log("⌛ En attente de la formation d'un gouvernement.")
            return

        # --- Début de la période de campagne ---
        if self.player_country:
            if self.next_election_turn - self.turn <= self.campaign_period:
                if not self.player_country.is_campaign_active:
                    self.log("📣 La période de campagne électorale a commencé !")
                    self.player_country.is_campaign_active = True
            else:
                self.player_country.is_campaign_active = False

        # --- Élections Présidentielles ---
        if self.turn >= self.next_election_turn:
            self.log("\n--- 🗳️ ÉLECTION PRÉSIDENTIELLE 🗳️ ---")
            player_won, results_log = simulate_election(self.player_country, self.player_party_name, initial_election=False)
            for line in results_log: self.log(line)

            # Vérifier si une coalition est nécessaire
            seats_dist = self.player_country.parliament.seats_distribution
            winner_seats = seats_dist.get(self.player_country.leader_party, 0)
            if winner_seats < self.player_country.parliament.total_seats / 2:
                self.log("\nAucun parti n'a la majorité absolue. Début des négociations de coalition...")
                self.game_state = "COALITION_NEGOTIATION"
                # Le jeu est en pause, la GUI doit ouvrir la fenêtre de négociation
            else:
                self.player_is_in_power = player_won

            if not self.player_is_in_power:
                self.log("\nVotre parti est dans l'opposition.")

            self.player_country.is_campaign_active = False # Fin de la campagne
            self.next_election_turn += 260 # Prochaine élection dans 5 ans

        # L'IA de l'opposition mène sa campagne
        if self.player_country and self.player_country.is_campaign_active:
            simulate_opposition_campaign(self.player_country)

        # L'IA des autres pays joue son tour
        for c in self.world:
            if c != self.player_country:
                ai_take_turn(c, self.world, self.alliances)
        
        # Simulation de l'économie des partis
        simulate_party_economy(self.player_country)
        ai_opposition_turn(self.player_country)

        self.log("\n=== Fin du tour ===")

        # Calcul du budget et de l'économie pour tous les pays
        for country in self.world:
            calculate_budget(country)
        simulate_economy_turn(self.world)

        # Simulation des guerres
        for war in self.wars:
            if war.status == "active":
                war_log = simulate_war_turn(war, self.world)
                self.log(f"\n--- ⚔️ Conflit : {war.attacker_leader} vs {war.defender_leader} ⚔️ ---\n{war_log}")
        self.wars = [w for w in self.wars if w.status == "active"] # Nettoyer les guerres terminées

        # Déclenchement d'événements (plus réalistes)
        if random.random() < 0.15: # 15% de chance d'événement par tour
            event_log = trigger_event(self.world, self.alliances)
            if event_log:
                self.log(f"\n--- 📰 ÉVÉNEMENT 📰 ---\n{event_log}")
        if self.player_country and random.random() < 0.05: # 5% de chance d'événement politique interne
            event_log = trigger_political_event(self.player_country)
            if event_log: self.log(f"\n--- 🏛️ VIE POLITIQUE 🏛️ ---\n{event_log}")

        # Log des alertes importantes pour le joueur
        if self.player_country:
            if self.player_country.growth < -0.001: # Entrée en récession
                self.log(f"⚠️ ALERTE : L'économie française est en récession (Croissance : {self.player_country.growth*100:.2f}%)")
            if self.player_country.inflation > 0.05: # Forte inflation
                self.log(f"🔥 ALERTE : L'inflation est élevée en France ({self.player_country.inflation*100:.2f}%)")

        # Mise à jour alliances et relations
        tick_alliances(self.alliances)
        update_relations(self.world, self.alliances)

        # Historique
        self.turn += 1
        if self.player_country:
            self.approval_history.append(self.player_country.approval)
            self.gdp_history.append(self.player_country.gdp)
            self.treasury_history.append(self.player_country.treasury)
            self.inflation_history.append(self.player_country.inflation)
            self.unemployment_history.append(self.player_country.unemployment)
            self.debt_history.append(self.player_country.debt)
            self.growth_history.append(self.player_country.growth)

    def log(self, message: str):
        """Ajoute un message au journal interne pour le tour actuel."""
        self.log_messages.append(message)

    def get_and_clear_log(self) -> List[str]:
        """Récupère les messages du journal et le vide."""
        messages = self.log_messages.copy()
        self.log_messages.clear()
        return messages

    def to_dict(self):
        """Sérialise l'état complet du jeu en dictionnaire."""
        # On utilise une copie pour ne pas modifier l'objet en place
        state = self.__dict__.copy()
        # On convertit les objets complexes en dictionnaires
        state['world'] = [c.to_dict() for c in self.world]
        state['alliances'] = [a.to_dict() for a in self.alliances]
        state['wars'] = [w.to_dict() for w in self.wars]
        state['start_date'] = self.start_date.isoformat()
        # player_country est une référence, pas besoin de le sérialiser séparément
        del state['player_country']
        return state

    @classmethod
    def from_dict(cls, data):
        """Crée un objet Game à partir d'un dictionnaire."""
        game = cls()
        game.turn = data['turn']
        game.start_date = date.fromisoformat(data['start_date'])
        game.world = [Country.from_dict(c_data) for c_data in data['world']]
        game.alliances = [Alliance.from_dict(a_data) for a_data in data['alliances']]
        game.wars = [War.from_dict(w_data) for w_data in data['wars']]
        game.player_party_name = data.get('player_party_name', 'Renaissance')
        game.player_is_in_power = data.get('player_is_in_power', True)
        # Recréer les listes d'historiques
        for history_list in ['approval_history', 'gdp_history', 'treasury_history', 'inflation_history', 'unemployment_history', 'debt_history', 'growth_history']:
            setattr(game, history_list, data.get(history_list, [])) # type: ignore
        return game

    # --- Actions du joueur ---

    # --- Actions Gouvernementales ---
    def player_adjust_taxes(self, tax_changes: dict) -> bool:
        """Le joueur ajuste plusieurs impôts en même temps."""
        if not self.player_is_in_power:
            self.log("❌ Action impossible depuis l'opposition.")
            return False
        for tax_type, change in tax_changes.items():
            if abs(change) > 0.0001:
                self.player_country.adjust_tax(tax_type, change)
        self.log("✅ Impôts mis à jour.")
        self.log(f"Nouvelle opinion publique : {self.player_country.approval*100:.1f}%")
        return True

    def player_adjust_membership_fee(self, new_fee: float) -> bool:
        """Le joueur ajuste la cotisation de son parti."""
        if not self.player_country: return False
        player_party = next((p for p in self.player_country.political_parties if p.name == self.player_party_name), None)
        if not player_party: return False

        if 0 <= new_fee <= 500:
            player_party.membership_fee = new_fee
            self.log(f"💰 La cotisation annuelle du parti a été fixée à {new_fee:.2f} €.")
            return True
        else:
            self.log("❌ Montant de cotisation invalide (doit être entre 0 et 500 €).")
            return False

    # --- Actions Diplomatiques ---
    def player_propose_treaty(self, treaty_type: str, target_country: Country) -> bool:
        """Le joueur propose un traité."""
        if not self.player_is_in_power:
            self.log("❌ Action impossible depuis l'opposition.")
            return False
        cost = 30
        if self.player_country.treasury < cost:
            self.log(f"❌ Pas assez d'argent pour un traité (coût {cost} Md€).")
            return False

        self.player_country.treasury -= cost
        target_country.treasury -= cost * 0.5

        if treaty_type == "military":
            dur, strg = 8, 25
        elif treaty_type == "trade":
            dur, strg = 6, 15
        else:  # science
            dur, strg = 5, 12

        alliance = create_alliance(self.alliances, treaty_type, [self.player_country.name, target_country.name], duration=dur, strength=strg) # type: ignore
        self.player_country.set_relation(target_country.name, self.player_country.relations.get(target_country.name, 0) + strg)
        target_country.set_relation(self.player_country.name, target_country.relations.get(self.player_country.name, 0) + strg)
        self.log(f"✍️ Traité signé (ID {alliance.id}) : {alliance.name}")
        return True

    def player_espionnage(self, target_country: Country) -> bool:
        """Le joueur lance une mission d'espionnage."""
        if not self.player_is_in_power:
            self.log("❌ Action impossible depuis l'opposition.")
            return False
        cost = 25
        if self.player_country.treasury < cost:
            self.log(f"❌ Pas assez d'argent pour l'espionnage (coût {cost} Md€).")
            return False

        self.player_country.treasury -= cost
        success = random.random() < 0.6
        if success:
            self.log(f"🕶️ Espionnage réussi ! Infos sur {target_country.name} : PIB {target_country.gdp:.1f} Md€, Opinion {target_country.approval*100:.1f}%")
        else:
            target_country.set_relation(self.player_country.name, target_country.relations.get(self.player_country.name, 0) - 20)
            self.log(f"⚠️ Espionnage découvert ! Relations avec {target_country.name} diminuées (-20).")
        return True

    def player_declare_war(self, target_country: Country):
        """Le joueur déclare la guerre."""
        if not self.player_is_in_power:
            self.log("❌ Action impossible depuis l'opposition.")
            return
        war, log_msg = start_war(self.player_country, target_country, self.world, self.alliances, self.wars)
        war.start_turn = self.turn
        self.log(log_msg)

    def player_send_diplomatic_mission(self, target_country: Country) -> bool:
        """Le joueur envoie une mission diplomatique."""
        if not self.player_is_in_power:
            self.log("❌ Action impossible depuis l'opposition.")
            return False
        cost = 20
        if self.player_country.treasury < cost:
            self.log(f"❌ Pas assez d'argent pour la mission (coût {cost} Md€).")
            return False

        self.player_country.treasury -= cost
        rel = self.player_country.relations.get(target_country.name, 0)
        chance = 0.5 + (rel / 200)

        if random.random() < chance:
            self.player_country.set_relation(target_country.name, self.player_country.relations.get(target_country.name, 0) + 10)
            target_country.set_relation(self.player_country.name, target_country.relations.get(self.player_country.name, 0) + 10)
            self.log(f"🤝 Mission réussie ! Relations améliorées avec {target_country.name} (+10).")
        else:
            self.log("Mission diplomatique échouée.")
        return True

    # --- Actions de Campagne ---
    def player_campaign_action(self, action_type: str) -> bool:
        """Le joueur effectue une action de campagne."""
        if not self.player_country or not self.player_country.is_campaign_active:
            self.log("❌ Aucune campagne électorale en cours.")
            return False

        player_party = next((p for p in self.player_country.political_parties if p.name == self.player_party_name), None)
        if not player_party: return False

        if action_type == "rally":
            cost = 2
            if player_party.funds < cost:
                self.log(f"❌ Fonds du parti insuffisants (coût : {cost} M€).")
                return False
            player_party.funds -= cost
            support_gain = random.uniform(0.005, 0.01)
            player_party.support += support_gain
            self.log(f"🎤 Meeting organisé ! Le soutien pour {player_party.name} augmente de {support_gain*100:.2f}%.")

        elif action_type == "ads":
            cost = 10
            if player_party.funds < cost:
                self.log(f"❌ Fonds du parti insuffisants (coût : {cost} M€).")
                return False
            player_party.funds -= cost
            support_gain = random.uniform(0.01, 0.03)
            player_party.support += support_gain
            self.log(f"📺 Campagne publicitaire lancée ! Le soutien pour {player_party.name} augmente de {support_gain*100:.2f}%.")

        elif action_type == "debate":
            success_chance = 0.4 + self.player_country.approval * 0.5
            if random.random() < success_chance:
                support_gain = random.uniform(0.02, 0.05)
                player_party.support += support_gain
                self.log(f"💬 Débat télévisé réussi ! Le soutien pour {player_party.name} augmente de {support_gain*100:.2f}%.")
            else:
                support_loss = random.uniform(0.01, 0.03)
                player_party.support -= support_loss
                self.log(f"🤯 Débat télévisé raté ! Le soutien pour {player_party.name} diminue de {support_loss*100:.2f}%.")
        
        return True

    # --- Actions d'Opposition ---
    def player_opposition_action(self, action_type: str) -> bool:
        """Le joueur effectue une action en tant qu'opposition."""
        if self.player_is_in_power or not self.player_country:
            self.log("❌ Cette action n'est disponible que pour l'opposition.")
            return False

        player_party = next((p for p in self.player_country.political_parties if p.name == self.player_party_name), None)
        gov_party = next((p for p in self.player_country.political_parties if p.name == self.player_country.leader_party), None)
        if not player_party or not gov_party:
            return False

        if action_type == "criticize":
            # Action médiatique, faible coût, faible impact
            gov_party.support = max(0, gov_party.support - 0.005)
            player_party.support += 0.002
            self.log(f"🎤 Vous avez critiqué le gouvernement dans les médias. Leur soutien baisse légèrement.")
            return True

        elif action_type == "protest":
            cost = 5
            if player_party.funds < cost:
                self.log(f"❌ Fonds du parti insuffisants pour organiser une manifestation (coût : {cost} M€).")
                return False
            player_party.funds -= cost
            
            # Le succès dépend du soutien du parti et de l'impopularité du gouvernement
            success_chance = player_party.support + (0.5 - self.player_country.approval)
            if random.random() < success_chance:
                approval_loss = random.uniform(0.02, 0.05)
                self.player_country.approval -= approval_loss
                self.log(f"✊ Manifestation réussie ! La popularité du gouvernement chute de {approval_loss*100:.1f}%.")
            else:
                self.log("Le mouvement de protestation a eu peu d'impact.")
            return True
        
        elif action_type == "filibuster":
            # Tente de bloquer une loi. Le succès dépend du poids parlementaire.
            player_seats = self.player_country.parliament.seats_distribution.get(self.player_party_name, 0)
            if random.random() < (player_seats / self.player_country.parliament.total_seats) * 0.5:
                self.log("🏛️ Obstruction parlementaire réussie ! L'agenda législatif du gouvernement est ralenti.")
            else:
                self.log("L'obstruction parlementaire a échoué.")
            return True

        return False

    def player_propose_censure(self) -> bool:
        """Le joueur, en opposition, propose une motion de censure."""
        if self.player_is_in_power or not self.player_country:
            self.log("❌ Action réservée à l'opposition.")
            return False
        
        player_party = next((p for p in self.player_country.political_parties if p.name == self.player_party_name), None)
        if not player_party or player_party.funds < 10:
            self.log("❌ Fonds du parti insuffisants (coût : 10M€).")
            return False
        
        player_party.funds -= 10
        # Logique simplifiée du succès
        if random.random() < (1 - self.player_country.approval) * 0.3:
            self.log("🔥 Motion de censure adoptée ! Des élections anticipées auront lieu dans 13 semaines.")
            self.next_election_turn = self.turn + 13
        else:
            self.log("La motion de censure a été rejetée.")
            player_party.credibility *= 0.95
        return True

    def player_attempt_coalition(self, partner_names: List[str]) -> bool:
        """Le joueur tente de former une coalition avec les partenaires choisis."""
        if self.game_state != "COALITION_NEGOTIATION" or not self.player_country:
            return False

        player_party = next((p for p in self.player_country.political_parties if p.name == self.player_party_name), None)
        if not player_party: return False

        # Vérifier l'acceptation des partenaires
        for partner_name in partner_names:
            partner_party = next((p for p in self.player_country.political_parties if p.name == partner_name), None)
            if not partner_party: continue

            # Calcul de la compatibilité idéologique
            compatibility = sum(player_party.stances.get(k, 0) * partner_party.stances.get(k, 0) for k in player_party.stances)
            if compatibility < 0: # Alliance contre-nature
                self.log(f"❌ Négociations échouées : '{partner_name}' refuse de s'allier avec vous en raison de divergences idéologiques trop importantes.")
                self.player_concede_power() # Échec, le joueur passe dans l'opposition
                return False

        self.log("✅ Négociations réussies ! Une coalition a été formée.")
        self.player_is_in_power = True
        self.game_state = "RUNNING"
        return True

    def player_concede_power(self):
        """Le joueur renonce à former un gouvernement et passe dans l'opposition."""
        if self.game_state != "COALITION_NEGOTIATION" or not self.player_country:
            return
        _, coal_log = form_coalition(self.player_country, self.player_party_name, player_conceded=True)
        self.log(coal_log)
        self.player_is_in_power = False
        self.game_state = "RUNNING"
