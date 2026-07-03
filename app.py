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

# Titre principal de l'application
st.title("⚽ Pronos des Cousins - Coupe du Monde 2026")

def obtenir_client_sheets():
    """Initialise la connexion avec l'API Google Sheets (via Secrets ou fichier local)."""
    try:
        url_sheet = st.secrets["gspread"]["spreadsheet_url"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        
        if "service_account" in st.secrets["gspread"]:
            creds = Credentials.from_service_account_info(st.secrets["gspread"]["service_account"], scopes=scopes)
        else:
            chemin_json = "credentials.json"
            if not os.path.exists(chemin_json):
                st.error(f"❌ Erreur : Configuration d'accès Google Sheets introuvable.")
                return None
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

def obtenir_et_securiser_onglet(sh, nom_onglet, en_tetes_attendus):
    """Récupère un onglet, force les en-têtes et injecte les matchs par défaut si vide."""
    try:
        feuille = sh.worksheet(nom_onglet)
    except gspread.exceptions.WorksheetNotFound:
        feuille = sh.add_worksheet(title=nom_onglet, rows="500", cols="10")
        feuille.insert_row(en_tetes_attendus, 1)
        return feuille, [en_tetes_attendus]
        
    valeurs = feuille.get_all_values()
    
    if not valeurs or en_tetes_attendus[0] not in valeurs[0]:
        feuille.insert_row(en_tetes_attendus, 1, value_input_option='USER_ENTERED')
        valeurs = feuille.get_all_values()
        
    if nom_onglet == "Matchs" and len(valeurs) <= 1:
        matchs_par_defaut = [
            ["Mexique", "Angleterre", "06/07/2026", "", ""],
            ["France", "Brésil", "07/07/2026", "", ""],
            ["Espagne", "Maroc", "08/07/2026", "", ""],
            ["Argentine", "Allemagne", "09/07/2026", "", ""],
            ["Italie", "USA", "10/07/2026", "", ""]
        ]
        for i, match in enumerate(matchs_par_defaut):
            feuille.insert_row(match, i + 2, value_input_option='USER_ENTERED')
        valeurs = feuille.get_all_values()
        
    return feuille, valeurs

def calculer_et_sauvegarder_classement(sh):
    """Calcule les points cumulés de chaque joueur et met à jour l'onglet Classement."""
    try:
        f_matchs, v_matchs = obtenir_et_securiser_onglet(sh, "Matchs", ["Equipe1", "Equipe2", "Date", "Score1", "Score2"])
        f_pronos, v_pronos = obtenir_et_securiser_onglet(sh, "Pronos", ["Pseudo", "Equipe1", "Equipe2", "Date", "Prono1", "Prono2"])
        
        if len(v_matchs) <= 1 or len(v_pronos) <= 1:
            # Si plus aucun prono, on vide le classement proprement
            f_class, _ = obtenir_et_securiser_onglet(sh, "Classement", ["Rang", "Pseudo", "Matchs Joués", "Scores Exacts (3pts)", "Bons Résultats (1pt)", "Total Points"])
            f_class.clear()
            f_class.insert_row(["Rang", "Pseudo", "Matchs Joués", "Scores Exacts (3pts)", "Bons Résultats (1pt)", "Total Points"], 1)
            return pd.DataFrame(columns=["Rang", "Pseudo", "Matchs Joués", "Scores Exacts (3pts)", "Bons Résultats (1pt)", "Total Points"])
            
        df_m = pd.DataFrame(v_matchs[1:], columns=v_matchs[0])
        df_p = pd.DataFrame(v_pronos[1:], columns=v_pronos[0])
        
        scores_joueurs = {}
        
        for _, prono in df_p.iterrows():
            pseudo = str(prono.get('Pseudo', '')).strip()
            if not pseudo:
                continue
            if pseudo not in scores_joueurs:
                scores_joueurs[pseudo] = {'matchs_joues': 0, 'exacts': 0, 'bons': 0, 'points': 0}
                
            match_corresp = df_m[
                (df_m['Equipe1'] == prono.get('Equipe1', '')) & 
                (df_m['Equipe2'] == prono.get('Equipe2', '')) & 
                (df_m['Date'] == prono.get('Date', ''))
            ]
            
            if not match_corresp.empty:
                m = match_corresp.iloc[0]
                s1_str, s2_str = str(m.get('Score1', '')).strip(), str(m.get('Score2', '')).strip()
                p1_str, p2_str = str(prono.get('Prono1', '')).strip(), str(prono.get('Prono2', '')).strip()
                
                if s1_str != "" and s2_str != "" and p1_str != "" and p2_str != "":
                    try:
                        s1, s2 = int(s1_str), int(s2_str)
                        p1, p2 = int(p1_str), int(p2_str)
                        
                        scores_joueurs[pseudo]['matchs_joues'] += 1
                        
                        if s1 == p1 and s2 == p2:
                            scores_joueurs[pseudo]['exacts'] += 1
                            scores_joueurs[pseudo]['points'] += 3
                        elif (s1 > s2 and p1 > p2) or (s1 < s2 and p1 < p2) or (s1 == s2 and p1 == p2):
                            scores_joueurs[pseudo]['bons'] += 1
                            scores_joueurs[pseudo]['points'] += 1
                    except ValueError:
                        pass
                        
        liste_rows = []
        for ps, stats in scores_joueurs.items():
            liste_rows.append({
                "Pseudo": ps,
                "Matchs Joués": stats['matchs_joues'],
                "Scores Exacts (3pts)": stats['exacts'],
                "Bons Résultats (1pt)": stats['bons'],
                "Total Points": stats['points']
            })
            
        df_res = pd.DataFrame(liste_rows)
        if not df_res.empty:
            df_res = df_res.sort_values(by="Total Points", ascending=False).reset_index(drop=True)
            df_res.insert(0, "Rang", df_res.index + 1)
        else:
            df_res = pd.DataFrame(columns=["Rang", "Pseudo", "Matchs Joués", "Scores Exacts (3pts)", "Bons Résultats (1pt)", "Total Points"])
            
        f_class, _ = obtenir_et_securiser_onglet(sh, "Classement", ["Rang", "Pseudo", "Matchs Joués", "Scores Exacts (3pts)", "Bons Résultats (1pt)", "Total Points"])
        f_class.clear()
        f_class.update(range_name="A1", values=[df_res.columns.tolist()] + df_res.values.tolist(), value_input_option='USER_ENTERED')
        return df_res
    except Exception as e:
        st.error(f"Erreur classement : {e}")
        return None

# Connexion initiale
sh = obtenir_client_sheets()

if sh:
    aujourdhui = datetime.date.today()
    lundi_en_cours = aujourdhui - datetime.timedelta(days=aujourdhui.weekday())
    lundi_prochain = lundi_en_cours + datetime.timedelta(weeks=1)
    
    onglet1, onglet2, onglet3, onglet4 = st.tabs([
        "🎯 Saisir mes Pronos", 
        "📊 Classements", 
        "📋 Tous les Pronos", 
        "⚙️ Admin"
    ])

    # --- ONGLET 1 : SAISIR MES PRONOS ---
    with onglet1:
        choix_semaine = st.radio(
            "📅 Quelle période veux-tu afficher ?", 
            ["Semaine en cours", "Semaine prochaine"], 
            index=0, 
            horizontal=True
        )
        
        if choix_semaine == "Semaine en cours":
            date_debut = lundi_en_cours
            date_fin = lundi_en_cours + datetime.timedelta(days=4)
        else:
            date_debut = lundi_prochain
            date_fin = lundi_prochain + datetime.timedelta(days=4)

        st.markdown(f"### 📝 Matchs du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}")
        pseudo_saisi = st.text_input("Entre ton Prénom (ou Pseudo unique) :", key="pseudo_utilisateur")
        
        if not pseudo_saisi:
            st.info("✍️ Écris ton prénom ci-dessus pour afficher tes matchs à pronostiquer.")
        else:
            pseudo = pseudo_saisi.strip().capitalize()
            st.success(f"🏆 Bienvenue {pseudo} !")
            
            try:
                f_matchs, vals_m = obtenir_et_securiser_onglet(sh, "Matchs", ["Equipe1", "Equipe2", "Date", "Score1", "Score2"])
                f_pronos, vals_p = obtenir_et_securiser_onglet(sh, "Pronos", ["Pseudo", "Equipe1", "Equipe2", "Date", "Prono1", "Prono2"])
                
                df_pronos_all = pd.DataFrame(vals_p[1:], columns=vals_p[0]) if len(vals_p) > 1 else pd.DataFrame(columns=["Pseudo", "Equipe1", "Equipe2", "Date", "Prono1", "Prono2"])

                if len(vals_m) > 1:
                    df_matchs = pd.DataFrame(vals_m[1:], columns=vals_m[0])
                    df_matchs['Date_Formatee'] = pd.to_datetime(df_matchs['Date'], format='%d/%m/%Y', errors='coerce').dt.date
                    
                    df_filtre = df_matchs[(df_matchs['Date_Formatee'] >= date_debut) & (df_matchs['Date_Formatee'] <= date_fin)]
                    
                    if not df_filtre.empty:
                        dict_inputs = {}
                        tous_verrouilles = True
                        
                        with st.form("formulaire_pronos"):
                            for idx, match in df_filtre.iterrows():
                                jours_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
                                jour_nom = jours_fr[match['Date_Formatee'].weekday()]
                                
                                prono_existant = df_pronos_all[
                                    (df_pronos_all['Pseudo'] == pseudo) & 
                                    (df_pronos_all['Equipe1'] == match['Equipe1']) & 
                                    (df_pronos_all['Equipe2'] == match['Equipe2']) & 
                                    (df_pronos_all['Date'] == match['Date'])
                                ]
                                
                                val_defaut_1 = 0
                                val_defaut_2 = 0
                                deja_enregistre = False
                                
                                if not prono_existant.empty:
                                    val_defaut_1 = int(prono_existant.iloc[0]['Prono1']) if str(prono_existant.iloc[0]['Prono1']).isdigit() else 0
                                    val_defaut_2 = int(prono_existant.iloc[0]['Prono2']) if str(prono_existant.iloc[0]['Prono2']).isdigit() else 0
                                    deja_enregistre = True
                                else:
                                    tous_verrouilles = False # S'il reste au moins un match sans prono
                                
                                # Affichage du statut verrouillé ou non
                                statut_texte = "🔒 Enregistré & Verrouillé" if deja_enregistre else "⏳ Non enregistré"
                                st.write(f"📅 **{jour_nom} {match['Date']}** — ⚽ **{match['Equipe1']}** vs **{match['Equipe2']}** *({statut_texte})*")
                                
                                col1, col2 = st.columns(2)
                                dict_inputs[f"e1_{idx}"] = col1.number_input(f"Score {match['Equipe1']}", min_value=0, step=1, value=val_defaut_1, key=f"in_e1_{idx}_{pseudo}", disabled=deja_enregistre)
                                dict_inputs[f"e2_{idx}"] = col2.number_input(f"Score {match['Equipe2']}", min_value=0, step=1, value=val_defaut_2, key=f"in_e2_{idx}_{pseudo}", disabled=deja_enregistre)
                                st.write("---")
                            
                            if tous_verrouilles:
                                st.info("🔒 Tous tes pronostics pour cette période sont validés et verrouillés. Contacte Victor s'il y a une erreur.")
                                bouton_soumettre = st.form_submit_button("💾 Pronostics verrouillés", disabled=True)
                            else:
                                st.warning("⚠️ Attention : Valider verrouillera définitivement les scores saisis ci-dessus.")
                                bouton_soumettre = st.form_submit_button("💾 Enregistrer mes pronostics")
                            
                            if bouton_soumettre and not tous_verrouilles:
                                for idx, match in df_filtre.iterrows():
                                    # On ne traite et n'ajoute que ceux qui n'étaient pas déjà enregistrés
                                    prono_existant = df_pronos_all[
                                        (df_pronos_all['Pseudo'] == pseudo) & 
                                        (df_pronos_all['Equipe1'] == match['Equipe1']) & 
                                        (df_pronos_all['Equipe2'] == match['Equipe2']) & 
                                        (df_pronos_all['Date'] == match['Date'])
                                    ]
                                    
                                    if prono_existant.empty:
                                        p1 = dict_inputs[f"e1_{idx}"]
                                        p2 = dict_inputs[f"e2_{idx}"]
                                        nouvel_enregistrement = {
                                            "Pseudo": pseudo, "Equipe1": match['Equipe1'], "Equipe2": match['Equipe2'],
                                            "Date": match['Date'], "Prono1": p1, "Prono2": p2
                                        }
                                        df_pronos_all = pd.concat([df_pronos_all, pd.DataFrame([nouvel_enregistrement])], ignore_index=True)
                                
                                f_pronos.clear()
                                f_pronos.update(range_name="A1", values=[df_pronos_all.columns.tolist()] + df_pronos_all.values.tolist(), value_input_option='USER_ENTERED')
                                
                                calculer_et_sauvegarder_classement(sh)
                                st.toast("🎉 Vos pronostics ont été validés et verrouillés !", icon="🚀")
                                st.rerun()
                    else:
                        st.warning("ℹ️ Aucun match n'est programmé pour cette période.")
                else:
                    st.warning("Aucun match configuré dans l'onglet 'Matchs' de ton Google Sheets.")
            except Exception as e:
                st.error(f"Erreur d'affichage : {e}")

    # --- ONGLET 2 : CLASSEMENTS ---
    with onglet2:
        st.markdown("## 📊 Classement général")
        df_classement = calculer_et_sauvegarder_classement(sh)
        
        if df_classement is not None and not df_classement.empty:
            st.markdown("### 👑 Le Top 3 du moment")
            cols_podium = st.columns(3)
            
            for rank in [1, 2, 3]:
                if len(df_classement) >= rank:
                    joueur = df_classement.iloc[rank-1]
                    medailles = {1: "🥇 1er", 2: "🥈 2ème", 3: "🥉 3ème"}
                    cols_podium[rank-1].metric(
                        label=f"{medailles[rank]} : {joueur['Pseudo']}", 
                        value=f"{joueur['Total Points']} pts",
                        delta=f"{joueur['Scores Exacts (3pts)']} exact(s)"
                    )
            st.write("---")
            st.dataframe(df_classement, use_container_width=True, hide_index=True)
        else:
            st.info("💡 Les points cumulés apparaîtront ici dès qu'un match aura un score officiel entré par l'Admin.")

    # --- ONGLET 3 : TOUS LES PRONOS ---
    with onglet3:
        st.markdown("## 📋 Historique global de tous les Pronostics")
        try:
            _, vals = obtenir_et_securiser_onglet(sh, "Pronos", ["Pseudo", "Equipe1", "Equipe2", "Date", "Prono1", "Prono2"])
            if len(vals) > 1:
                df_tous_pronos = pd.DataFrame(vals[1:], columns=vals[0])
                
                recherche_pseudo = st.text_input("🔍 Filtrer par prénom pour espionner un cousin :").strip().capitalize()
                if recherche_pseudo:
                    df_tous_pronos = df_tous_pronos[df_tous_pronos['Pseudo'] == recherche_pseudo]
                    
                st.dataframe(df_tous_pronos, use_container_width=True, hide_index=True)
            else:
                st.info("💡 Aucun pronostic n'a encore été enregistré dans le système.")
        except Exception as e:
            st.error(f"Erreur : {e}")

    # --- ONGLET 4 : ESPACE ADMIN ---
    with onglet4:
        st.markdown("## ⚙️ Administration du jeu (Réservé à Victor)")
        if st.text_input("Entre le mot de passe Admin :", type="password", key="pwd_admin") == "admin123":
            st.success("🔓 Mode admin activé !")
            
            action = st.radio("Que veux-tu faire ?", [
                "➕ Ajouter un nouveau match", 
                "🏆 Entrer le score d'un match joué",
                "❌ Gestion des erreurs / Suppressions"
            ])
            
            # Action A : Ajouter un match
            if action == "➕ Ajouter un nouveau match":
                st.write("### 📝 Créer une nouvelle affiche")
                with st.form("form_ajout"):
                    eq1 = st.text_input("Nom Équipe Domicile :")
                    eq2 = st.text_input("Nom Équipe Extérieur :")
                    dt = st.text_input("Date du match (Format : JJ/MM/AAAA) :", value=lundi_prochain.strftime("%d/%m/%Y"))
                    
                    if st.form_submit_button("💾 Envoyer le match sur le site"):
                        if eq1 and eq2 and dt:
                            try:
                                f_matchs, vals = obtenir_et_securiser_onglet(sh, "Matchs", ["Equipe1", "Equipe2", "Date", "Score1", "Score2"])
                                prochaine_ligne = len(vals) + 1
                                f_matchs.insert_row([eq1, eq2, dt, "", ""], prochaine_ligne, value_input_option='USER_ENTERED')
                                st.success(f"✅ Match {eq1} vs {eq2} ajouté !")
                                st.rerun()
                            except Exception as err:
                                st.error(f"Erreur d'écriture : {err}")
                        else:
                            st.warning("Remplis toutes les cases.")
            
            # Action B : Entrer les scores
            elif action == "🏆 Entrer le score d'un match joué":
                st.write("### 🎯 Enregistrer un résultat officiel")
                try:
                    f_matchs, vals = obtenir_et_securiser_onglet(sh, "Matchs", ["Equipe1", "Equipe2", "Date", "Score1", "Score2"])
                    
                    if len(vals) > 1:
                        options_matchs = []
                        for i, m in enumerate(vals[1:]):
                            options_matchs.append(f"Ligne {i+2} : {m[0]} vs {m[1]} ({m[2]})")
                        
                        match_choisi = st.selectbox("Sélectionne le match à clôturer :", options_matchs)
                        ligne_cible = int(match_choisi.split(" ")[1])
                        
                        match_selectionne = vals[ligne_cible - 1]
                        score1_actuel = int(match_selectionne[3]) if len(match_selectionne) > 3 and match_selectionne[3].isdigit() else 0
                        score2_actuel = int(match_selectionne[4]) if len(match_selectionne) > 4 and match_selectionne[4].isdigit() else 0
                        
                        c1, c2 = st.columns(2)
                        sc1 = c1.number_input("Score Réel Domicile", min_value=0, step=1, value=score1_actuel, key="sc_admin_1")
                        sc2 = c2.number_input("Score Réel Extérieur", min_value=0, step=1, value=score2_actuel, key="sc_admin_2")
                        
                        if st.button("🏁 Enregistrer définitivement le score"):
                            f_matchs.update_cell(ligne_cible, 4, sc1)
                            f_matchs.update_cell(ligne_cible, 5, sc2)
                            
                            calculer_et_sauvegarder_classement(sh)
                            st.success("🎉 Score validé et points mis à jour !")
                            st.rerun()
                    else:
                        st.info("Aucun match créé pour le moment.")
                except Exception as err:
                    st.error(f"Erreur : {err}")
            
            # ❌ NEW ACTION C : GESTION DES ERREURS & SUPPRESSIONS
            elif action == "❌ Gestion des erreurs / Suppressions":
                st.write("### 🛠️ Espace de correction des Pronostics")
                try:
                    f_pronos, vals_p = obtenir_et_securiser_onglet(sh, "Pronos", ["Pseudo", "Equipe1", "Equipe2", "Date", "Prono1", "Prono2"])
                    
                    if len(vals_p) > 1:
                        df_p_admin = pd.DataFrame(vals_p[1:], columns=vals_p[0])
                        liste_pseudos = sorted(df_p_admin['Pseudo'].unique().tolist())
                        
                        cousin_selectionne = st.selectbox("Sélectionne le cousin qui a fait une erreur :", liste_pseudos)
                        
                        # Option 1 : Tout supprimer d'un coup
                        st.markdown(f"#### 💥 Option Radicale : Supprimer tout le profil de **{cousin_selectionne}**")
                        if st.button(f"🗑️ Effacer définitivement TOUS les pronos de {cousin_selectionne}"):
                            df_p_admin = df_p_admin[df_p_admin['Pseudo'] != cousin_selectionne]
                            f_pronos.clear()
                            f_pronos.update(range_name="A1", values=[df_p_admin.columns.tolist()] + df_p_admin.values.tolist(), value_input_option='USER_ENTERED')
                            calculer_et_sauvegarder_classement(sh)
                            st.success(f"🔥 Tous les pronostics de {cousin_selectionne} ont été balayés. Il peut rejouer !")
                            st.rerun()
                            
                        st.write("---")
                        
                        # Option 2 : Supprimer un prono individuel
                        st.markdown(f"#### 🎯 Option Précise : Débloquer un seul match pour **{cousin_selectionne}**")
                        df_cousin = df_p_admin[df_p_admin['Pseudo'] == cousin_selectionne]
                        
                        options_matchs_cousin = []
                        for idx, r in df_cousin.iterrows():
                            options_matchs_cousin.append(f"ID {idx} : {r['Equipe1']} vs {r['Equipe2']} ({r['Date']}) -> Prono: {r['Prono1']}-{r['Prono2']}")
                        
                        match_prono_choisi = st.selectbox("Sélectionne le prono erroné à supprimer :", options_matchs_cousin)
                        id_dataframe = int(match_prono_choisi.split(" ")[1])
                        
                        if st.button("🗑️ Supprimer uniquement ce prono"):
                            df_p_admin = df_p_admin.drop(id_dataframe)
                            f_pronos.clear()
                            f_pronos.update(range_name="A1", values=[df_p_admin.columns.tolist()] + df_p_admin.values.tolist(), value_input_option='USER_ENTERED')
                            calculer_et_sauvegarder_classement(sh)
                            st.success("✅ Pronostic supprimé avec succès ! La case est débloquée pour ce joueur.")
                            st.rerun()
                    else:
                        st.info("Aucun pronostic n'est enregistré dans la base pour le moment.")
                except Exception as err:
                    st.error(f"Erreur lors de la suppression : {err}")