# -*- coding: utf-8 -*-
# game_data.py

from models import Law, PoliticalParty

LAWS = [
    Law(
        id=1,
        name="Augmentation du SMIC",
        description="Augmente le pouvoir d'achat, baisse la compétitivité.",
        effect={"approval": +0.08, "gdp": -0.01, "unemployment": -0.01},
        domain="Social"
    ),
    Law(
        id=2,
        name="Réduction de l'impôt sur le revenu",
        description="Baisse l'impôt sur le revenu, augmente l'opinion, baisse les recettes.",
        effect={"tax_income": -0.03, "approval": +0.05, "treasury": -10},
        domain="Fiscalité"
    ),
    Law(
        id=3,
        name="Taxe sur les transactions financières",
        description="Augmente les recettes, baisse l'opinion.",
        effect={"tax_corporate": +0.02, "treasury": +20, "approval": -0.03},
        domain="Fiscalité"
    ),
    Law(
        id=4,
        name="Investissement public massif",
        description="Augmente le PIB, baisse le trésor, baisse le chômage.",
        effect={"gdp": +0.03, "treasury": -30, "unemployment": -0.02},
        domain="Macroéconomie"
    ),
    Law(
        id=5,
        name="Réforme du marché du travail",
        description="Baisse le chômage, baisse l'opinion.",
        effect={"unemployment": -0.02, "approval": -0.04},
        domain="Entreprise"
    ),
    Law(
        id=6,
        name="Plan de réduction de la dette",
        description="Baisse la dette, baisse la croissance.",
        effect={"debt": -100, "growth": -0.005},
        domain="Macroéconomie"
    ),
    Law(
        id=7,
        name="Soutien à l'export",
        description="Augmente les exportations, augmente le PIB.",
        effect={"exports": +30, "gdp": +0.01},
        domain="Entreprise"
    ),
    Law(
        id=8,
        name="Protectionnisme",
        description="Diminue les importations, baisse la croissance.",
        effect={"imports": -40, "growth": -0.01},
        domain="Macroéconomie"
    ),
]

FRENCH_PARTIES = [
    PoliticalParty(name="Renaissance", ideology="Centre", support=0.20, stances={"Social": 0.2, "Fiscalité": 0.1, "Macroéconomie": 0.5, "Entreprise": 0.7}),
    PoliticalParty(name="Rassemblement National", ideology="Extrême-droite", support=0.25, stances={"Social": 0.6, "Fiscalité": -0.8, "Macroéconomie": -0.5, "Entreprise": -0.6}),
    PoliticalParty(name="La France Insoumise", ideology="Extrême-gauche", support=0.18, stances={"Social": 0.9, "Fiscalité": 0.8, "Macroéconomie": 0.7, "Entreprise": -0.8}),
    PoliticalParty(name="Les Républicains", ideology="Droite", support=0.10, stances={"Social": -0.6, "Fiscalité": -0.7, "Macroéconomie": 0.2, "Entreprise": 0.8}),
    PoliticalParty(name="Parti Socialiste", ideology="Gauche", support=0.08, stances={"Social": 0.7, "Fiscalité": 0.5, "Macroéconomie": 0.4, "Entreprise": -0.5}),
    PoliticalParty(name="Les Écologistes", ideology="Écologiste", support=0.07, stances={"Social": 0.6, "Fiscalité": 0.4, "Macroéconomie": -0.2, "Entreprise": -0.4}),
    PoliticalParty(name="Autres", ideology="Divers", support=0.12, stances={"Social": 0.1, "Fiscalité": 0.0, "Macroéconomie": 0.1, "Entreprise": 0.1}),
]