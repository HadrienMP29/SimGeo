# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font
import ssl
from game_engine import Game
from data_manager import list_saves, delete_save
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from politics_system import get_available_laws, apply_law_to_country, remove_law_from_country, get_laws_by_domain, simulate_parliament_vote
from diplomacy_system import dissolve_alliance
from war_system import find_country


class GeoGameGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SimGeo")
        self.root.geometry("1050x700")
        self.root.minsize(1100, 650)

        # --- Palettes de couleurs ---
        self.LIGHT_THEME = {
            "bg": "#f0f2f5",
            "frame_bg": "#ffffff",
            "text": "#212529",
            "accent": "#34568B",
            "accent_hover": "#4A6C9E",
            "accent_text": "#ffffff",
            "border": "#dee2e6"
        }
        self.DARK_THEME = {
            "bg": "#1c1c1e",
            "frame_bg": "#2c2c2e",
            "text": "#e4e6eb",
            "accent": "#5893D4",
            "accent_hover": "#75A9E0",
            "accent_text": "#ffffff",
            "border": "#424245"
        }
        self.colors = self.LIGHT_THEME # Thème par défaut

        # --- Configuration initiale des styles ---
        style = ttk.Style(root)
        style.theme_use("clam")
        self.apply_theme()

        # --- Police par défaut ---
        default_font = font.Font(family="Segoe UI", size=11)

        # Utiliser le moteur de jeu
        self.game = Game()

        # --- Structure principale ---
        ttk.Label(root, text="Simulateur Géopolitique", font=("Segoe UI", 20, "bold"), background=self.colors["bg"], foreground=self.colors["text"]).pack(pady=(15, 5))
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(root, textvariable=self.status_var, style="Info.TLabel")
        self.status_label.pack(pady=(0, 15))
        
        # --- Notebook (système d'onglets) ---
        style.configure("TNotebook.Tab", font=("Segoe UI", 11, "bold"), padding=[10, 5])
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Création des onglets
        self.dashboard_tab = ttk.Frame(self.notebook)
        self.government_tab = ttk.Frame(self.notebook)
        self.foreign_affairs_tab = ttk.Frame(self.notebook)
        self.world_info_tab = ttk.Frame(self.notebook)
        self.campaign_tab = ttk.Frame(self.notebook)
        self.opposition_tab = ttk.Frame(self.notebook)

        # Ajout des onglets au notebook
        self.notebook.add(self.dashboard_tab, text="📊 Tableau de Bord")
        self.notebook.add(self.government_tab, text="🏛️ Gouvernement")
        self.notebook.add(self.foreign_affairs_tab, text="🌍 Affaires Étrangères")
        self.notebook.add(self.campaign_tab, text="📣 Campagne")
        self.notebook.add(self.opposition_tab, text="✊ Opposition")
        self.notebook.add(self.world_info_tab, text="📈 Infos Monde")

        # --- Contenu des onglets ---
        self.setup_campaign_tab()
        self.setup_dashboard_tab()
        self.setup_government_tab()
        self.setup_foreign_affairs_tab()
        self.setup_world_info_tab()
        self.setup_opposition_tab()

        # Lancer la première mise à jour
        self.new_game()

        # --- Menu principal ---
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        options_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Options", menu=options_menu)

        theme_menu = tk.Menu(options_menu, tearoff=0)
        options_menu.add_cascade(label="Thème", menu=theme_menu)
        theme_menu.add_command(label="Clair", command=lambda: self.set_theme("light"))
        theme_menu.add_command(label="Sombre", command=lambda: self.set_theme("dark"))

        options_menu.add_separator()
        options_menu.add_command(label="Quitter", command=self.quit_game)

    def setup_dashboard_tab(self):
        """Configure l'onglet Tableau de Bord."""
        self.dashboard_tab.columnconfigure(0, weight=1)
        self.dashboard_tab.columnconfigure(1, weight=3)
        self.dashboard_tab.rowconfigure(0, weight=1)

        # Panneau d'actions rapides
        actions_frame = ttk.LabelFrame(self.dashboard_tab, text="Actions", style="Card.TLabelframe")
        actions_frame.grid(row=0, column=0, sticky="nswe", padx=10, pady=10)
        
        ttk.Button(actions_frame, text="✨ Nouvelle partie", command=self.new_game, style="Accent.TButton").pack(fill="x", padx=8, pady=4)
        ttk.Button(actions_frame, text="💾 Sauvegarder", command=self.save_game_named, style="Text.TButton").pack(fill="x", padx=8, pady=4)
        ttk.Button(actions_frame, text="📂 Charger", command=self.load_game_named, style="Text.TButton").pack(fill="x", padx=8, pady=4)
        ttk.Button(actions_frame, text="🚪 Quitter", command=self.quit_game, style="Text.TButton").pack(fill="x", padx=8, pady=4)
        ttk.Separator(actions_frame, orient="horizontal").pack(fill="x", pady=10, padx=5)
        ttk.Button(actions_frame, text="➡️ Tour Suivant", command=self.next_turn, style="Accent.TButton").pack(fill="both", expand=True, padx=8, pady=4)

        # Journal des événements
        log_frame = ttk.LabelFrame(self.dashboard_tab, text="Journal des Événements", style="Card.TLabelframe")
        log_frame.grid(row=0, column=1, sticky="nswe", padx=10, pady=10)
        self.log_text = tk.Text(log_frame, height=15, wrap="word", font=("Consolas", 12), relief="flat", borderwidth=0, padx=10, pady=10)
        self.log_text.pack(fill="both", expand=True)

    def log(self, message):
        """Ajoute un message au journal"""
        self.log_text.insert(tk.END, f"{message}\n\n")
        self.log_text.see(tk.END)

    def update_status(self):
        """Met à jour la barre de statut et rafraîchit la diplomatie si ouverte"""
        
        if self.game.player_country:
            current_date = self.game.get_current_date().strftime("%d %B %Y")
            self.status_var.set(
                f"🗓️ {current_date} | France - PIB {self.france.gdp:.0f} Md€, "
                f"Trésor {self.france.treasury:.0f} Md€, "
                f"Opinion {self.france.approval*100:.0f}%" +
                (" | ⚔️ EN GUERRE" if self.france.at_war_with else "")
            )
            # Style pour la guerre
            if self.france.at_war_with:
                self.status_label.config(foreground="#dc3545")
            else:
                self.status_label.config(foreground=self.colors["text"])

        # Mettre à jour la visibilité du bouton de campagne
        if self.france and self.france.is_campaign_active:
            self.notebook.tab(self.campaign_tab, state="normal")
        else:
            self.notebook.tab(self.campaign_tab, state="disabled")
        
        # Gérer l'état pouvoir/opposition
        if self.game.player_is_in_power:
            self.notebook.tab(self.government_tab, state="normal")
            self.notebook.tab(self.foreign_affairs_tab, state="normal")
            self.notebook.tab(self.opposition_tab, state="disabled")
            # La campagne est accessible au pouvoir
            if self.france and self.france.is_campaign_active:
                self.notebook.tab(self.campaign_tab, state="normal")
        else:
            self.notebook.tab(self.government_tab, state="disabled")
            self.notebook.tab(self.foreign_affairs_tab, state="disabled")
            self.notebook.tab(self.opposition_tab, state="normal")

    def new_game(self):
        """Nouvelle partie"""
        # Fenêtre modale pour choisir le parti
        party_choice_window = tk.Toplevel(self.root)
        party_choice_window.title("Choisissez votre parti")
        party_choice_window.geometry("450x400")
        party_choice_window.transient(self.root)
        party_choice_window.grab_set()

        ttk.Label(party_choice_window, text="Choisissez votre parti pour commencer", font=("Segoe UI", 14, "bold")).pack(pady=10)

        # Utiliser les données de systems.py pour peupler la liste
        from game_data import FRENCH_PARTIES
        party_names = [p.name for p in FRENCH_PARTIES]
        
        listbox = tk.Listbox(party_choice_window, selectmode=tk.SINGLE, exportselection=False, font=("Segoe UI", 11))
        for name in party_names:
            listbox.insert(tk.END, name)
        listbox.pack(fill="both", expand=True, padx=20, pady=10)
        listbox.selection_set(0) # Sélectionner le premier par défaut

        description_label = ttk.Label(party_choice_window, text="", wraplength=400)
        description_label.pack(pady=5)

        def show_party_info(event=None):
            selected_indices = listbox.curselection()
            if not selected_indices: return
            party_name = listbox.get(selected_indices[0])
            party = next((p for p in FRENCH_PARTIES if p.name == party_name), None)
            if party:
                stances_text = ", ".join([f"{domain}: {stance*100:.0f}%" for domain, stance in party.stances.items()])
                description_label.config(text=f"Idéologie: {party.ideology}\nPositions: {stances_text}")

        listbox.bind("<<ListboxSelect>>", show_party_info)
        show_party_info() # Afficher les infos du premier parti

        def on_choice_made():
            selected_indices = listbox.curselection()
            chosen_party = listbox.get(selected_indices[0]) if selected_indices else "Renaissance"
            party_choice_window.destroy()
            self.game.start_new_game(chosen_party)
            for msg in self.game.get_and_clear_log(): self.log(msg)
            self.update_status()
            self.update_countries_info()

        ttk.Button(party_choice_window, text="Commencer la partie", command=on_choice_made, style="Accent.TButton").pack(pady=10)

    def load_game(self):
        """Charge une sauvegarde"""
        if self.game.load_game():
            self.log("📂 Partie chargée.")
            self.update_status()
        else:
            messagebox.showinfo("Info", "Aucune sauvegarde trouvée.")

    def save_game_named(self):
        """Fenêtre pour choisir le nom de la sauvegarde"""
        # Pour simplifier, on utilise une boîte de dialogue modale
        name = tk.simpledialog.askstring("Sauvegarder", "Nom de la sauvegarde :", parent=self.root) # type: ignore
        if name:
            if name and self.game.player_country:
                self.game.save_game_by_name(name)
                self.log(self.game.get_and_clear_log()[-1]) # Affiche le dernier message du log
            else:
                self.log("Sauvegarde annulée ou nom invalide.")

    def load_game_named(self):
        """Fenêtre pour charger une sauvegarde existante"""
        saves = list_saves()
        if not saves:
            messagebox.showinfo("Charger", "Aucune sauvegarde disponible.")
            return
        
        name = tk.simpledialog.askstring("Charger", f"Sauvegardes disponibles: {', '.join(saves)}\n\nEntrez un nom:", parent=self.root) # type: ignore
        if name and name in saves:
            if self.game.load_game_by_name(name):
                self.log(self.game.get_and_clear_log()[-1])
                self.update_status()
                self.update_countries_info()
        else:
            self.log(f"Chargement annulé ou sauvegarde '{name}' introuvable.")

    def setup_world_info_tab(self):
        """Fenêtre avec les infos de tous les pays"""
        frame = self.world_info_tab
        
        cols = ("Pays", "PIB (Md€)", "Dette (Md€)", "Chômage (%)", "Inflation (%)")
        self.country_tree = ttk.Treeview(frame, columns=cols, show='headings', style="Custom.Treeview")
        for col in cols:
            self.country_tree.heading(col, text=col, command=lambda _col=col: self.sort_treeview(_col, False))
            self.country_tree.column(col, width=150, anchor="e")
        self.country_tree.column("Pays", anchor="w")
        self.country_tree.pack(fill="both", expand=True, padx=10, pady=10)

        refresh_button = ttk.Button(frame, text="Rafraîchir les données", command=self.update_countries_info)
        refresh_button.pack(pady=5)

    def update_countries_info(self):
        """Met à jour le tableau d'informations des pays."""
        for i in self.country_tree.get_children():
            self.country_tree.delete(i)
        
        if not self.world: return

        for country in self.world:
            values = (
                country.name,
                f"{country.gdp:.0f}",
                f"{country.debt:.0f}",
                f"{country.unemployment*100:.1f}",
                f"{country.inflation*100:.2f}"
            )
            self.country_tree.insert("", "end", values=values)

    def delete_save_named(self):
        """Fenêtre pour supprimer une sauvegarde existante"""
        name = tk.simpledialog.askstring("Supprimer", f"Sauvegardes disponibles: {', '.join(list_saves())}\n\nEntrez un nom:", parent=self.root) # type: ignore
        if name:
            if delete_save(name):
                self.log(f"Sauvegarde '{name}' supprimée.")
            else:
                self.log(f"❌ Impossible de supprimer '{name}'.")

    def sort_treeview(self, col, reverse):
        """Trie le Treeview par colonne."""
        # Implémentation du tri...
        pass
    
    def setup_government_tab(self):
        """Configure l'onglet Gouvernement."""
        pane = ttk.PanedWindow(self.government_tab, orient=tk.HORIZONTAL)
        pane.pack(fill="both", expand=True)

        # Panneau de gauche avec les boutons d'action
        actions_frame = ttk.Frame(pane, width=200)
        pane.add(actions_frame, weight=1)

        # Panneau de droite pour afficher le contenu
        self.gov_content_frame = ttk.Frame(pane)
        pane.add(self.gov_content_frame, weight=4)

        # Création des boutons
        buttons = {
            "📈 Économie": self.economy_menu_ui,
            "🏛️ Politique": self.politics_menu_ui,
            "⚖️ Lois": self.laws_menu_ui,
            "💰 Impôts": self.tax_modification_ui,
            "📊 Sondage": self.conduct_poll_ui
        }
        for text, command in buttons.items():
            ttk.Button(actions_frame, text=text, command=lambda c=command: self.switch_view(self.gov_content_frame, c)).pack(fill="x", padx=10, pady=5)

    def setup_foreign_affairs_tab(self):
        """Configure l'onglet Affaires Étrangères."""
        pane = ttk.PanedWindow(self.foreign_affairs_tab, orient=tk.HORIZONTAL)
        pane.pack(fill="both", expand=True)

        # Panneau de gauche avec les boutons d'action
        actions_frame = ttk.Frame(pane, width=200)
        pane.add(actions_frame, weight=1)

        # Panneau de droite pour afficher le contenu
        self.foreign_content_frame = ttk.Frame(pane)
        pane.add(self.foreign_content_frame, weight=4)

        buttons = {
            "🌍 Relations": self.diplomacy_menu,
            "✍️ Proposer Traité": self.propose_treaty_ui,
            "❌ Rompre Traité": self.break_treaty_ui,
            "🤝 Mission Diplo.": self.send_diplomatic_mission_ui,
            "🕶️ Espionner": self.espionnage_action,
            "💥 Déclarer Guerre": self.declare_war_ui,
            "⚔️ Guerres en cours": self.wars_ui,
        }
        for text, command in buttons.items():
            ttk.Button(actions_frame, text=text, command=lambda c=command: self.switch_view(self.foreign_content_frame, c)).pack(fill="x", padx=10, pady=5)

    def wars_ui(self, parent):
        """Affiche les guerres en cours."""
        frame = ttk.LabelFrame(parent, text="⚔️ Guerres en cours", style="Card.TLabelframe")
        frame.pack(fill="both", expand=True, padx=20, pady=10)

        if not self.game.wars:
            ttk.Label(frame, text="Aucune guerre en cours dans le monde.", font=("Segoe UI", 11, "italic")).pack(pady=20)
            return

        for war in self.game.wars:
            war_frame = ttk.LabelFrame(frame, text=f"Conflit : {war.attacker_leader} vs. {war.defender_leader}", style="Card.TLabelframe")
            war_frame.pack(fill="x", padx=10, pady=10)
            
            ttk.Label(war_frame, text=f"Début : Tour {war.start_turn} | Intensité : {war.intensity*100:.0f}%").pack(anchor="w", padx=5)
            ttk.Label(war_frame, text=f"Belligérants : {war.attacker_leader} (Alliés: {', '.join(war.attacker_allies) or 'aucun'})").pack(anchor="w", padx=5)
            ttk.Label(war_frame, text=f"              vs").pack(anchor="w", padx=5)
            ttk.Label(war_frame, text=f"              {war.defender_leader} (Alliés: {', '.join(war.defender_allies) or 'aucun'})").pack(anchor="w", padx=5)

            # Bouton pour proposer la paix si le joueur est impliqué
            if self.france.name in [war.attacker_leader, war.defender_leader] + war.attacker_allies + war.defender_allies:
                def propose_peace(war_id=war.id):
                    cost = 50
                    if self.france.treasury < cost:
                        messagebox.showwarning("Fonds insuffisants", f"Il vous faut {cost} Md€ pour proposer la paix.")
                        return
                    # Logique de paix à implémenter
                    self.log(f"🕊️ Une proposition de paix a été envoyée pour le conflit (ID {war_id}).")
                    self.france.treasury -= cost
                    self.update_status()

                ttk.Button(war_frame, text="Proposer la paix (50 Md€)", command=propose_peace).pack(pady=5)

    def setup_opposition_tab(self):
        """Configure l'onglet pour les actions d'opposition."""
        # Le contenu sera dessiné par la fonction opposition_ui lorsque l'onglet est sélectionné
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        # On crée un flag pour savoir si l'UI a déjà été construite
        self._opposition_ui_built = False

    def setup_campaign_tab(self):
        """Configure l'onglet pour la campagne électorale."""
        # Le contenu sera dessiné par la fonction campaign_menu_ui lorsque l'onglet est sélectionné.
        pass

    def opposition_ui(self, parent):
        """Génère l'interface de l'onglet Opposition."""
        # Nettoyer le parent avant de redessiner
        for widget in parent.winfo_children():
            widget.destroy()
        
        # Création d'un canvas avec une scrollbar pour le contenu
        canvas = tk.Canvas(parent, bg=self.colors["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Section Vue d'ensemble ---
        overview_frame = ttk.LabelFrame(scrollable_frame, text="Vue d'ensemble", style="Card.TLabelframe")
        overview_frame.pack(fill="x", padx=20, pady=10)
        overview_frame.columnconfigure(1, weight=1)
        
        player_party = next((p for p in self.france.political_parties if p.name == self.game.player_party_name), None) if self.france else None
        if player_party:
            ttk.Label(overview_frame, text="Parti :", font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", padx=10, pady=5)
            ttk.Label(overview_frame, text=f"{player_party.name}", font=("Segoe UI", 11, "bold")).grid(row=0, column=1, sticky="w", padx=10)
            ttk.Label(overview_frame, text="Budget :", font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w", padx=10, pady=5)
            ttk.Label(overview_frame, text=f"{player_party.funds:.1f} M€", font=("Segoe UI", 11, "bold")).grid(row=1, column=1, sticky="w", padx=10)

            def create_progress_bar(parent, label, value, row):
                ttk.Label(parent, text=f"{label} :").grid(row=row, column=0, sticky="w", padx=10, pady=5)
                bar_frame = ttk.Frame(parent)
                bar_frame.grid(row=row, column=1, sticky="ew", padx=10)
                bar_frame.columnconfigure(0, weight=1)
                ttk.Progressbar(bar_frame, length=100, maximum=1, value=value).grid(row=0, column=0, sticky="ew")
                ttk.Label(parent, text=f"{value*100:.0f}%").grid(row=row, column=2, sticky="w", padx=10)

            create_progress_bar(overview_frame, "Crédibilité", player_party.credibility, 2)
            create_progress_bar(overview_frame, "Cohésion", player_party.cohesion, 3)

        # --- Section Finances du Parti ---
        finance_frame = ttk.LabelFrame(scrollable_frame, text="💰 Finances du Parti", style="Card.TLabelframe")
        finance_frame.pack(fill="x", padx=20, pady=10)

        if player_party:
            ttk.Label(finance_frame, text=f"Adhérents : {player_party.members_count}").pack(anchor="w", padx=10, pady=2)
            
            fee_frame = ttk.Frame(finance_frame)
            fee_frame.pack(fill="x", padx=10, pady=5)
            ttk.Label(fee_frame, text="Cotisation annuelle (€) :").pack(side="left")
            fee_var = tk.StringVar(value=f"{player_party.membership_fee:.2f}")
            fee_entry = ttk.Entry(fee_frame, textvariable=fee_var, width=8)
            fee_entry.pack(side="left", padx=5)

            def apply_fee():
                try:
                    new_fee = float(fee_var.get())
                    self.game.player_adjust_membership_fee(new_fee)
                    self.log(self.game.get_and_clear_log()[-1])
                except ValueError:
                    messagebox.showerror("Erreur", "Veuillez entrer un montant numérique valide.")
            ttk.Button(fee_frame, text="Appliquer", command=apply_fee).pack(side="left")

        # --- Section Stratégie ---
        strategy_frame = ttk.LabelFrame(scrollable_frame, text="Stratégie d'Opposition", style="Card.TLabelframe")
        strategy_frame.pack(fill="x", padx=20, pady=10)

        def create_opp_action_button(text, action_type, description, action_func):
            btn_frame = ttk.Frame(strategy_frame)
            btn_frame.pack(fill="x", pady=5, padx=10)
            def do_action():
                action_func()
                self.log(self.game.get_and_clear_log()[-1]) # Affiche le dernier message
                self.opposition_ui(parent) # Rafraîchit la vue
            
            ttk.Button(btn_frame, text=text, command=do_action).pack(side="left", padx=10)
            ttk.Label(btn_frame, text=description).pack(side="left")

        create_opp_action_button("Motion de Censure", "censure", "(Coût: 10M€) Tente de renverser le gouvernement.", self.game.player_propose_censure)
        create_opp_action_button("Critiquer le Gouvernement", "criticize", "Action médiatique pour éroder le soutien du gouvernement.", lambda: self.game.player_opposition_action("criticize"))
        create_opp_action_button("Organiser une Manifestation", "protest", "(Coût: 5M€) Peut fortement impacter l'opinion.", lambda: self.game.player_opposition_action("protest"))

        # --- Section Suivi des Rivaux ---
        rivals_frame = ttk.LabelFrame(scrollable_frame, text="Suivi des Rivaux (Sondages)", style="Card.TLabelframe")
        rivals_frame.pack(fill="x", padx=20, pady=10)
        rivals_frame.columnconfigure(1, weight=1)

        if self.france:
            row_num = 0
            for p in sorted(self.france.political_parties, key=lambda p: p.support, reverse=True):
                ttk.Label(rivals_frame, text=p.name).grid(row=row_num, column=0, sticky="w", padx=10, pady=2)
                ttk.Progressbar(rivals_frame, length=100, maximum=40, value=p.support*100).grid(row=row_num, column=1, sticky="ew", padx=10)
                ttk.Label(rivals_frame, text=f"{p.support*100:.1f}%").grid(row=row_num, column=2, sticky="w", padx=10)
                row_num += 1

    def on_tab_changed(self, event):
        """Appelé lorsque l'utilisateur change d'onglet."""
        selected_tab_index = self.notebook.index(self.notebook.select())
        tab_text = self.notebook.tab(selected_tab_index, "text")

        if "Opposition" in tab_text and not self.game.player_is_in_power:
             self.opposition_ui(self.opposition_tab)
        elif "Campagne" in tab_text and self.game.player_country and self.game.player_country.is_campaign_active:
             self.campaign_menu_ui(self.campaign_tab)

    def next_turn(self):
        """Passe au tour suivant"""
        if not self.world:
            return        
        self.game.next_turn()
        for msg in self.game.get_and_clear_log():
            self.log(msg)
        self.update_status()
        self.update_countries_info()
        self.check_game_state()

    def quit_game(self):
        """Quitte le jeu."""
        if messagebox.askokcancel("Quitter", "Êtes-vous sûr de vouloir quitter ?"):
            if self.france:
                pass # On pourrait afficher un graphique final ici
            self.root.quit()

    def check_game_state(self):
        """Vérifie l'état du jeu et déclenche les UI appropriées (ex: coalition)."""
        if self.game.game_state == "COALITION_NEGOTIATION":
            self.open_coalition_window()

    def open_coalition_window(self):
        """Ouvre la fenêtre de négociation de coalition."""
        coalition_window = tk.Toplevel(self.root)
        coalition_window.title("Négociations de Coalition")
        coalition_window.geometry("500x550")
        coalition_window.transient(self.root)
        coalition_window.grab_set()

        ttk.Label(coalition_window, text="Aucune majorité absolue !", font=("Segoe UI", 16, "bold")).pack(pady=10)
        ttk.Label(coalition_window, text="Vous devez former une coalition pour gouverner.", font=("Segoe UI", 11)).pack(pady=5)

        seats_frame = ttk.LabelFrame(coalition_window, text="Résultats des élections", style="Card.TLabelframe")
        seats_frame.pack(fill="x", padx=20, pady=10)

        partners_frame = ttk.LabelFrame(coalition_window, text="Choisir des partenaires", style="Card.TLabelframe")
        partners_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Afficher les sièges
        for party, seats in sorted(self.france.parliament.seats_distribution.items(), key=lambda item: item[1], reverse=True):
            ttk.Label(seats_frame, text=f"{party}: {seats} sièges").pack(anchor="w", padx=10)

        # Liste des partenaires potentiels
        partner_vars = {}
        for party in self.france.political_parties:
            if party.name != self.game.player_party_name:
                var = tk.BooleanVar()
                chk = ttk.Checkbutton(partners_frame, text=f"{party.name} ({self.france.parliament.seats_distribution.get(party.name, 0)} sièges)", variable=var)
                chk.pack(anchor="w", padx=10)
                partner_vars[party.name] = var

        # Affichage du total de la coalition
        total_seats_var = tk.StringVar(value=f"Total de la coalition : {self.france.parliament.seats_distribution.get(self.game.player_party_name, 0)} sièges")
        total_seats_label = ttk.Label(coalition_window, textvariable=total_seats_var, font=("Segoe UI", 12, "bold"))
        total_seats_label.pack(pady=10)

        def update_total_seats(*args):
            total = self.france.parliament.seats_distribution.get(self.game.player_party_name, 0)
            for name, var in partner_vars.items():
                if var.get():
                    total += self.france.parliament.seats_distribution.get(name, 0)
            
            total_seats_var.set(f"Total de la coalition : {total} sièges")
            if total >= 289:
                total_seats_label.config(foreground="green")
            else:
                total_seats_label.config(foreground="red")

        for var in partner_vars.values():
            var.trace_add("write", update_total_seats)

        def attempt_formation():
            selected_partners = [name for name, var in partner_vars.items() if var.get()]
            self.game.player_attempt_coalition(selected_partners)
            for msg in self.game.get_and_clear_log(): self.log(msg)
            self.update_status()
            coalition_window.destroy()

        def concede():
            self.game.player_concede_power()
            for msg in self.game.get_and_clear_log(): self.log(msg)
            self.update_status()
            coalition_window.destroy()

        btn_frame = ttk.Frame(coalition_window)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Tenter de former le gouvernement", command=attempt_formation, style="Accent.TButton").pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Aller dans l'opposition", command=concede).pack(side="left", padx=10)

    def switch_view(self, parent_frame, view_function):
        """Affiche une vue dans le panneau de contenu spécifié."""
        for widget in parent_frame.winfo_children():
            widget.destroy()
        view_function(parent_frame)

    def diplomacy_menu(self, parent):
        """Affiche le panneau de diplomatie."""
        frame = ttk.LabelFrame(parent, text="Relations Diplomatiques", style="Card.TLabelframe")
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        text_widget = tk.Text(frame, wrap="word", width=60, height=15, font=("Segoe UI", 11), relief="flat", background=self.colors["frame_bg"], foreground=self.colors["text"])
        text_widget.pack(padx=10, pady=10, fill="both", expand=True)

        france = self.france
        if not france:
            text_widget.insert(tk.END, "Aucune partie en cours.\n")
        else:
            text_widget.insert(tk.END, "Relations de la France :\n")
            for c in self.world:
                if c.name != france.name:
                    rel = france.relations.get(c.name, 0)
                    text_widget.insert(tk.END, f"  • {c.name}: {rel}\n")
            text_widget.insert(tk.END, "\nTraités en cours :\n")
            active_alliances = [a for a in self.alliances if a.active and self.france.name in a.members]
            if not active_alliances:
                text_widget.insert(tk.END, "  • Aucun traité actif.\n")
            else:
                for a in active_alliances:
                    status = f"({a.turns_left} tours restants)"
                    text_widget.insert(tk.END, f"  • {a.name} {status}\n")
        text_widget.config(state="disabled")

    def espionnage_action(self, parent):
        """Action d'espionnage"""
        if not self.france:
            return
        frame = ttk.LabelFrame(parent, text="🕶️ Espionner un pays", style="Card.TLabelframe")
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        ttk.Label(frame, text="Choisir le pays à espionner (coût : 25 Md€) :").pack(padx=10, pady=5)
        listbox, get_selected = self.create_filterable_list(frame, [c.name for c in self.world if c.name != self.france.name])
        def do_espionnage():
            target = get_selected()
            target_country = find_country(self.world, target)
            if not target_country:
                self.log("❌ Pays introuvable.")
                return
            
            self.game.player_espionnage(target_country)
            for msg in self.game.get_and_clear_log():
                self.log(msg)
            self.update_status()
            self.notebook.select(self.dashboard_tab) # Revenir au tableau de bord
        ttk.Button(frame, text="Lancer l'espionnage", command=do_espionnage, style="Accent.TButton").pack(pady=10)

    def declare_war_ui(self, parent):
        """Fenêtre pour déclarer la guerre à un pays"""
        if not self.france:
            return
        frame = ttk.LabelFrame(parent, text="💥 Déclarer la guerre", style="Card.TLabelframe")
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        ttk.Label(frame, text="Choisir le pays à attaquer :").pack(padx=10, pady=5)
        ttk.Label(frame, text="⚠️ Déclarer une guerre aura de graves conséquences économiques et diplomatiques.",
                  wraplength=400, font=("Segoe UI", 10, "italic")).pack(pady=5)

        listbox, get_selected = self.create_filterable_list(frame, [c.name for c in self.world if c.name != self.france.name])
        def do_declare():
            target = get_selected()
            target_country = find_country(self.world, target)
            if not target_country:
                self.log("❌ Pays introuvable.")
            else:
                self.game.player_declare_war(target_country)
                for msg in self.game.get_and_clear_log(): self.log(msg)
                self.update_status()
            self.notebook.select(self.dashboard_tab)
        ttk.Button(frame, text="Déclarer la guerre", command=do_declare, style="Accent.TButton").pack(pady=10)

    def propose_treaty_ui(self, parent):
        """Fenêtre pour proposer un traité/alliance"""
        if not self.france:
            return
        frame = ttk.LabelFrame(parent, text="✍️ Proposer un traité", style="Card.TLabelframe")
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        ttk.Label(frame, text="Type de traité (coût : 30 Md€) :").pack(padx=10, pady=5)
        combo_type = ttk.Combobox(frame, values=["military", "trade", "science"], state="readonly")
        combo_type.pack(padx=10, pady=5, fill="x")
        ttk.Label(frame, text="Choisir le pays partenaire :").pack(padx=10, pady=(10,5))
        listbox, get_selected = self.create_filterable_list(frame, [c.name for c in self.world if c.name != self.france.name])
        def do_propose():
            tt = combo_type.get()
            target = get_selected()
            target_country = find_country(self.world, target)
            if not tt or not target_country:
                self.log("❌ Type de traité ou pays invalide.")
            else:
                self.game.player_propose_treaty(tt, target_country)
                for msg in self.game.get_and_clear_log():
                    self.log(msg)
                self.update_status()
            self.notebook.select(self.dashboard_tab)
        ttk.Button(frame, text="Proposer le traité", command=do_propose, style="Accent.TButton").pack(pady=10)

    def break_treaty_ui(self, parent):
        """Fenêtre pour rompre un traité"""
        if not self.alliances:
            messagebox.showinfo("Info", "Aucun traité à rompre.")
            return
        frame = ttk.LabelFrame(parent, text="❌ Rompre un traité", style="Card.TLabelframe")
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        ttk.Label(frame, text="Sélectionner le traité à rompre :").pack(padx=10, pady=5)
        # Affichage : "ID - nom du traité"
        ids = [f"{a.id} - {a.name}" for a in self.alliances if a.active and self.france.name in a.members]
        combo = ttk.Combobox(frame, values=ids, state="readonly")
        combo.pack(padx=10, pady=10, fill="x")
        def do_break():
            val = combo.get()
            if not val:
                messagebox.showinfo("Info", "Aucun traité sélectionné.")
                return
            try:
                aid_i = int(val.split(" - ")[0])
            except Exception:
                self.log("ID de traité invalide.")
                return
            ok = dissolve_alliance(self.alliances, aid_i)
            if ok:
                self.log("Traité rompu (il sera marqué inactif).")
            else:
                self.log("Aucun traité avec cet ID.")
            self.update_status()
            self.notebook.select(self.dashboard_tab)
        ttk.Button(frame, text="Rompre le traité", command=do_break, style="Accent.TButton").pack(pady=10)

    def send_diplomatic_mission_ui(self, parent):
        """Fenêtre pour envoyer une mission diplomatique"""
        if not self.france:
            return
        frame = ttk.LabelFrame(parent, text="🤝 Mission diplomatique", style="Card.TLabelframe")
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        ttk.Label(frame, text="Choisir le pays cible (coût : 20 Md€) :").pack(padx=10, pady=5)
        listbox, get_selected = self.create_filterable_list(frame, [c.name for c in self.world if c.name != self.france.name])
        def do_mission():
            target = get_selected()
            target_country = find_country(self.world, target)
            if not target_country:
                self.log("❌ Pays introuvable.")
            else:
                self.game.player_send_diplomatic_mission(target_country)
                for msg in self.game.get_and_clear_log():
                    self.log(msg)
                self.update_status()
            self.notebook.select(self.dashboard_tab)
        ttk.Button(frame, text="Envoyer la mission", command=do_mission, style="Accent.TButton").pack(pady=10)

    def economy_menu_ui(self, parent):
        """Fenêtre affichant toutes les variables économiques du pays joueur"""
        if not self.france:
            return
        frame = ttk.LabelFrame(parent, text=f"📈 Variables Économiques - {self.france.name}", style="Card.TLabelframe")
        frame.pack(fill="both", expand=True, padx=20, pady=10)

        # --- Zone de défilement pour les graphiques ---
        canvas = tk.Canvas(frame, bg=self.colors["frame_bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Fonction pour créer un mini-graphique ---
        def create_mini_graph(parent, title, data, color, unit=""):
            graph_frame = ttk.Frame(parent, style="Card.TLabelframe")
            graph_frame.pack(fill="x", padx=10, pady=5)

            fig = Figure(figsize=(8, 2), dpi=80)
            fig.patch.set_facecolor(self.colors["frame_bg"])
            ax = fig.add_subplot(111)

            history_slice = slice(-52, None)
            plot_data = data[history_slice]

            ax.plot(plot_data, color=color, linewidth=2)
            
            # Style
            ax.set_facecolor(self.colors["frame_bg"])
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_color(self.colors["border"])
            ax.spines['left'].set_color(self.colors["border"])
            ax.tick_params(axis='x', colors=self.colors["text"], bottom=False, labelbottom=False)
            ax.tick_params(axis='y', colors=self.colors["text"], left=True, labelleft=True)
            ax.set_title(f"{title}: {plot_data[-1]:.2f}{unit}", loc='left', color=self.colors["text"], fontsize=12, fontweight='bold')
            
            fig.tight_layout(pad=0.5)
            canvas_widget = FigureCanvasTkAgg(fig, master=graph_frame)
            canvas_widget.draw()
            canvas_widget.get_tk_widget().pack(fill="x")

        # --- Création de tous les graphiques ---
        create_mini_graph(scrollable_frame, "PIB", self.gdp_history, "#34568B", " Md€")
        create_mini_graph(scrollable_frame, "Opinion Publique", [v*100 for v in self.approval_history], "#28a745", "%")
        create_mini_graph(scrollable_frame, "Trésor", self.treasury_history, "#17a2b8", " Md€")
        create_mini_graph(scrollable_frame, "Dette Publique", self.debt_history, "#dc3545", " Md€")
        create_mini_graph(scrollable_frame, "Chômage", [v*100 for v in self.unemployment_history], "#ffc107", "%")
        create_mini_graph(scrollable_frame, "Inflation", [v*100 for v in self.inflation_history], "#fd7e14", "%")
        create_mini_graph(scrollable_frame, "Croissance", [v*100 for v in self.growth_history], "#6f42c1", "%")

    def campaign_menu_ui(self, parent):
        """Interface pour gérer la campagne électorale."""
        if not self.france:
            return
        frame = ttk.LabelFrame(parent, text="📣 Campagne Électorale", style="Card.TLabelframe")
        frame.pack(fill="both", expand=True, padx=20, pady=10)

        player_party = next((p for p in self.france.political_parties if p.name == self.game.player_party_name), None)
        if not player_party: return

        # Infos campagne
        info_frame = ttk.Frame(frame)
        info_frame.pack(fill="x", pady=10)
        turns_left = self.game.next_election_turn - self.game.turn
        ttk.Label(info_frame, text=f"Prochaine élection dans : {turns_left} semaines", font=("Segoe UI", 12, "bold")).pack()
        ttk.Label(info_frame, text=f"Fonds du parti : {player_party.funds:.1f} M€", font=("Segoe UI", 11)).pack()

        # Actions de campagne
        actions_frame = ttk.LabelFrame(frame, text="Actions de campagne", style="Card.TLabelframe")
        actions_frame.pack(fill="x", padx=10, pady=10)

        def create_action_button(text, action_type, cost_text):
            btn_frame = ttk.Frame(actions_frame)
            btn_frame.pack(fill="x", pady=4)
            def do_action():
                self.game.player_campaign_action(action_type)
                self.update_status()
                self.switch_view(parent, self.campaign_menu_ui)
            
            ttk.Button(btn_frame, text=text, command=do_action, style="Accent.TButton").pack(side="left", padx=10)
            ttk.Label(btn_frame, text=cost_text).pack(side="left")

        create_action_button("🎤 Organiser un meeting", "rally", "(Coût : 2 M€)")
        create_action_button("📺 Lancer une campagne publicitaire", "ads", "(Coût : 10 M€)")
        create_action_button("💬 Participer à un débat télévisé", "debate", "(Gratuit, risqué)")

    def laws_menu_ui(self, parent):
        """Fenêtre de gestion des lois pour la France, par domaine"""
        if not self.france:
            return
        frame = ttk.LabelFrame(parent, text="⚖️ Gestion des lois", style="Card.TLabelframe")
        frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Sélection du domaine
        domains = list(get_laws_by_domain().keys())
        ttk.Label(frame, text="Choisir un domaine de lois :", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=4)
        combo_domain = ttk.Combobox(frame, values=domains, state="readonly", font=("Segoe UI", 11))
        combo_domain.pack(fill="x", pady=6)

        laws_frame = ttk.Frame(frame)
        laws_frame.pack(fill="both", expand=True, pady=8)

        def show_laws_for_domain(event=None):
            for widget in laws_frame.winfo_children():
                widget.destroy()
            domain = combo_domain.get()
            if not domain:
                return
            laws = get_laws_by_domain()[domain]
            ttk.Label(laws_frame, text=f"Lois du domaine {domain} :", font=("Segoe UI", 12)).pack(anchor="w", pady=2)
            law_names = [f"{law.id} - {law.name}" for law in laws]
            combo_law = ttk.Combobox(laws_frame, values=law_names, state="readonly", font=("Segoe UI", 11))
            combo_law.pack(fill="x", pady=6)

            def do_apply():
                val = combo_law.get()
                if not val:
                    messagebox.showinfo("Info", "Sélectionnez une loi.")
                    return
                law_id = int(val.split(" - ")[0]) # type: ignore
                law = next((l for l in laws if l.id == law_id), None)
                if law and law not in self.france.laws:
                    if simulate_parliament_vote(self.france, law):
                        apply_law_to_country(self.france, law_id)
                        messagebox.showinfo("Vote Réussi", f"La loi '{law.name}' a été adoptée par le parlement !")
                    else:
                        messagebox.showwarning("Vote Échoué", f"La loi '{law.name}' a été rejetée par le parlement.")
                    self.notebook.select(self.dashboard_tab)
                else:
                    messagebox.showinfo("Info", "Loi déjà appliquée ou introuvable.")

            def do_remove():
                val = combo_law.get()
                if not val:
                    messagebox.showinfo("Info", "Sélectionnez une loi.")
                    return
                law_id = int(val.split(" - ")[0]) # type: ignore
                if remove_law_from_country(self.france, law_id):
                    messagebox.showinfo("Info", "Loi retirée.")
                    self.notebook.select(self.dashboard_tab)
                else:
                    messagebox.showinfo("Info", "Loi non appliquée ou introuvable.")

            btns = ttk.Frame(laws_frame)
            btns.pack(fill="x", pady=8)
            ttk.Button(btns, text="Appliquer la loi", command=do_apply).pack(side="left", padx=8)
            ttk.Button(btns, text="Retirer la loi", command=do_remove).pack(side="left", padx=8)

            # Affichage de la description de la loi sélectionnée
            def show_desc(event=None):
                val = combo_law.get()
                desc_label.config(text="")
                if val:
                    law_id = int(val.split(" - ")[0])
                    law = next((l for l in laws if l.id == law_id), None) # type: ignore
                    if law:
                        desc_label.config(text=law.description)
            desc_label = ttk.Label(laws_frame, text="", wraplength=420, font=("Segoe UI", 11))
            desc_label.pack(fill="x", pady=6)
            combo_law.bind("<<ComboboxSelected>>", show_desc)

        combo_domain.bind("<<ComboboxSelected>>", show_laws_for_domain)

        # Lois actives
        ttk.Label(frame, text="Lois actives :", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=4)
        active_text = tk.Text(frame, height=5, width=60, font=("Segoe UI", 11), bg=self.colors["frame_bg"], fg=self.colors["text"], relief="flat", borderwidth=0)
        active_text.pack(fill="x", pady=6)
        active_text.insert(tk.END, "\n".join([f"{law.name} : {law.description}" for law in self.france.laws]))
        active_text.config(state="disabled")

    def politics_menu_ui(self, parent):
        """Fenêtre affichant l'état politique du pays."""
        if not self.france:
            return
        frame = ttk.LabelFrame(parent, text="🏛️ Scène Politique Française", style="Card.TLabelframe")
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Composition du parlement
        parliament_frame = ttk.LabelFrame(frame, text="Assemblée Nationale", style="Card.TLabelframe")
        parliament_frame.pack(fill="x", pady=10)

        # Affichage visuel de l'hémicycle
        hemicycle_canvas = tk.Canvas(parliament_frame, height=20, bg=self.colors["frame_bg"], highlightthickness=0)
        hemicycle_canvas.pack(fill="x", padx=10, pady=5)
        
        party_colors = {"Centre": "#ffc107", "Droite": "#007bff", "Extrême-droite": "#343a40", "Gauche": "#dc3545", "Extrême-gauche": "#8B0000", "Écologiste": "#28a745", "Divers": "#6c757d"}
        
        total_seats = self.france.parliament.total_seats
        current_pos = 0
        for party_name, seats in sorted(self.france.parliament.seats_distribution.items(), key=lambda item: item[1], reverse=True):
            party_ideology = next((p.ideology for p in self.france.political_parties if p.name == party_name), "Divers")
            color = party_colors.get(party_ideology, "#6c757d")
            width = (seats / total_seats) * hemicycle_canvas.winfo_width() if hemicycle_canvas.winfo_width() > 1 else (seats / total_seats) * 600
            hemicycle_canvas.create_rectangle(current_pos, 0, current_pos + width, 20, fill=color, outline="")
            current_pos += width

        # Légende
        for party_name, seats in self.france.parliament.seats_distribution.items():
             ttk.Label(parliament_frame, text=f"• {party_name}: {seats} sièges").pack(anchor="w", padx=10)
        ttk.Label(parliament_frame, text=f"--- Majorité absolue : {total_seats // 2 + 1} sièges ---", font=("Segoe UI", 10, "italic")).pack(pady=5)

        # Soutien populaire
        support_frame = ttk.LabelFrame(frame, text="Soutien Populaire (Sondages)", style="Card.TLabelframe")
        support_frame.pack(fill="x", pady=10)
        for p in sorted(self.france.political_parties, key=lambda p: p.support, reverse=True):
            row = ttk.Frame(support_frame)
            row.pack(fill="x", padx=10, pady=2)
            ttk.Label(row, text=f"{p.name} ({p.ideology})", width=30).pack(side="left")
            ttk.Progressbar(row, length=300, maximum=50, value=p.support*100).pack(side="left", fill="x", expand=True)
            ttk.Label(row, text=f" {p.support*100:.1f}%").pack(side="left")

    def conduct_poll_ui(self, parent):
        """Action pour commander un sondage."""
        if not self.france:
            return
        
        cost = 5
        if self.france.treasury < cost:
            messagebox.showwarning("Fonds insuffisants", f"Vous n'avez pas assez d'argent pour commander un sondage (coût : {cost} Md€).")
            return

        self.france.treasury -= cost
        self.log(f"📊 Un sondage a été commandé pour {cost} Md€.")
        # Affiche les résultats dans une nouvelle fenêtre pour un impact plus fort
        self.politics_menu_ui(parent)
        messagebox.showinfo("Résultats du Sondage", "Les nouvelles intentions de vote sont affichées.")

    def tax_modification_ui(self, parent):
        """Fenêtre pour modifier les impôts avec des zones de texte."""
        if not self.france:
            return
        frame = ttk.LabelFrame(parent, text="💰 Modifier les impôts", style="Card.TLabelframe")
        frame.pack(fill="both", expand=True, padx=20, pady=10)
    
        initial_taxes = {
            "revenu": self.france.tax_income,
            "societes": self.france.tax_corporate,
            "tva": self.france.tax_vat,
            "social": self.france.tax_social_contributions,
            "production": self.france.tax_production,
            "patrimoine": self.france.tax_property
        }
    
        entries = {}
        for tax_type, label_text, initial_value in [
            ("revenu", "Impôt sur le revenu", initial_taxes["revenu"]),
            ("societes", "Impôt sur les sociétés", initial_taxes["societes"]),
            ("tva", "TVA", initial_taxes["tva"]),
            ("social", "Contributions Sociales", initial_taxes["social"]),
            ("production", "Impôts sur la production", initial_taxes["production"]),
            ("patrimoine", "Impôts sur le patrimoine", initial_taxes["patrimoine"])
        ]:
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=5)
            ttk.Label(row, text=f"{label_text} (%) :", width=22).pack(side="left")
            
            var = tk.StringVar(value=f"{initial_value * 100:.1f}")
            entry = ttk.Entry(row, textvariable=var, width=10, font=("Segoe UI", 11))
            entry.pack(side="left", padx=5)
            entries[tax_type] = var
    
        def do_apply():
            try:
                tax_changes = {}
                for tax_key, var in entries.items():
                    new_value_percent = float(var.get().strip())
                    # Limites différentes par impôt
                    max_tax = 80 if tax_key == "social" else 60
                    if not (0 <= new_value_percent <= max_tax):
                        raise ValueError(f"Le taux pour '{tax_key}' doit être entre 0 et {max_tax}%.")
                    
                    new_value = new_value_percent / 100.0
                    tax_changes[tax_key] = new_value - initial_taxes[tax_key]
                
                self.game.player_adjust_taxes(tax_changes)
                for msg in self.game.get_and_clear_log():
                    self.log(msg)
                self.update_status()
                self.notebook.select(self.dashboard_tab)
            except ValueError as e:
                messagebox.showerror("Erreur de saisie", f"Valeur invalide : {e}\nVeuillez entrer un nombre correct pour les impôts.")
    
        ttk.Button(frame, text="Appliquer les changements", command=do_apply, style="Accent.TButton").pack(pady=10)

    def create_filterable_list(self, parent, items):
        """Crée un champ de recherche avec une Listbox filtrable."""
        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True, padx=10, pady=5)

        search_var = tk.StringVar()
        search_entry = ttk.Entry(container, textvariable=search_var, style="TEntry")
        search_entry.pack(fill="x", pady=(0, 5))

        listbox = tk.Listbox(container, selectmode=tk.SINGLE, exportselection=False, relief="solid", borderwidth=1, bg=self.colors["frame_bg"], fg=self.colors["text"])
        listbox.pack(fill="both", expand=True)

        sorted_items = sorted(items)

        def update_listbox(event=None):
            search_term = search_var.get().lower()
            listbox.delete(0, tk.END)
            for item in sorted_items:
                if search_term in item.lower():
                    listbox.insert(tk.END, item)

        search_var.trace_add("write", update_listbox)
        update_listbox() # Initial population

        def get_selected_item():
            selected_indices = listbox.curselection()
            return listbox.get(selected_indices[0]) if selected_indices else ""

        return listbox, get_selected_item

    def set_theme(self, theme_name):
        """Change le thème de l'application (clair ou sombre)."""
        if theme_name == "dark":
            self.colors = self.DARK_THEME
        else:
            self.colors = self.LIGHT_THEME
        self.apply_theme()

    def apply_theme(self):
        """Applique la palette de couleurs actuelle à tous les widgets."""
        style = ttk.Style(self.root)
        
        # Appliquer les couleurs de base
        self.root.configure(bg=self.colors["bg"])
        
        # Styles généraux
        style.configure(".", background=self.colors["bg"], foreground=self.colors["text"])
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("TNotebook", background=self.colors["bg"])
        style.configure("TNotebook.Tab", background=self.colors["bg"], foreground=self.colors["text"])
        style.map("TNotebook.Tab", background=[("selected", self.colors["frame_bg"])])

        # Style pour les cadres "cartes"
        style.configure("Card.TLabelframe", background=self.colors["frame_bg"], borderwidth=1, relief="solid", bordercolor=self.colors["border"])
        style.configure("Card.TLabelframe.Label", font=("Segoe UI", 12, "bold"), background=self.colors["frame_bg"], foreground=self.colors["text"])

        # Style pour les boutons
        style.configure("Accent.TButton", foreground=self.colors["accent_text"], background=self.colors["accent"])
        style.map("Accent.TButton", background=[('active', self.colors["accent_hover"])])
        style.configure("Text.TButton", foreground=self.colors["text"], background=self.colors["frame_bg"])
        style.map("Text.TButton", background=[('active', self.colors["bg"])])

        # Style pour les labels d'information
        style.configure("Info.TLabel", background=self.colors["bg"], foreground=self.colors["text"])

        # Style pour le Treeview
        style.configure("Custom.Treeview", background=self.colors["frame_bg"], foreground=self.colors["text"], fieldbackground=self.colors["frame_bg"])
        style.configure("Custom.Treeview.Heading", background=self.colors["bg"], foreground=self.colors["text"], font=("Segoe UI", 11, "bold"))
        style.map("Custom.Treeview.Heading", background=[('active', self.colors["frame_bg"])])

        # Mettre à jour les widgets tk non-ttk
        for widget in self.root.winfo_children():
            if isinstance(widget, (tk.Text, tk.Listbox)):
                widget.config(bg=self.colors["frame_bg"], fg=self.colors["text"], insertbackground=self.colors["text"])
        if hasattr(self, 'log_text'): # S'assurer que le log_text est mis à jour
             self.log_text.config(bg=self.colors["frame_bg"], fg=self.colors["text"], insertbackground=self.colors["text"])
        
        # Forcer la mise à jour des graphiques si nécessaire (exemple)
        # if hasattr(self, 'gov_content_frame') and self.gov_content_frame.winfo_children():
        #     self.economy_menu_ui(self.gov_content_frame)
    @property
    def unemployment_history(self):
        return self.game.unemployment_history
    @property
    def debt_history(self):
        return self.game.debt_history
    @property
    def growth_history(self):
        return self.game.growth_history
    @property
    def france(self):
        """Accès au pays joueur"""
        return self.game.player_country

    @property
    def world(self):
        return self.game.world

    @property
    def alliances(self):
        return self.game.alliances

    @property
    def wars(self):
        return self.game.wars

    @property
    def turn(self):
        return self.game.turn

    @property
    def approval_history(self):
        return self.game.approval_history

    @property
    def gdp_history(self):
        return self.game.gdp_history

    @property
    def treasury_history(self):
        return self.game.treasury_history

    @property
    def inflation_history(self):
        return self.game.inflation_history


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = GeoGameGUI(root)
        root.mainloop()
    except Exception as e:
        import traceback
        print("Erreur lors de l'exécution de l'interface graphique :")
       
        traceback.print_exc()
        input("Appuyez sur Entrée pour quitter...")
