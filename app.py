import streamlit as st
import pandas as pd
import json
import os

# Configuration de la page
st.set_page_config(page_title="Prono Cousins - CDM 2026", page_icon="⚽", layout="wide")

# Style CSS pour rendre l'application jolie sur mobile et PC
st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: bold; text-align: center; color: #1E3A8A; margin-bottom: 20px; }
    .match-box { border: 1px solid #E5E7EB; border-radius: 10px; padding: 15px; background-color: #F9FAFB; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .team-name { font-weight: bold; font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-title'>⚽ Pronos des Cousins - Coupe du Monde 2026</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# CONSTANTES & CONFIGURATION DU TOURNOI (À modifier par l'organisateur)
# -----------------------------------------------------------------------------
# Liste des matchs disponibles pour les pronostics
MATCHS = [
    {"id": "M1", "date": "Jour 1", "equipe1": "France", "equipe2": "Paraguay"},
    {"id": "M2", "date": "Jour 1", "equipe1": "Maroc", "equipe2": "Canada"},
    {"id": "M3", "date": "Jour 1", "equipe1": "Brésil", "equipe2": "Norvège"},
    {"id": "M4", "date": "Jour 2", "equipe1": "Espagne", "equipe2": "Japon"},
    {"id": "M5", "date": "Jour 2", "equipe1": "Argentine", "equipe2": "Sénégal"}
]

# Les scores réels des matchs (Remplir au fur et à mesure que les matchs se terminent)
# Si un match n'a pas encore eu lieu, ne pas le mettre ou laisser None. Exemple :
RESULTATS_REELS = {
    "M1": {"score1": 3, "score2": 0},  # France 3 - 0 Paraguay
    "M2": {"score1": 1, "score2": 1},  # Maroc 1 - 1 Canada
    "M3": {"score1": 2, "score2": 1},  # Brésil 2 - 1 Norvège
    # "M4": {"score1": 0, "score2": 2}, # Exemple futur
}

BARÈME = {
    "EXACT": 5,   # Bon score exact (ex: prono 2-1, réel 2-1)
    "VAINQUEUR": 2, # Bon vainqueur ou nul mais mauvais score (ex: prono 1-0, réel 2-1)
    "PERDU": 0     # Mauvais prono
}

# -----------------------------------------------------------------------------
# GESTION DES DONNÉES (Sauvegarde dans un fichier local/serveur)
# -----------------------------------------------------------------------------
DATA_FILE = "pronostics_data.json"

def charger_pronostics():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def sauvegarder_pronostics(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Initialisation des données dans la session de l'application
if 'db' not in st.session_state:
    st.session_state.db = charger_pronostics()

# -----------------------------------------------------------------------------
# FONCTION DE CALCUL DES POINTS
# -----------------------------------------------------------------------------
def calculer_points(p1, p2, r1, r2):
    if r1 is None or r2 is None:
        return None # Match non joué
    if p1 == r1 and p2 == r2:
        return BARÈME["EXACT"]
    elif (p1 > p2 and r1 > r2) or (p1 < p2 and r1 < r2) or (p1 == p2 and r1 == r2):
        return BARÈME["VAINQUEUR"]
    return BARÈME["PERDU"]

# -----------------------------------------------------------------------------
# INTERFACE DE L'APPLICATION (ONGLETS)
# -----------------------------------------------------------------------------
onglet1, onglet2, onglet3 = st.tabs(["🎯 Saisir mes Pronos", "📊 Classements", "📋 Tous les Pronos"])

# --- ONGLET 1 : SAISIE DES PRONOSTICS ---
with onglet1:
    st.header("📝 Entre tes prédictions")
    
    nom_cousin = st.text_input("Entre ton Prénom (ou Pseudo unique) :").strip()
    
    if nom_cousin:
        # Récupérer les anciens pronos du cousin s'ils existent pour pré-remplir
        anciens_pronos = st.session_state.db.get(nom_cousin, {})
        
        # Filtrer par jour pour ne pas surcharger l'écran
        jours_disponibles = sorted(list(set([m["date"] for m in MATCHS])))
        jour_selectionne = st.selectbox("Choisis le jour de compétition :", jours_disponibles)
        
        matchs_filtres = [m for m in MATCHS if m["date"] == jour_selectionne]
        
        st.write(f"### Matchs du {jour_selectionne}")
        
        # Formulaire pour éviter de recharger la page à chaque chiffre tapé
        with st.form(key=f"form_{jour_selectionne}"):
            pronos_du_formulaire = {}
            
            for m in matchs_filtres:
                match_id = m["id"]
                # Valeurs par défaut si le cousin avait déjà voté
                deja_p1 = anciens_pronos.get(match_id, {}).get("p1", 0)
                deja_p2 = anciens_pronos.get(match_id, {}).get("p2", 0)
                
                st.markdown(f"""
                <div class='match-box'>
                    <span class='team-name'>{m['equipe1']}</span> 🆚 <span class='team-name'>{m['equipe2']}</span>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    p1 = st.number_input(f"Score {m['equipe1']}", min_value=0, max_value=20, value=int(deja_p1), key=f"p1_{match_id}")
                with col2:
                    p2 = st.number_input(f"Score {m['equipe2']}", min_value=0, max_value=20, value=int(deja_p2), key=f"p2_{match_id}")
                
                pronos_du_formulaire[match_id] = {"p1": p1, "p2": p2}
            
            bouton_valider = st.form_submit_button("💾 Enregistrer mes pronostics")
            
            if bouton_valider:
                # Mettre à jour la base de données globale
                if nom_cousin not in st.session_state.db:
                    st.session_state.db[nom_cousin] = {}
                
                for match_id, scores in pronos_du_formulaire.items():
                    st.session_state.db[nom_cousin][match_id] = scores
                
                # Sauvegarder dans le fichier
                sauvegarder_pronostics(st.session_state.db)
                st.success(f"Impeccable {nom_cousin} ! Tes pronos pour le {jour_selectionne} sont enregistrés.")
                st.rerun()
    else:
        st.info("👋 Écris ton prénom ci-dessus pour afficher et remplir les matchs.")

# --- ONGLET 2 : CLASSEMENTS ---
with onglet2:
    st.header("🏆 Tableaux des scores")
    
    if not st.session_state.db:
        st.warning("Aucun prono n'a encore été enregistré.")
    else:
        # Choix du type de classement
        jours_disponibles = sorted(list(set([m["date"] for m in MATCHS])))
        choix_classement = st.radio("Type de classement :", ["Général (Total)", "Par Jour spécifique"], horizontal=True)
        
        points_par_cousin = {}
        
        # Parcours de tous les cousins
        for cousin, pronos in st.session_state.db.items():
            total_points = 0
            
            # Parcours de tous les matchs
            for m in MATCHS:
                match_id = m["id"]
                
                # Si on filtre par jour, on ignore les matchs des autres jours
                if choix_classement == "Par Jour spécifique":
                    filtrer_jour = st.selectbox("Sélectionne le Jour :", jours_disponibles, key="select_cl_jour")
                    if m["date"] != filtrer_jour:
                        continue
                
                # Calcul si le cousin a pronostiqué ET si le match a un résultat réel
                if match_id in pronos and match_id in RESULTATS_REELS:
                    p1 = pronos[match_id]["p1"]
                    p2 = pronos[match_id]["p2"]
                    r1 = RESULTATS_REELS[match_id]["score1"]
                    r2 = RESULTATS_REELS[match_id]["score2"]
                    
                    pts = calculer_points(p1, p2, r1, r2)
                    if pts is not None:
                        total_points += pts
            
            points_par_cousin[cousin] = total_points

        # Création et affichage du tableau de classement
        if points_par_cousin:
            df = pd.DataFrame(list(points_par_cousin.items()), columns=["Cousin / Cousine", "Points"])
            df = df.sort_values(by="Points", ascending=False).reset_index(drop=True)
            df.index += 1 # Pour commencer à la position 1 au lieu de 0
            
            # Décoration du podium
            st.write("### 🥇 Le Classement Actuel")
            st.table(df)
            
            # Petit mot d'ambiance
            if len(df) > 0:
                st.balloons()
                st.success(f"Pour le moment, le boss de la famille c'est **{df.iloc[0]['Cousin / Cousine']}** ! 😎")
        else:
            st.info("En attente des résultats des premiers matchs pour afficher les points !")

# --- ONGLET 3 : TOUS LES PRONOS (Pour éviter la triche !) ---
with onglet3:
    st.header("📋 Transparence totale (Qui a mis quoi ?)")
    if st.session_state.db:
        donnees_affichage = []
        for cousin, pronos in st.session_state.db.items():
            for m in MATCHS:
                match_id = m["id"]
                if match_id in pronos:
                    p_str = f"{pronos[match_id]['p1']} - {pronos[match_id]['p2']}"
                else:
                    p_str = "Pas voté"
                
                # Résultat réel textuel
                if match_id in RESULTATS_REELS:
                    r_str = f"{RESULTATS_REELS[match_id]['score1']} - {RESULTATS_REELS[match_id]['score2']}"
                else:
                    r_str = "À venir"
                    
                donnees_affichage.append({
                    "Cousin": cousin,
                    "Jour": m["date"],
                    "Match": f"{m['equipe1']} vs {m['equipe2']}",
                    "Pronostic": p_str,
                    "Score Réel": r_str
                })
        
        df_tous = pd.DataFrame(donnees_affichage)
        st.dataframe(df_tous, use_container_width=True, hide_index=True)
    else:
        st.info("Personne n'a encore soumis de pronostics.")