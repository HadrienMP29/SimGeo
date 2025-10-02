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
        top_bar = ttk.Frame(root)
        top_bar.pack(fill="x", pady=(15, 5), padx=10)
        top_bar.columnconfigure(0, weight=1)

        ttk.Label(top_bar, text="Simulateur Géopolitique", font=("Segoe UI", 20, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Button(top_bar, text="Options ⚙️", command=self.open_options_menu, style="Text.TButton").grid(row=0, column=1, sticky="e")

        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(root, textvariable=self.status_var, style="Info.TLabel")
        self.status_label.pack(pady=(0, 15), fill="x", padx=10)
        
        # --- Conteneur pour le panneau de news et le contenu principal ---
        side_by_side_container = ttk.Frame(root)
        side_by_side_container.pack(fill="both", expand=True)

        # --- Panneau d'événements (initialement caché) ---
        self.news_panel = ttk.Frame(side_by_side_container, width=350, style="Card.TLabelframe")
        self.news_title_var = tk.StringVar()
        news_header = ttk.Frame(self.news_panel, style="Card.TLabelframe")
        news_header.pack(fill="x", pady=(0,5))
        ttk.Label(news_header, textvariable=self.news_title_var, font=("Segoe UI", 14, "bold")).pack(side="left", padx=10, pady=5)
        ttk.Button(news_header, text="✖", command=self.hide_news_panel, style="Text.TButton").pack(side="right", padx=5)
        self.news_text = tk.Text(self.news_panel, wrap="word", font=("Segoe UI", 11), relief="flat", borderwidth=0)
        self.news_text.pack(fill="both", expand=True, padx=10, pady=5)

        # --- Conteneur principal qui affichera la vue "pouvoir" ou "opposition" ---
        self.main_content_frame = ttk.Frame(side_by_side_container)
        self.main_content_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        # --- Panneau de contrôle (boutons communs) ---
        control_panel = ttk.Frame(root, style="Card.TLabelframe")
        control_panel.pack(side="bottom", fill="x", padx=10, pady=5)
        
        # --- Nouvelle barre de chronologie ---
        self.timeline_canvas = tk.Canvas(control_panel, height=40, bg=self.colors["frame_bg"], highlightthickness=0)
        self.timeline_canvas.pack(side="left", fill="x", expand=True, padx=10, pady=5)
        self.timeline_canvas.bind("<Button-1>", self.on_timeline_click)
        self.timeline_canvas.bind("<Configure>", lambda e: self.draw_timeline())

        ttk.Button(control_panel, text="➡️ Tour Suivant", command=self.next_turn, style="Accent.TButton").pack(side="right", fill="y", padx=8, pady=4)

        # --- Vues principales (pouvoir/opposition) ---
        self.power_view = ttk.Frame(self.main_content_frame)
        self.opposition_view = ttk.Frame(self.main_content_frame)

        # --- Données pour la timeline ---
        self.turn_events = {}

        # --- Contenu des onglets ---
        self.setup_government_tab()
        self.setup_opposition_tab()
        self.country_tree = None # Le treeview sera créé à la demande

        # Lancer la première mise à jour
        self.new_game()
        
        # Raccourci clavier pour le tour suivant
        self.root.bind("<space>", lambda event: self.next_turn())

    def log(self, message):
        """Obsolète, les messages sont maintenant gérés par tour."""
        pass

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

        # Gérer l'affichage de la vue "pouvoir" ou "opposition"
        if self.game.player_is_in_power:
            self.opposition_view.pack_forget()
            self.power_view.pack(fill="both", expand=True)
        else:
            self.power_view.pack_forget()
            self.opposition_view.pack(fill="both", expand=True)

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
            self.process_turn_logs()
            self.update_status()
            self.update_countries_info()

        ttk.Button(party_choice_window, text="Commencer la partie", command=on_choice_made, style="Accent.TButton").pack(pady=10)

    def load_game(self):
        """Charge une sauvegarde"""
        if self.game.load_game():
            self.show_events_for_turn(self.game.turn -1, ["📂 Partie chargée."])
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
                self.show_events_for_turn(self.game.turn -1, self.game.get_and_clear_log())
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
                self.process_turn_logs()
                self.update_status()
                self.update_countries_info()
        else:
            messagebox.showwarning("Erreur", f"Chargement annulé ou sauvegarde '{name}' introuvable.")

    def update_countries_info(self):
        """Met à jour le tableau d'informations des pays."""
        if self.country_tree and self.country_tree.winfo_exists():
            for i in self.country_tree.get_children():
                self.country_tree.delete(i)
        else:
            return
        
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
                messagebox.showinfo("Succès", f"Sauvegarde '{name}' supprimée.")
            else:
                messagebox.showerror("Erreur", f"Impossible de supprimer '{name}'.")

    def sort_treeview(self, col, reverse):
        """Trie le Treeview par colonne."""
        # Implémentation du tri...
        pass
    
    def open_options_menu(self):
        """Ouvre la fenêtre modale des options."""
        options_window = tk.Toplevel(self.root)
        options_window.title("Options")
        options_window.geometry("300x350")
        options_window.transient(self.root)
        options_window.grab_set()

        frame = ttk.Frame(options_window, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Button(frame, text="✨ Nouvelle partie", command=self.new_game, style="Text.TButton").pack(fill="x", pady=5)
        ttk.Button(frame, text="💾 Sauvegarder la partie", command=self.save_game_named, style="Text.TButton").pack(fill="x", pady=5)
        ttk.Button(frame, text="📂 Charger une partie", command=self.load_game_named, style="Text.TButton").pack(fill="x", pady=5)
        ttk.Button(frame, text="🗑️ Supprimer une sauvegarde", command=self.delete_save_named, style="Text.TButton").pack(fill="x", pady=5)

        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=15)

        def toggle_theme():
            if self.colors == self.LIGHT_THEME:
                self.set_theme("dark")
            else:
                self.set_theme("light")

        ttk.Button(frame, text="🌗 Changer de thème", command=toggle_theme, style="Text.TButton").pack(fill="x", pady=5)
        
        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=15)
        ttk.Button(frame, text="🚪 Quitter le jeu", command=self.quit_game, style="Accent.TButton").pack(fill="x", pady=5)

    def setup_government_tab(self):
        """Configure la vue lorsque le joueur est au pouvoir."""
        pane = ttk.PanedWindow(self.power_view, orient=tk.HORIZONTAL)
        pane.pack(fill="both", expand=True)

        actions_frame = ttk.Frame(pane, width=200)
        pane.add(actions_frame, weight=1)

        self.power_content_frame = ttk.Frame(pane)
        pane.add(self.power_content_frame, weight=4)

        categories = {
            "Économie 💰": self.economy_category_view,
            "Société 👨‍👩‍👧": self.placeholder_view, # À implémenter
            "Politique intérieure ⚖️": self.politics_category_view,
            "Défense 🪖": self.defense_category_view,
            "Diplomatie 🌍": self.diplomacy_category_view,
            "Ressources & environnement 🌱": self.placeholder_view,
            "Technologie 💡": self.placeholder_view,
            "Mon parti": self.my_party_view,
            "Infos Monde 📈": self.world_info_ui,
            "Assemblée 🏛️": self.hemicycle_view,
        }

        for text, command in categories.items():
            # On passe le texte à la commande pour savoir quoi afficher
            btn_command = lambda t=text, c=command: self.switch_view(self.power_content_frame, c, t)
            ttk.Button(actions_frame, text=text, command=btn_command).pack(fill="x", padx=10, pady=5)
        
        # Afficher la première catégorie par défaut
        self.switch_view(self.power_content_frame, self.economy_category_view, "Économie 💰")

    def setup_opposition_tab(self):
        """Configure la vue lorsque le joueur est dans l'opposition."""
        pane = ttk.PanedWindow(self.opposition_view, orient=tk.HORIZONTAL)
        pane.pack(fill="both", expand=True)

        actions_frame = ttk.Frame(pane, width=200)
        pane.add(actions_frame, weight=1)

        self.opposition_content_frame = ttk.Frame(pane)
        pane.add(self.opposition_content_frame, weight=4)

        categories = {
            "Stratégie politique": self.opposition_strategy_view,
            "Communication": self.placeholder_view, # À implémenter
            "Opinion publique": self.placeholder_view, # À implémenter
            "Influence": self.placeholder_view, # À implémenter
            "Élections": self.placeholder_view, # À implémenter
            "Mon parti": self.my_party_view,
            "Assemblée 🏛️": self.hemicycle_view,
        }

        for text, command in categories.items():
            btn_command = lambda t=text, c=command: self.switch_view(self.opposition_content_frame, c, t)
            ttk.Button(actions_frame, text=text, command=btn_command).pack(fill="x", padx=10, pady=5)
        
        # Afficher la première catégorie par défaut
        self.switch_view(self.opposition_content_frame, self.opposition_strategy_view, "Stratégie politique")

    def setup_campaign_tab(self):
        """Configure l'onglet pour la campagne électorale."""
        # Le contenu sera dessiné par la fonction campaign_menu_ui lorsque l'onglet est sélectionné.
        pass

    def opposition_ui(self, parent):
        """Obsolète, la logique est maintenant dans my_party_view et opposition_strategy_view."""
        
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
        pass # Obsolète avec la nouvelle structure

    def next_turn(self):
        """Passe au tour suivant"""
        if not self.world:
            return        
        self.game.next_turn()
        self.process_turn_logs()
        self.update_status()
        self.update_countries_info()
        self.draw_timeline()
        self.check_game_state()

    def process_turn_logs(self):
        """Récupère les logs du tour, les stocke et les affiche."""
        logs = self.game.get_and_clear_log()
        self.turn_events[self.game.turn - 1] = logs
        self.show_events_for_turn(self.game.turn - 1)

    def quit_game(self):
        """Quitte le jeu."""
        if messagebox.askokcancel("Quitter", "Êtes-vous sûr de vouloir quitter ?"):
            if self.france:
                pass # On pourrait afficher un graphique final ici
            self.root.quit()

    def check_game_state(self):
        """Vérifie l'état du jeu et déclenche les UI appropriées (ex: coalition)."""
        if self.game.game_state == "COALITION_NEGOTIATION" and self.france:
            sorted_parties = sorted(self.france.parliament.seats_distribution.items(), key=lambda item: item[1], reverse=True)
            
            if self.game.coalition_negotiator_rank < len(sorted_parties):
                negotiator_name = sorted_parties[self.game.coalition_negotiator_rank][0]
                self.game.negotiating_party_name = negotiator_name
                if negotiator_name == self.game.player_party_name:
                    self.open_coalition_window()
                else:
                    self.game.handle_ai_coalition_turn()

    def draw_timeline(self):
        """Dessine la barre de chronologie en bas."""
        canvas = self.timeline_canvas
        canvas.delete("all")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        
        if width < 2 or not hasattr(self.game, 'turn'): return

        num_weeks_to_show = 20
        week_width = width / num_weeks_to_show
        start_turn = max(0, self.game.turn - 3) # Commence un peu avant le tour actuel

        for i in range(num_weeks_to_show):
            turn = start_turn + i
            x0 = i * week_width
            x1 = (i + 1) * week_width
            
            is_current_turn = (turn == self.game.turn)
            is_past_turn = (turn < self.game.turn -1)

            color = self.colors["frame_bg"]
            outline_color = self.colors["border"]
            if is_current_turn:
                color = self.colors["accent"]
                outline_color = self.colors["accent_hover"]
            elif is_past_turn:
                color = self.colors["bg"]

            canvas.create_rectangle(x0, 2, x1, height - 2, fill=color, outline=outline_color, width=2)
            canvas.create_text(x0 + week_width/2, height/2, text=f"S{turn+1}", fill=self.colors["text"])

    def on_timeline_click(self, event):
        """Gère le clic sur la chronologie."""
        width = self.timeline_canvas.winfo_width()
        num_weeks_to_show = 20
        week_width = width / num_weeks_to_show
        start_turn = max(0, self.game.turn - 3)

        clicked_index = int(event.x // week_width)
        clicked_turn = start_turn + clicked_index

        if clicked_turn < self.game.turn -1 and clicked_turn in self.turn_events:
            self.show_events_for_turn(clicked_turn)

    def show_events_for_turn(self, turn_number, custom_logs=None):
        """Affiche les événements pour un tour donné dans une fenêtre modale."""
        logs = custom_logs if custom_logs is not None else self.turn_events.get(turn_number, [])
        if not logs:
            self.hide_news_panel()
            return

        self.news_title_var.set(f"Rapport - Semaine {turn_number + 1}")
        self.news_text.config(state="normal")
        self.news_text.delete("1.0", tk.END)
        self.news_text.insert(tk.END, "\n\n".join(logs))
        self.news_text.config(state="disabled", bg=self.colors["frame_bg"], fg=self.colors["text"])
        
        self.news_panel.pack(side="left", fill="y", padx=(10,0), pady=10)

    def hide_news_panel(self):
        """Cache le panneau des nouvelles."""
        self.news_panel.pack_forget()
        
    def placeholder_view(self, parent, title=""):
        """Vue temporaire pour les catégories non implémentées."""
        frame = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe")
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        ttk.Label(frame, text="Contenu à venir...", font=("Segoe UI", 14, "italic")).pack(pady=50)

    # --- Vues de Catégories (Pouvoir) ---

    def economy_category_view(self, parent, title):
        """Vue pour la catégorie Économie."""
        pane = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        pane.pack(fill="both", expand=True)
        actions_frame = ttk.Frame(pane, width=200)
        pane.add(actions_frame, weight=1)
        content_frame = ttk.Frame(pane)
        pane.add(content_frame, weight=4)

        buttons = {
            "Indicateurs Clés": self.economy_menu_ui,
            "Politique Fiscale": self.tax_modification_ui,
        }
        for text, command in buttons.items():
            btn_command = lambda t=text, c=command: self.switch_view(content_frame, c, t)
            ttk.Button(actions_frame, text=text, command=btn_command).pack(fill="x", padx=10, pady=5)
        
        self.switch_view(content_frame, self.economy_menu_ui, "Indicateurs Clés")

    def politics_category_view(self, parent, title):
        """Vue pour la catégorie Politique Intérieure."""
        pane = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        pane.pack(fill="both", expand=True)
        actions_frame = ttk.Frame(pane, width=200)
        pane.add(actions_frame, weight=1)
        content_frame = ttk.Frame(pane)
        pane.add(content_frame, weight=4)

        buttons = {
            "Scène Politique": self.politics_menu_ui,
            "Proposer une Loi": self.laws_menu_ui,
            "Commander un Sondage": self.conduct_poll_ui,
        }
        for text, command in buttons.items():
            btn_command = lambda t=text, c=command: self.switch_view(content_frame, c, t)
            ttk.Button(actions_frame, text=text, command=btn_command).pack(fill="x", padx=10, pady=5)
        
        self.switch_view(content_frame, self.politics_menu_ui, "Scène Politique")

    def defense_category_view(self, parent, title):
        """Vue pour la catégorie Défense."""
        pane = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        pane.pack(fill="both", expand=True)
        actions_frame = ttk.Frame(pane, width=200)
        pane.add(actions_frame, weight=1)
        content_frame = ttk.Frame(pane)
        pane.add(content_frame, weight=4)

        buttons = {
            "Guerres en cours": self.wars_ui,
            "Déclarer la Guerre": self.declare_war_ui,
        }
        for text, command in buttons.items():
            btn_command = lambda t=text, c=command: self.switch_view(content_frame, c, t)
            ttk.Button(actions_frame, text=text, command=btn_command).pack(fill="x", padx=10, pady=5)
        
        self.switch_view(content_frame, self.wars_ui, "Guerres en cours")

    def diplomacy_category_view(self, parent, title):
        """Vue pour la catégorie Diplomatie."""
        pane = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        pane.pack(fill="both", expand=True)
        actions_frame = ttk.Frame(pane, width=200)
        pane.add(actions_frame, weight=1)
        content_frame = ttk.Frame(pane)
        pane.add(content_frame, weight=4)

        buttons = {
            "Relations Diplomatiques": self.diplomacy_menu,
            "Proposer un Traité": self.propose_treaty_ui,
            "Rompre un Traité": self.break_treaty_ui,
            "Mission Diplomatique": self.send_diplomatic_mission_ui,
            "Espionnage": self.espionnage_action,
        }
        for text, command in buttons.items():
            btn_command = lambda t=text, c=command: self.switch_view(content_frame, c, t)
            ttk.Button(actions_frame, text=text, command=btn_command).pack(fill="x", padx=10, pady=5)
        
        self.switch_view(content_frame, self.diplomacy_menu, "Relations Diplomatiques")

    # --- Vues de Catégories (Communes et Opposition) ---

    def my_party_view(self, parent, title):
        """Vue pour la gestion de son propre parti."""
        for widget in parent.winfo_children():
            widget.destroy()
        
        # Création d'un canvas avec une scrollbar pour tout le contenu de "Mon Parti"
        canvas = tk.Canvas(parent, bg=self.colors["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.create_party_finance_view(scrollable_frame)

        if self.france and self.france.is_campaign_active:
            self.campaign_menu_ui(scrollable_frame, "Actions de Campagne")

    def opposition_strategy_view(self, parent, title):
        """Vue pour les actions stratégiques de l'opposition."""
        frame = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe")
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        self.create_opposition_actions(frame) # Fonction helper pour créer les boutons

    def hemicycle_view(self, parent, title=""):
        """Affiche la composition de l'Assemblée Nationale en hémicycle."""
        frame = ttk.LabelFrame(parent, text="Composition de l'Assemblée Nationale", style="Card.TLabelframe")
        frame.pack(fill="both", expand=True, padx=20, pady=10)

        if not self.france:
            ttk.Label(frame, text="Aucune donnée parlementaire disponible.").pack()
            return

        # Paned window to separate hemicycle and legend
        pane = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        pane.pack(fill="both", expand=True, pady=10)

        canvas_frame = ttk.Frame(pane)
        pane.add(canvas_frame, weight=3)
        
        legend_frame = ttk.LabelFrame(pane, text="Légende", style="Card.TLabelframe")
        pane.add(legend_frame, weight=1)

        canvas = tk.Canvas(canvas_frame, bg=self.colors["bg"], highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        party_colors = {"Centre": "#ffc107", "Droite": "#007bff", "Extrême-droite": "#343a40", "Gauche": "#dc3545", "Extrême-gauche": "#8B0000", "Écologiste": "#28a745", "Divers": "#6c757d"}
        
        total_seats = self.france.parliament.total_seats
        if total_seats == 0: return

        start_angle = 0

        # Définir l'ordre politique de gauche à droite
        ideology_order = ["Extrême-gauche", "Gauche", "Écologiste", "Centre", "Droite", "Extrême-droite", "Divers"]

        # Créer une liste de partis avec leur idéologie pour le tri
        parties_with_ideology = []
        for party_name, seats in self.france.parliament.seats_distribution.items():
            party_ideology = next((p.ideology for p in self.france.political_parties if p.name == party_name), "Divers")
            parties_with_ideology.append({'name': party_name, 'seats': seats, 'ideology': party_ideology})

        # Trier les partis selon l'ordre de l'échiquier politique
        sorted_parties_by_ideology = sorted(parties_with_ideology, key=lambda p: ideology_order.index(p['ideology']) if p['ideology'] in ideology_order else len(ideology_order))

        for party_info in reversed(sorted_parties_by_ideology):
            party_name = party_info['name']
            seats = party_info['seats']
            party_ideology = next((p.ideology for p in self.france.political_parties if p.name == party_name), "Divers")
            color = party_colors.get(party_ideology, "#6c757d")
            
            # Dessiner la légende
            legend_entry = ttk.Frame(legend_frame)
            legend_entry.pack(fill="x", padx=10, pady=3)
            ttk.Label(legend_entry, text="■", foreground=color, font=("Segoe UI", 14)).pack(side="left")
            ttk.Label(legend_entry, text=f" {party_name}: {seats}").pack(side="left", anchor="w")

            # Dessiner l'arc de l'hémicycle
            extent = (seats / total_seats) * 180
            canvas.create_arc(20, 20, 700, 700, start=start_angle, extent=extent, fill=color, outline=self.colors["border"], width=2)
            start_angle += extent

        ttk.Label(legend_frame, text=f"Majorité : {total_seats // 2 + 1} sièges", font=("Segoe UI", 10, "italic")).pack(pady=10)

    def world_info_ui(self, parent, title=""):
        """Fenêtre avec les infos de tous les pays"""
        frame = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe")
        frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Si le treeview n'existe pas ou a été détruit, on le recrée.
        if not self.country_tree or not self.country_tree.winfo_exists():
            cols = ("Pays", "PIB (Md€)", "Dette (Md€)", "Chômage (%)", "Inflation (%)")
            self.country_tree = ttk.Treeview(frame, columns=cols, show='headings', style="Custom.Treeview")
            for col in cols:
                self.country_tree.heading(col, text=col, command=lambda _col=col: self.sort_treeview(_col, False))
                self.country_tree.column(col, width=150, anchor="e")
            self.country_tree.column("Pays", anchor="w")

        self.country_tree.pack(in_=frame, fill="both", expand=True, padx=10, pady=10)
        self.update_countries_info()

    def create_party_finance_view(self, parent):
        """Crée la vue des finances et de l'état du parti."""
        player_party = next((p for p in self.france.political_parties if p.name == self.game.player_party_name), None) if self.france else None
        if not player_party: return

        # --- Section Vue d'ensemble ---
        overview_frame = ttk.LabelFrame(parent, text="État du Parti", style="Card.TLabelframe")
        overview_frame.pack(fill="x", padx=20, pady=10)
        overview_frame.columnconfigure(1, weight=1)
        
        ttk.Label(overview_frame, text="Parti :", font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        ttk.Label(overview_frame, text=f"{player_party.name}", font=("Segoe UI", 11, "bold")).grid(row=0, column=1, sticky="w", padx=10)
        ttk.Label(overview_frame, text="Fonds :", font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        ttk.Label(overview_frame, text=f"{player_party.funds:.1f} M€", font=("Segoe UI", 11, "bold")).grid(row=1, column=1, sticky="w", padx=10)

        def create_progress_bar(p, label, value, row):
            ttk.Label(p, text=f"{label} :").grid(row=row, column=0, sticky="w", padx=10, pady=5)
            bar_frame = ttk.Frame(p)
            bar_frame.grid(row=row, column=1, sticky="ew", padx=10)
            bar_frame.columnconfigure(0, weight=1)
            ttk.Progressbar(bar_frame, length=100, maximum=1, value=value).grid(row=0, column=0, sticky="ew")
            ttk.Label(p, text=f"{value*100:.0f}%").grid(row=row, column=2, sticky="w", padx=10)

        create_progress_bar(overview_frame, "Crédibilité", player_party.credibility, 2)
        create_progress_bar(overview_frame, "Cohésion", player_party.cohesion, 3)

        # --- Section Finances du Parti ---
        finance_frame = ttk.LabelFrame(parent, text="💰 Finances & Adhérents", style="Card.TLabelframe")
        finance_frame.pack(fill="x", padx=20, pady=10)

        ttk.Label(finance_frame, text=f"Adhérents : {player_party.members_count}").pack(anchor="w", padx=10, pady=2)
        fee_frame = ttk.Frame(finance_frame)
        fee_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(fee_frame, text="Cotisation annuelle (€) :").pack(side="left")
        fee_var = tk.StringVar(value=f"{player_party.membership_fee:.2f}")
        fee_entry = ttk.Entry(fee_frame, textvariable=fee_var, width=8)
        fee_entry.pack(side="left", padx=5)

        def apply_fee():
            # ... (la fonction apply_fee reste la même)
            pass
        ttk.Button(fee_frame, text="Appliquer", command=apply_fee).pack(side="left")

    def open_coalition_window(self):
        """Ouvre la fenêtre de négociation de coalition."""
        self.coalition_partner_vars = {} # Stocker les variables ici pour éviter le garbage collection
        coalition_window = tk.Toplevel(self.root)
        coalition_window.title("Négociations de Coalition")
        coalition_window.geometry("500x550")
        coalition_window.transient(self.root)
        coalition_window.grab_set()

        ttk.Label(coalition_window, text="Aucune majorité absolue !", font=("Segoe UI", 16, "bold")).pack(pady=10)
        ttk.Label(coalition_window, text=f"C'est à votre tour ({self.game.player_party_name}) de tenter de former un gouvernement.", font=("Segoe UI", 11)).pack(pady=5)

        seats_frame = ttk.LabelFrame(coalition_window, text="Résultats des élections", style="Card.TLabelframe")
        seats_frame.pack(fill="x", padx=20, pady=10)

        partners_frame = ttk.LabelFrame(coalition_window, text="Choisir des partenaires", style="Card.TLabelframe")
        partners_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Afficher les sièges
        for party, seats in sorted(self.france.parliament.seats_distribution.items(), key=lambda item: item[1], reverse=True):
            ttk.Label(seats_frame, text=f"{party}: {seats} sièges").pack(anchor="w", padx=10)

        # Liste des partenaires potentiels
        for party in self.france.political_parties:
            if party.name != self.game.player_party_name:
                var = tk.BooleanVar()
                chk = ttk.Checkbutton(partners_frame, text=f"{party.name} ({self.france.parliament.seats_distribution.get(party.name, 0)} sièges)", variable=var)
                chk.pack(anchor="w", padx=10)
                self.coalition_partner_vars[party.name] = var

        # Affichage du total de la coalition
        total_seats_var = tk.StringVar(value=f"Total de la coalition : {self.france.parliament.seats_distribution.get(self.game.player_party_name, 0)} sièges")
        total_seats_label = ttk.Label(coalition_window, textvariable=total_seats_var, font=("Segoe UI", 12, "bold"))
        total_seats_label.pack(pady=10)

        def update_total_seats(*args):
            total = self.france.parliament.seats_distribution.get(self.game.player_party_name, 0)
            for name, var in self.coalition_partner_vars.items():
                if var.get():
                    total += self.france.parliament.seats_distribution.get(name, 0)
            
            total_seats_var.set(f"Total de la coalition : {total} sièges")
            if total >= 289:
                total_seats_label.config(foreground="green")
            else:
                total_seats_label.config(foreground="red")

        for var in self.coalition_partner_vars.values():
            var.trace_add("write", update_total_seats)

        def attempt_formation():
            selected_partners = [name for name, var in self.coalition_partner_vars.items() if var.get()]
            success = self.game.player_attempt_coalition(selected_partners)
            self.process_turn_logs()
            self.update_status()
            coalition_window.destroy()

        def concede():
            self.game.player_concede_power()
            self.process_turn_logs()
            self.update_status()
            coalition_window.destroy()

        btn_frame = ttk.Frame(coalition_window)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Tenter de former le gouvernement", command=attempt_formation, style="Accent.TButton").pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Aller dans l'opposition", command=concede).pack(side="left", padx=10)

        # Cette ligne est cruciale : elle rend la fenêtre modale et attend sa fermeture.
        coalition_window.wait_window()

    def switch_view(self, parent_frame, view_function, title=""):
        """Affiche une vue dans le panneau de contenu spécifié."""
        for widget in parent_frame.winfo_children():
            widget.destroy()
        view_function(parent_frame, title)

    def create_opposition_actions(self, parent):
        """Crée les boutons d'action pour l'opposition."""
        strategy_frame = ttk.LabelFrame(parent, text="Stratégie d'Opposition", style="Card.TLabelframe")
        strategy_frame.pack(fill="x", padx=20, pady=10)

        def create_opp_action_button(text, description, action_func):
            btn_frame = ttk.Frame(strategy_frame)
            btn_frame.pack(fill="x", pady=5, padx=10)
            def do_action():
                action_func()
                self.process_turn_logs()
            ttk.Button(btn_frame, text=text, command=do_action).pack(side="left", padx=10)
            ttk.Label(btn_frame, text=description).pack(side="left")

        create_opp_action_button("Motion de Censure", "(Coût: 10M€) Tente de renverser le gouvernement.", self.game.player_propose_censure)
        create_opp_action_button("Critiquer le Gouvernement", "Action médiatique pour éroder le soutien du gouvernement.", lambda: self.game.player_opposition_action("criticize"))
        create_opp_action_button("Organiser une Manifestation", "(Coût: 5M€) Peut fortement impacter l'opinion.", lambda: self.game.player_opposition_action("protest"))

    def diplomacy_menu(self, parent, title=""):
        """Affiche le panneau de diplomatie."""
        frame = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe")
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

    def espionnage_action(self, parent, title=""):
        """Action d'espionnage"""
        if not self.france:
            return
        frame = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe")
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
            self.process_turn_logs()
            self.update_status()
            # Revenir au tableau de bord
        ttk.Button(frame, text="Lancer l'espionnage", command=do_espionnage, style="Accent.TButton").pack(pady=10)

    def declare_war_ui(self, parent, title=""):
        """Fenêtre pour déclarer la guerre à un pays"""
        if not self.france:
            return
        frame = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe")
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
                self.process_turn_logs()
            # Revenir au tableau de bord
        ttk.Button(frame, text="Déclarer la guerre", command=do_declare, style="Accent.TButton").pack(pady=10)

    def propose_treaty_ui(self, parent, title=""):
        """Fenêtre pour proposer un traité/alliance"""
        if not self.france:
            return
        frame = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe")
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
                self.process_turn_logs()
                self.update_status()
            # Revenir au tableau de bord
        ttk.Button(frame, text="Proposer le traité", command=do_propose, style="Accent.TButton").pack(pady=10)

    def break_treaty_ui(self, parent, title=""):
        """Fenêtre pour rompre un traité"""
        if not self.alliances:
            messagebox.showinfo("Info", "Aucun traité à rompre.")
            return
        frame = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe")
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
                messagebox.showinfo("Succès", "Le traité a été rompu.")
            else:
                messagebox.showerror("Erreur", "Aucun traité avec cet ID trouvé.")
            self.update_status()
        ttk.Button(frame, text="Rompre le traité", command=do_break, style="Accent.TButton").pack(pady=10)

    def send_diplomatic_mission_ui(self, parent, title=""):
        """Fenêtre pour envoyer une mission diplomatique"""
        if not self.france:
            return
        frame = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe")
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
                self.process_turn_logs()
                self.update_status()
            # Revenir au tableau de bord
        ttk.Button(frame, text="Envoyer la mission", command=do_mission, style="Accent.TButton").pack(pady=10)

    def economy_menu_ui(self, parent, title=""):
        """Fenêtre affichant toutes les variables économiques du pays joueur"""
        if not self.france:
            return
        frame = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe")
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

    def campaign_menu_ui(self, parent, title=""):
        """Interface pour gérer la campagne électorale."""
        if not self.france:
            return
        frame = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe")
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
                self.process_turn_logs()
            
            ttk.Button(btn_frame, text=text, command=do_action, style="Accent.TButton").pack(side="left", padx=10)
            ttk.Label(btn_frame, text=cost_text).pack(side="left")

        create_action_button("🎤 Organiser un meeting", "rally", "(Coût : 2 M€)")
        create_action_button("📺 Lancer une campagne publicitaire", "ads", "(Coût : 10 M€)")
        create_action_button("💬 Participer à un débat télévisé", "debate", "(Gratuit, risqué)")

    def laws_menu_ui(self, parent, title=""):
        """Fenêtre de gestion des lois pour la France, par domaine"""
        if not self.france:
            return
        frame = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe")
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
                    # Revenir au tableau de bord
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
                    # Revenir au tableau de bord
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

    def politics_menu_ui(self, parent, title=""):
        """Fenêtre affichant l'état politique du pays."""
        if not self.france:
            return
        frame = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe")
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Soutien populaire
        support_frame = ttk.LabelFrame(frame, text="Soutien Populaire (Sondages)", style="Card.TLabelframe")
        support_frame.pack(fill="x", pady=10)
        for p in sorted(self.france.political_parties, key=lambda p: p.support, reverse=True):
            row = ttk.Frame(support_frame)
            row.pack(fill="x", padx=10, pady=2)
            ttk.Label(row, text=f"{p.name} ({p.ideology})", width=30).pack(side="left")
            ttk.Progressbar(row, length=300, maximum=50, value=p.support*100).pack(side="left", fill="x", expand=True)
            ttk.Label(row, text=f" {p.support*100:.1f}%").pack(side="left")

    def conduct_poll_ui(self, parent, title=""):
        """Action pour commander un sondage."""
        if not self.france:
            return
        
        cost = 5
        if self.france.treasury < cost:
            messagebox.showwarning("Fonds insuffisants", f"Vous n'avez pas assez d'argent pour commander un sondage (coût : {cost} Md€).")
            return

        self.france.treasury -= cost
        messagebox.showinfo("Sondage", f"📊 Un sondage a été commandé pour {cost} Md€.")
        # Affiche les résultats dans une nouvelle fenêtre pour un impact plus fort
        self.politics_menu_ui(parent)
        messagebox.showinfo("Résultats du Sondage", "Les nouvelles intentions de vote sont affichées.")
        
    def tax_modification_ui(self, parent, title=""):
        """Fenêtre pour modifier les impôts avec des zones de texte."""
        if not self.france:
            return
        frame = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe")
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
                self.process_turn_logs()
                self.update_status()
                # Revenir au tableau de bord
            except ValueError as e:
                messagebox.showerror("Erreur de saisie", f"Valeur invalide : {e}\nVeuillez entrer un nombre correct pour les impôts.")
    
        ttk.Button(frame, text="Appliquer les changements", command=do_apply, style="Accent.TButton").pack(pady=10)

    def wars_ui(self, parent, title=""):
        """Affiche les guerres en cours."""
        frame = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe")
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

            if self.france.name in [war.attacker_leader, war.defender_leader] + war.attacker_allies + war.defender_allies:
                def propose_peace(war_id=war.id):
                    # Logique de paix à implémenter
                    messagebox.showinfo("Paix", f"🕊️ Une proposition de paix a été envoyée pour le conflit (ID {war_id}).")
                ttk.Button(war_frame, text="Proposer la paix (50 Md€)", command=propose_peace).pack(pady=5)

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
        
        if hasattr(self, 'news_text'): # S'assurer que le panneau de news est mis à jour
             self.news_text.config(bg=self.colors["frame_bg"], fg=self.colors["text"])
        
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
