# -*- coding: utf-8 -*-
# models.py
from dataclasses import dataclass, asdict, field
from typing import Dict, List

@dataclass
class Alliance:
    """Représente une alliance ou traité entre pays."""
    id: int
    type: str                # "military", "trade", "science"
    members: list[str]       # noms des pays participants
    strength: int            # bonus relation apporté (ex: +20)
    turns_left: int          # durée restante
    active: bool = True
    name: str = ""           # nom logique du traité

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d):
        return Alliance(
            id=d.get("id"),
            type=d.get("type"),
            members=d.get("members"),
            strength=d.get("strength"),
            turns_left=d.get("turns_left"),
            active=d.get("active", True),
            name=d.get("name", "")
        )


@dataclass
class Law:
    """Représente une loi pouvant être appliquée à un pays."""
    id: int
    name: str
    description: str
    effect: dict  # exemple: {"gdp": +0.02, "approval": -0.05, "tax_income": +0.01}
    domain: str = "Général"  # Catégorie de la loi

    def apply(self, country: "Country"):
        for k, v in self.effect.items():
            if hasattr(country, k):
                current_value = getattr(country, k)
                setattr(country, k, current_value + v)
        country.clamp_attributes()

    def remove(self, country: "Country"):
        for k, v in self.effect.items():
            if hasattr(country, k):
                current_value = getattr(country, k)
                setattr(country, k, current_value - v)
        country.clamp_attributes()

@dataclass
class PoliticalParty:
    """Représente un parti politique avec son idéologie et son soutien."""
    name: str
    ideology: str  # ex: "Centre-gauche", "Droite", "Écologiste"
    support: float # Soutien populaire en % (0-1)
    funds: float = 10.0 # Fonds du parti en M€
    cohesion: float = 1.0 # Cohésion interne du parti (0-1)
    credibility: float = 0.7 # Crédibilité du parti (0-1)
    scandal_count: int = 0
    members_count: int = 50000 # Nombre d'adhérents
    membership_fee: float = 50.0 # Cotisation annuelle en €
    expenses: float = 0.5 # Dépenses de fonctionnement hebdomadaires en M€
    stances: Dict[str, float] = field(default_factory=dict) # ex: {"Social": 0.8, "Fiscalité": -0.5}

@dataclass
class Parliament:
    """Représente la composition du parlement."""
    total_seats: int = 577 # Assemblée Nationale
    seats_distribution: Dict[str, int] = field(default_factory=dict) # ex: {"Renaissance": 250, ...}

@dataclass
class War:
    """Représente un conflit entre deux camps."""
    id: int
    attacker_leader: str
    defender_leader: str
    start_turn: int
    attacker_allies: List[str] = field(default_factory=list)
    defender_allies: List[str] = field(default_factory=list)
    intensity: float = 0.5 # Intensité du conflit (0.1 à 1.0)
    status: str = "active" # "active" ou "finished"
    # Pour suivre la domination militaire
    attacker_dominance_turns: int = 0
    defender_dominance_turns: int = 0

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d):
        return War(**d)

@dataclass
class Country:
    """Représente un pays dans le jeu."""
    name: str
    population: int
    gdp: float
    approval: float
    treasury: float
    tax_income: float = 0.20
    tax_corporate: float = 0.25
    tax_vat: float = 0.20
    tax_social_contributions: float = 0.40 # Contributions sociales (CSG, etc.)
    tax_production: float = 0.05           # Impôts sur la production (CVAE, etc.)
    tax_property: float = 0.03             # Impôts sur le patrimoine (foncier, etc.)
    relations: Dict[str, int] = field(default_factory=dict)  # other_name -> -100..100
    espionnage_success: int = 0  # nombre de missions réussies
    laws: List[Law] = field(default_factory=list)  # Lois actives
    unemployment: float = 0.08      # Taux de chômage (0..1)
    debt: float = 2500              # Dette publique (Md€)
    growth: float = 0.015           # Croissance annuelle (ex: 0.015 = 1.5%)
    exports: float = 600            # Exportations (Md€)
    imports: float = 650            # Importations (Md€)

    # --- Variables calculées ---
    government_spending: float = 0.45 # Dépenses de l'état en % du PIB
    budget_balance: float = 0       # Solde budgétaire du dernier tour (Md€)

    # --- Nouvelles variables politiques ---
    leader_party: str = "Renaissance"
    political_parties: List[PoliticalParty] = field(default_factory=list)
    parliament: Parliament = field(default_factory=Parliament)

    # --- Nouvelles variables économiques "réalistes" ---
    inflation: float = 0.02 # Taux d'inflation annuel
    central_bank_rate: float = 0.025 # Taux directeur de la banque centrale (annuel)
    potential_growth: float = 0.012 # Croissance potentielle structurelle (annuelle)

    # --- Campagne électorale ---
    is_campaign_active: bool = False

    # --- Stabilité politique ---
    government_history: List[Dict] = field(default_factory=list) # Historique des gouvernements
    political_stability: float = 1.0 # Stabilité politique du pays (0-1)

    # --- Guerre ---
    at_war_with: List[str] = field(default_factory=list)
    war_weariness: float = 0.0 # Lassitude de guerre (0 à 1)

    @property
    def military_power(self) -> float:
        """Puissance militaire, calculée comme un pourcentage du PIB."""
        return self.gdp * 0.02


    def set_relation(self, other_name: str, value: int):
        """Fixe la relation avec un autre pays, bornée entre -100 et +100."""
        self.relations[other_name] = max(-100, min(100, value))

    def collect_taxes(self):
        """Calcule les recettes fiscales totales en se basant sur la structure du PIB."""
        # Part du PIB approximative pour chaque assiette fiscale
        consumption_base = self.gdp * 0.55
        income_base = self.gdp * 0.45
        corporate_profit_base = self.gdp * 0.12
        production_base = self.gdp # La production est le PIB lui-même
        property_base = self.gdp * 1.5 # Le patrimoine est un multiple du PIB

        revenue_vat = consumption_base * self.tax_vat
        revenue_income = income_base * self.tax_income
        revenue_social = income_base * self.tax_social_contributions # Les contributions pèsent sur les revenus
        revenue_corporate = corporate_profit_base * self.tax_corporate
        revenue_production = production_base * self.tax_production
        revenue_property = property_base * self.tax_property
        total_revenue = (revenue_vat + revenue_income + revenue_social + revenue_corporate + revenue_production + revenue_property) / 52 # Recettes hebdomadaires
        return total_revenue

    def calculate_interest_rate(self) -> float:
        """Calcule le taux d'intérêt hebdomadaire en fonction du ratio dette/PIB."""
        debt_to_gdp_ratio = self.debt / self.gdp if self.gdp > 0 else 100
        # Taux de base annuel de 2%
        base_annual_rate = 0.02
        # La prime de risque augmente avec le ratio dette/PIB
        risk_premium = max(0, (debt_to_gdp_ratio - 0.8)) * 0.02
        annual_rate = self.central_bank_rate + risk_premium
        return annual_rate / 52 # Conversion en taux hebdomadaire

    def grow_economy(self, growth_rate: float):
        self.gdp *= (1 + growth_rate)
        self.growth = growth_rate # Met à jour la variable de croissance
        return growth_rate

    def adjust_tax(self, tax_type: str, change: float):
        if tax_type == "revenu":
            self.tax_income += change
            self.approval -= change * 2
        elif tax_type == "societes":
            self.tax_corporate += change
            self.approval -= change * 1.2
        elif tax_type == "tva":
            self.tax_vat += change
            self.approval -= change * 1.5
        elif tax_type == "social":
            self.tax_social_contributions += change
            self.approval -= change * 2.5 # Très impopulaire
        elif tax_type == "production":
            self.tax_production += change
            # Moins d'impact sur l'opinion car moins visible pour le citoyen lambda
            self.approval -= change * 0.5
        elif tax_type == "patrimoine":
            self.tax_property += change
            self.approval -= change * 1.0

        self.clamp_attributes()

    def clamp_attributes(self):
        """Applique des bornes à toutes les variables critiques."""
        self.approval = max(0, min(1, self.approval))
        self.tax_income = max(0, min(0.6, self.tax_income))
        self.tax_corporate = max(0, min(0.6, self.tax_corporate))
        self.tax_vat = max(0, min(0.6, self.tax_vat))
        self.tax_social_contributions = max(0, min(0.8, self.tax_social_contributions))
        self.tax_production = max(0, min(0.2, self.tax_production))
        self.tax_property = max(0, min(0.1, self.tax_property))
        self.unemployment = max(0, min(1, self.unemployment))
        self.debt = max(0, self.debt)
        self.growth = max(-0.2, min(0.2, self.growth))
        self.exports = max(0, self.exports)
        self.imports = max(0, self.imports)

    @property
    def trade_balance(self) -> float:
        return self.exports - self.imports

    def improve_relations(self, other, cost=20, delta=15):
        if self.treasury >= cost:
            self.treasury -= cost
            self.set_relation(other.name, self.relations.get(other.name, 0) + delta)
            other.set_relation(self.name, other.relations.get(self.name, 0) + delta)
            return True
        return False

    def declare_war(self, other):
        self.set_relation(other.name, -100)
        other.set_relation(self.name, -100)

    def apply_law(self, law: Law):
        """Ajoute une loi et applique son effet."""
        if law not in self.laws:
            law.apply(self)
            self.laws.append(law)

    def remove_law(self, law: Law):
        """Retire une loi et son effet."""
        if law in self.laws:
            law.remove(self)
            self.laws.remove(law)

    def list_laws(self):
        """Retourne la liste des lois actives (noms)."""
        return [law.name for law in self.laws]

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d):
        # Chargement des lois (si présentes)
        laws_data = d.get("laws", [])
        from models import Law  # Import local pour éviter les boucles
        laws = []
        for law_dict in laws_data:
            # Si les lois sont stockées comme dicts, on les reconstruit
            if isinstance(law_dict, dict):
                laws.append(Law(
                    id=law_dict.get("id"),
                    name=law_dict.get("name"),
                    description=law_dict.get("description"),
                    effect=law_dict.get("effect", {}),
                    domain=law_dict.get("domain", "Général")
                ))
        return Country(
            name=d.get("name"),
            population=d.get("population"),
            gdp=d.get("gdp"),
            approval=d.get("approval"),
            treasury=d.get("treasury"),
            tax_income=d.get("tax_income", 0.20),
            tax_corporate=d.get("tax_corporate", 0.25),
            tax_vat=d.get("tax_vat", 0.20),
            tax_social_contributions=d.get("tax_social_contributions", 0.40),
            tax_production=d.get("tax_production", 0.05),
            tax_property=d.get("tax_property", 0.03),
            relations=d.get("relations", {}),
            espionnage_success=d.get("espionnage_success", 0),
            laws=laws,
            unemployment=d.get("unemployment", 0.08),
            debt=d.get("debt", 2500),
            growth=d.get("growth", 0.015),
            exports=d.get("exports", 600),
            imports=d.get("imports", 650),
            government_spending=d.get("government_spending", 0.45),
            budget_balance=d.get("budget_balance", 0),
            leader_party=d.get("leader_party", "Renaissance"),
            political_parties=[PoliticalParty(**p) for p in d.get("political_parties", [])],
            parliament=Parliament(**d.get("parliament", {})),
            inflation=d.get("inflation", 0.02),
            central_bank_rate=d.get("central_bank_rate", 0.025),
            potential_growth=d.get("potential_growth", 0.012),
            is_campaign_active=d.get("is_campaign_active", False),
            government_history=d.get("government_history", []),
            political_stability=d.get("political_stability", 1.0),
            at_war_with=d.get("at_war_with", []),
            war_weariness=d.get("war_weariness", 0.0)
        )
