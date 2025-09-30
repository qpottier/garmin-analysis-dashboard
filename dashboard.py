import streamlit as st
import sqlite3
import pandas as pd
import os
import plotly.express as px
from datetime import datetime, timedelta

# --- Configuration de la Page ---
st.set_page_config(
    page_title="Suivi de la charge d'entrainement",
    page_icon="🏃‍♂️",
    layout="wide"
)

# --- Configuration des paths ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.getcwd(), '.'))
DATABASE_FILE = os.path.join(PROJECT_ROOT, "garmin_data.db")

# --- Fonctions de Chargement des données (avec cache) ---
@st.cache_data
def load_data(start_date, end_date):
    conn = sqlite3.connect(DATABASE_FILE)

    # Assurer que les dates sont au bon format pour SQL
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')

    query = f"""
    SELECT * FROM activities WHERE DATE(start_time_gmt) BETWEEN '{start_str}' AND '{end_str}'
    """
    df_activities = pd.read_sql_query(query, conn)
    
    conn.close()
    return df_activities

# --- Barre latérale ---

st.sidebar.header("Filtres")

# Filtre par date
period_option = st.sidebar.selectbox(
    "Choisir la période :",
    ("Cette semaine", "La semaine dernière", "Ce mois-ci", "Le mois dernier", "Année en cours")
)

# Définir les dates en fonction de l'option choisie
today = datetime.now().date()
if period_option == "Cette semaine":
    start_date = today - timedelta(days=today.weekday())
    end_date = start_date + timedelta(days=6)
elif period_option == "La semaine dernière":
    start_date = today - timedelta(days=today.weekday() + 7)
    end_date = start_date + timedelta(days=6)
elif period_option == "Ce mois-ci":
    start_date = today.replace(day=1)
    end_date = (start_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)
elif period_option == "Le mois dernier":
    last_month_end = today.replace(day=1) - timedelta(days=1)
    start_date = last_month_end.replace(day=1)
    end_date = last_month_end
elif period_option == "Année en cours":
    start_date = today.replace(month=1, day=1)
    end_date = today

st.sidebar.info(f"Période sélectionnée : \n{start_date.strftime('%d/%m/%Y')} au {end_date.strftime('%d/%m/%Y')}")

# --- Chargement des données filtrées ---
df_filtered = load_data(start_date, end_date)

# --- Affichage du Dashboard ---
st.title("🏃‍♂️ Dashboard d'Analyse d'Entraînement")
st.markdown(f"### Vue d'ensemble pour la période : *{period_option}*")

if df_filtered.empty:
    st.warning("Aucune donnée disponible pour la période sélectionnée.")
else:
    # --- Indicateurs Clés (KPIs) ---
    total_kms = df_filtered['distance_m'].sum() / 1000
    total_sessions = len(df_filtered)
    total_temps_minutes = df_filtered['total_timer_time_s'].sum() / 60
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Distance Totale", f"{total_kms:.2f} km")
    col3.metric("Sessions", f"{total_sessions}")
    col4.metric("Temps d'effort", f"{total_temps_minutes:.0f} min")

    st.markdown("---")

    # --- Graphiques ---
    col_graph1, col_graph2 = st.columns(2)
    
    with col_graph1:
        st.subheader("Charge d'entraînement (zTRIMP)")
        # Placeholder - nous construirons ce graphique ensuite
        st.info("Le calcul de la charge d'entraînement (zTRIMP) sera implémenté ici.")
        # Exemple de graphique simple en attendant
        df_daily_volume = df_filtered.copy()
        df_daily_volume['activity_date'] = pd.to_datetime(df_daily_volume['start_time_gmt']).dt.date
        daily_summary = df_daily_volume.groupby('activity_date')['distance_m'].sum() / 1000
        fig_placeholder = px.bar(daily_summary, title="Volume par jour (km)", labels={'value': 'Distance (km)', 'activity_date': 'Date'})
        st.plotly_chart(fig_placeholder, use_container_width=True)

    with col_graph2:
        st.subheader("Volume par semaine")
        # Placeholder - nous construirons ce graphique ensuite
        st.info("Le graphique de volume par semaine sera implémenté ici.")
        df_weekly_volume = df_filtered.copy()
        df_weekly_volume['week_number'] = pd.to_datetime(df_weekly_volume['start_time_gmt']).dt.strftime('%Y-%U')
        weekly_summary = df_weekly_volume.groupby('week_number')['distance_m'].sum() / 1000
        fig_weekly = px.bar(weekly_summary, title="Volume hebdomadaire (km)", labels={'value': 'Distance (km)', 'week_number': 'Semaine'})
        st.plotly_chart(fig_weekly, use_container_width=True)

    st.markdown("---")

    # --- Tableau des Activités ---
    st.subheader("Détail des Activités")
    st.dataframe(df_filtered[[
        'start_time_gmt', 'sport', 'distance_m', 'total_timer_time_s', 
        'total_ascent', 'avg_hr', 'workout_rpe', 'workout_feel'
    ]].rename(columns={
        'start_time_gmt': 'Date',
        'sport': 'Sport',
        'distance_m': 'Distance (m)',
        'total_timer_time_s': 'Durée (s)',
        'total_ascent': 'D+ (m)',
        'avg_hr': 'FC Moy.',
        'workout_rpe': 'RPE',
        'workout_feel': 'Ressenti'
    }).sort_values(by='Date', ascending=False), use_container_width=True)
