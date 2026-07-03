import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import os
import datetime

# 1. Configuration de la page Streamlit
st.set_page_config(
    page_title="Pronos des Cousins - Coupe du Monde 2026",
    page_icon="⚽",
    layout="wide"
)

# 2. Titre principal de l'application
st.markdown("<h1 style='text-align: center; color: #1e3d59;'>⚽ Pronos des Cousins - Coupe du Monde 2026</h1>", unsafe_allow_html=True)

def obtenir_client_sheets():
    """Initialise la connexion avec l'API Google Sheets."""
    try:
        url_sheet = st.secrets["gspread"]["spreadsheet_url"]
        chemin_json = "credentials.json"
        
        if not os.path.exists(chemin_json):
            st.error(f"❌ Erreur : Le fichier '{chemin_json}' est introuvable.")
            return None
            
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(chemin_json, scopes=scopes)
        client = gspread.authorize(creds)
        
        if "/d/" in url_sheet:
            id_sheet = url_sheet.split("/d/")[1].split("/")[0]
            return client.open_by_key(id_sheet)
        else:
            return client.open_by_url(url_sheet)
    except Exception as e:
        st.error(f"❌ Erreur de connexion avec Google Sheets : {e}")
        return None

# Connexion à Google Sheets
sh = obtenir_client_sheets()

if sh:
    # 📆 CALCULS DES DATES POUR LE FILTRAGE DE LA SEMAINE (LUNDI AU VENDREDI)
    aujourdhui = datetime.date.today()
    lundi_en_cours = aujourdhui - datetime.timedelta(days=aujourdhui.weekday())
    vendredi_en_cours = lundi_en_cours + datetime.timedelta(days=4)
    
    lundi_prochain = lundi_en_cours + datetime.timedelta(weeks=1)
    vendredi_prochain = lundi_prochain + datetime.timedelta(days=4)
    
    # Barre latérale pour naviguer entre les semaines de matchs
    st.sidebar.markdown("### 📅 Calendrier des Matchs")
    choix_semaine = st.sidebar.radio(
        "Sélectionne la semaine :",
        [
            f"Semaine en cours ({lundi_en_cours.strftime('%d/%m')} au {vendredi_en_cours.strftime('%d/%m')})",
            f"Semaine prochaine ({lundi_prochain.strftime('%d/%m')} au {vendredi_prochain.strftime('%d/%m')})"
        ]
    )
    
    if "en cours" in choix_semaine:
        date_debut, date_fin = lundi_en_cours, vendredi_en_cours
    else:
        date_debut, date_fin = lundi_prochain, vendredi_prochain

    # Création des onglets principaux
    onglet1, onglet2, onglet3, onglet4 = st.tabs([
        "🎯 Saisir mes Pronos", 
        "📊 Classements", 
        "📋 Tous les Pronos", 
        "⚙️ Admin"
    ])

    # --- ONGLET 1 : SAISIR MES PRONOS ---
    with onglet1:
        st.markdown(f"## 📝 Matchs du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}")
        pseudo = st.text_input("Entre ton Prénom (ou Pseudo unique) :", key="pseudo_utilisateur")
        
        if not pseudo:
            st.info("✍️ Écris ton prénom ci-dessus pour afficher tes matchs à pronostiquer.")
        else:
            st.success(f"🏆 Bienvenue {pseudo} !")
            try:
                feuille_matchs = sh.worksheet("Matchs")
                donnees_matchs = feuille_matchs.get_all_records()
                
                if donnees_matchs:
                    df_matchs = pd.DataFrame(donnees_matchs)
                    df_matchs['Date_Formatee'] = pd.to_datetime(df_matchs['Date'], format='%d/%m/%Y', errors='coerce').dt.date
                    
                    # Filtrage dynamique : uniquement de ce lundi à ce vendredi
                    df_filtre = df_matchs[(df_matchs['Date_Formatee'] >= date_debut) & (df_matchs['Date_Formatee'] <= date_fin)]
                    
                    if not df_filtre.empty:
                        with st.form("formulaire_pronos"):
                            for idx, match in df_filtre.iterrows():
                                jours_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
                                jour_nom = jours_fr[match['Date_Formatee'].weekday()]
                                
                                # Si le score réel existe déjà, on indique que le match est terminé
                                complet = str(match.get('Score1', '')) != '' and str(match.get('Score2', '')) != ''
                                statut = f" | 🏁 Terminé ({match['Score1']}-{match['Score2']})" if complet else ""
                                
                                st.write(f"📅 **{jour_nom} {match['Date']}** — ⚽ **{match['Equipe1']}** vs **{match['Equipe2']}** {statut}")
                                col1, col2 = st.columns(2)
                                col1.number_input(f"Score {match['Equipe1']}", min_value=0, step=1, key=f"e1_{idx}", disabled=complet)
                                col2.number_input(f"Score {match['Equipe2']}", min_value=0, step=1, key=f"e2_{idx}", disabled=complet)
                                st.write("---")
                            
                            if st.form_submit_button("💾 Enregistrer mes pronostics"):
                                st.toast("🎉 Vos pronostics ont bien été envoyés au Sheets !")
                    else:
                        st.warning("ℹ️ Aucun match n'est encore enregistré pour cette semaine.")
                else:
                    st.warning("Aucun match configuré dans l'onglet 'Matchs' de ton Google Sheets.")
            except Exception as e:
                st.error(f"Erreur d'affichage : {e}")

    # --- ONGLET 2 : CLASSEMENTS ---
    with onglet2:
        st.markdown("## 📊 Classements des Cousins")
        try:
            st.dataframe(pd.DataFrame(sh.worksheet("Classement").get_all_records()), use_container_width=True)
        except Exception:
            st.info("💡 Les classements apparaîtront ici dès que l'onglet 'Classement' sera complété.")

    # --- ONGLET 3 : TOUS LES PRONOS ---
    with onglet3:
        st.markdown("## 📋 Historique de tous les Pronos")
        try:
            st.dataframe(pd.DataFrame(sh.worksheet("Pronos").get_all_records()), use_container_width=True)
        except Exception:
            st.info("💡 Vos pronos s'enregistreront ici.")

    # --- ONGLET 4 : LE RETOUR DE L'ESPACE ADMIN 🔥 ---
    with onglet4:
        st.markdown("## ⚙️ Administration du jeu (Réservé à Victor)")
        if st.text_input("Entre le mot de passe Admin :", type="password") == "admin123":
            st.success("🔓 Bienvenue Victor. Mode admin activé !")
            
            action = st.radio("Que veux-tu faire ?", ["➕ Ajouter un nouveau match", "🏆 Entrer le score d'un match joué"])
            
            # Action A : Ajouter un match directement depuis l'interface
            if action == "➕ Ajouter un nouveau match":
                st.write("### 📝 Créer une nouvelle affiche")
                with st.form("form_ajout"):
                    eq1 = st.text_input("Nom Équipe Domicile :")
                    eq2 = st.text_input("Nom Équipe Extérieur :")
                    dt = st.text_input("Date du match (Format 필수 : JJ/MM/AAAA) :", value=aujourdhui.strftime("%d/%m/%Y"))
                    
                    if st.form_submit_button("💾 Envoyer le match sur le site"):
                        if eq1 and eq2 and dt:
                            try:
                                f_matchs = sh.worksheet("Matchs")
                                # Ajoute la ligne : Equipe1, Equipe2, Date, Score1(vide), Score2(vide)
                                f_matchs.append_row([eq1, eq2, dt, "", ""])
                                st.success(f"✅ Match {eq1} vs {eq2} correctement ajouté au calendrier !")
                                st.rerun()
                            except Exception as err:
                                st.error(f"Erreur d'écriture : {err}")
                        else:
                            st.warning("Remplis toutes les cases avant de valider.")
            
            # Action B : Valider les scores réels
            elif action == "🏆 Entrer le score d'un match joué":
                st.write("### 🎯 Enregistrer un résultat officiel")
                try:
                    f_matchs = sh.worksheet("Matchs")
                    tous_les_matchs = f_matchs.get_all_records()
                    
                    if tous_les_matchs:
                        options_matchs = []
                        for i, m in enumerate(tous_les_matchs):
                            options_matchs.append(f"Ligne {i+2} : {m['Equipe1']} vs {m['Equipe2']} ({m['Date']})")
                        
                        match_choisi = st.selectbox("Sélectionne le match à clôturer :", options_matchs)
                        ligne_cible = int(match_choisi.split(" ")[1])
                        
                        c1, c2 = st.columns(2)
                        sc1 = c1.number_input("Score Réel Domicile", min_value=0, step=1)
                        sc2 = c2.number_input("Score Réel Extérieur", min_value=0, step=1)
                        
                        if st.button("🏁 Enregistrer définitivement le score"):
                            # Colonne 4 = Score1, Colonne 5 = Score2 dans le Google Sheets
                            f_matchs.update_cell(ligne_cible, 4, sc1)
                            f_matchs.update_cell(ligne_cible, 5, sc2)
                            st.success("🎉 Score validé ! Les points vont pouvoir être calculés.")
                            st.rerun()
                    else:
                        st.info("Aucun match créé pour le moment.")
                except Exception as err:
                    st.error(f"Erreur : {err}")