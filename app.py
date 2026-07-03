import streamlit as st
import pandas as pd
import json
import os

# Configuration de la page
st.set_page_config(page_title="Prono Cousins - CDM 2026", page_icon="⚽", layout="wide")

# Style CSS
st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: bold; text-align: center; color: #1E3A8A; margin-bottom: 20px; }
    .match-box { border: 1px solid #E5E7EB; border-radius: 10px; padding: 15px; background-color: #F9FAFB; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .team-name { font-weight: bold; font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-title'>⚽ Pronos des Cousins - Coupe du Monde 2026</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# CALENDRIER DES MATCHS
# -----------------------------------------------------------------------------
MATCHS = [
    {"id": "M92", "date": "Lundi 6 Juillet", "equipe1": "Mexique", "equipe2": "Angleterre"},
    {"id": "M93", "date": "Lundi 6 Juillet", "equipe1": "Portugal", "equipe2": "Espagne"},
    {"id": "M94", "date": "Mardi 7 Juillet", "equipe1": "Belgique", "equipe2": "États-Unis"},
    {"id": "M95", "date": "Mardi 7 Juillet", "equipe1": "Arg / Cap-Vert", "equipe2": "Aus / Égypte"},
    {"id": "M96", "date": "Mardi 7 Juillet", "equipe1": "Suisse", "equipe2": "Col / Ghana"},
    {"id": "Q1", "date": "Jeudi 9 Juillet", "equipe1": "Vainqueur Match 89", "equipe2": "Vainqueur Match 90"},
    {"id": "Q2", "date": "Vendredi 10 Juillet", "equipe1": "Vainqueur Match 91", "equipe2": "Vainqueur Match 92"}
]

BARÈME = {"EXACT": 5, "VAINQUEUR": 2, "PERDU": 0}

# -----------------------------------------------------------------------------
# GESTION DES FICHIERS DE SAUVEGARDE (PRONOS + RÉSULTATS REELS)
# -----------------------------------------------------------------------------
PRONOS_FILE = "pronostics_data.json"
REELS_FILE = "resultats_reels.json"

def charger_json(fichier):
    if os.path.exists(fichier):
        try:
            with open(fichier, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def sauvegarder_json(fichier, data):
    with open(fichier, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Enregistrement initial des données
if 'db_pronos' not in st.session_state:
    st.session_state.db_pronos = charger_json(PRONOS_FILE)
if 'db_reels' not in st.session_state:
    st.session_state.db_reels = charger_json(REELS_FILE)

def calculer_points(p1, p2, r1, r2):
    if p1 == r1 and p2 == r2:
        return BARÈME["EXACT"]
    elif (p1 > p2 and r1 > r2) or (p1 < p2 and r1 < r2) or (p1 == p2 and r1 == r2):
        return BARÈME["VAINQUEUR"]
    return BARÈME["PERDU"]

# -----------------------------------------------------------------------------
# INTERFACE DE L'APPLICATION
# -----------------------------------------------------------------------------
onglet1, onglet2, onglet3, onglet4 = st.tabs([
    "🎯 Saisir mes Pronos", 
    "📊 Classements", 
    "📋 Tous les Pronos", 
    "⚙️ Admin (Scores Réels)"
])

# --- ONGLET 1 : SAISIE DES PRONOSTICS ---
with onglet1:
    st.header("📝 Entre tes prédictions")
    nom_cousin = st.text_input("Entre ton Prénom (ou Pseudo unique) :").strip()
    
    if nom_cousin:
        anciens_pronos = st.session_state.db_pronos.get(nom_cousin, {})
        jours_ordres = ["Lundi 6 Juillet", "Mardi 7 Juillet", "Jeudi 9 Juillet", "Vendredi 10 Juillet"]
        jours_disponibles = [j for j in jours_ordres if j in [m["date"] for m in MATCHS]]
        jour_selectionne = st.selectbox("Choisis la date des matchs :", jours_disponibles, key="sb_jour_prono")
        
        matchs_filtres = [m for m in MATCHS if m["date"] == jour_selectionne]
        
        with st.form(key=f"form_{jour_selectionne}"):
            pronos_du_formulaire = {}
            for m in matchs_filtres:
                match_id = m["id"]
                deja_p1 = anciens_pronos.get(match_id, {}).get("p1", 0)
                deja_p2 = anciens_pronos.get(match_id, {}).get("p2", 0)
                
                st.markdown(f"<div class='match-box'><span class='team-name'>{m['equipe1']}</span> 🆚 <span class='team-name'>{m['equipe2']}</span></div>", unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    p1 = st.number_input(f"Score {m['equipe1']}", min_value=0, max_value=20, value=int(deja_p1), key=f"p1_{match_id}")
                with col2:
                    p2 = st.number_input(f"Score {m['equipe2']}", min_value=0, max_value=20, value=int(deja_p2), key=f"p2_{match_id}")
                
                pronos_du_formulaire[match_id] = {"p1": p1, "p2": p2}
            
            if st.form_submit_button("💾 Enregistrer mes pronostics"):
                if nom_cousin not in st.session_state.db_pronos:
                    st.session_state.db_pronos[nom_cousin] = {}
                for match_id, scores in pronos_du_formulaire.items():
                    st.session_state.db_pronos[nom_cousin][match_id] = scores
                
                sauvegarder_json(PRONOS_FILE, st.session_state.db_pronos)
                st.success(f"Impeccable {nom_cousin} ! Enregistré.")
                st.rerun()
    else:
        st.info("👋 Écris ton prénom ci-dessus pour afficher la liste des matchs.")

# --- ONGLET 2 : CLASSEMENTS ---
with onglet2:
    st.header("🏆 Tableaux des scores")
    if not st.session_state.db_pronos:
        st.warning("Aucun prono n'a encore été enregistré.")
    else:
        choix_classement = st.radio("Type de classement souhaité :", ["Général (Cumulé)", "Par Jour spécifique"], horizontal=True)
        
        filtrer_jour = None
        if choix_classement == "Par Jour spécifique":
            jours_ordres = ["Lundi 6 Juillet", "Mardi 7 Juillet", "Jeudi 9 Juillet", "Vendredi 10 Juillet"]
            # LA CORRECTION EST ICI : key="select_cl_jour_classement" pour éviter le doublon
            filtrer_jour = st.selectbox("Sélectionne le Jour :", jours_ordres, key="select_cl_jour_classement")
        
        points_par_cousin = {}
        for cousin, pronos in st.session_state.db_pronos.items():
            total_points = 0
            for m in MATCHS:
                match_id = m["id"]
                if choix_classement == "Par Jour spécifique" and m["date"] != filtrer_jour:
                    continue
                
                if match_id in pronos and match_id in st.session_state.db_reels:
                    res_reel = st.session_state.db_reels[match_id]
                    if res_reel.get("joue", False):
                        pts = calculer_points(pronos[match_id]["p1"], pronos[match_id]["p2"], res_reel["score1"], res_reel["score2"])
                        total_points += pts
            points_par_cousin[cousin] = total_points

        if points_par_cousin:
            df = pd.DataFrame(list(points_par_cousin.items()), columns=["Cousin / Cousine", "Points"]).sort_values(by="Points", ascending=False).reset_index(drop=True)
            df.index += 1
            st.write("### 🥇 Le Classement")
            st.table(df)
        else:
            st.info("Aucun score disponible.")

# --- ONGLET 3 : TOUS LES PRONOS ---
with onglet3:
    st.header("📋 Qui a mis quoi ?")
    if st.session_state.db_pronos:
        donnees_affichage = []
        for cousin, pronos in st.session_state.db_pronos.items():
            for m in MATCHS:
                match_id = m["id"]
                p_str = f"{pronos[match_id]['p1']} - {pronos[match_id]['p2']}" if match_id in pronos else "Pas voté"
                
                res_reel = st.session_state.db_reels.get(match_id, {})
                r_str = f"{res_reel['score1']} - {res_reel['score2']}" if res_reel.get("joue", False) else "À venir"
                    
                donnees_affichage.append({"Cousin": cousin, "Jour": m["date"], "Match": f"{m['equipe1']} vs {m['equipe2']}", "Pronostic": p_str, "Score Réel": r_str})
        st.dataframe(pd.DataFrame(donnees_affichage), use_container_width=True, hide_index=True)

# --- ONGLET 4 : ESPACE ADMINISTRATEUR ---
with onglet4:
    st.header("🔒 Espace Administrateur")
    mot_de_passe = st.text_input("Entre le mot de passe admin pour entrer les scores :", type="password")
    
    if mot_de_passe == "famille2026":
        st.success("Accès autorisé. Rentre les scores des matchs terminés :")
        
        with st.form("form_admin"):
            nouveaux_reels = {}
            for m in MATCHS:
                match_id = m["id"]
                deja_regle = st.session_state.db_reels.get(match_id, {"score1": 0, "score2": 0, "joue": False})
                
                st.write(f"**{m['equipe1']} vs {m['equipe2']}** ({m['date']})")
                col_j, col_s1, col_s2 = st.columns([1, 2, 2])
                with col_j:
                    est_joue = st.checkbox("Terminé ?", value=deja_regle["joue"], key=f"joue_{match_id}")
                with col_s1:
                    s1 = st.number_input(f"Score {m['equipe1']}", min_value=0, max_value=20, value=int(deja_regle["score1"]), key=f"admin_s1_{match_id}")
                with col_s2:
                    s2 = st.number_input(f"Score {m['equipe2']}", min_value=0, max_value=20, value=int(deja_regle["score2"]), key=f"admin_s2_{match_id}")
                
                nouveaux_reels[match_id] = {"score1": s1, "score2": s2, "joue": est_joue}
            
            if st.form_submit_button("📢 Valider et Publier les résultats réels"):
                st.session_state.db_reels = nouveaux_reels
                sauvegarder_json(REELS_FILE, nouveaux_reels)
                st.success("Les résultats officiels ont été mis à jour ! Les classements sont recalculés.")
                st.rerun()