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


# --- Définition des zones personelles (modifié plus tard quand intégré dans la BDD) ---
hr_bins = [0, 153, 173, 188, 195, 204]
hr_zone_multipliers = { "Z1": 1, "Z2": 2, "Z3": 3, "Z4": 4, "Z5": 5 }
speed_bins = [0,13,16,19,21,30]  # en km/h  
zone_labels = ["Z1 - Endurance", "Z2 - Marathon", "Z3 - Seuil", "Z4 - VMA", "Z5 - Max"]
zone_colors = {
    "Z1 - Endurance": "#d3d3d3",   # Gris clair
    "Z2 - Marathon": "#add8e6",    # Bleu clair
    "Z3 - Seuil": "#90ee90",       # Vert clair
    "Z4 - VMA": "#ffb6c1",         # Orange/rose clair
    "Z5 - Max": "#f08080"          # Rouge clair
}

# --- Fonctions de Chargement des données (avec cache) ---
@st.cache_data
def load_main_data(start_date, end_date):
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

@st.cache_data
def load_weekly_volume_by_speed_zone():
    """Charge et calcule le volume hebdomadaire par zone de vitesse pour les 10 dernières semaines."""
    conn = sqlite3.connect(DATABASE_FILE)
    # On va chercher les données des 70 derniers jours (10 semaines)
    ten_weeks_ago = (datetime.now() - timedelta(days=70)).strftime('%Y-%m-%d')
    
    # Jointure pour récupérer la vitesse des records pour les activités de course à pied
    query = f"""
        SELECT
            r.activity_id,
            r.timestamp,
            r.speed, -- On récupère la vitesse
            r.distance
        FROM records r
        JOIN activities a ON r.activity_id = a.activity_id
        WHERE a.sport = 'running' AND DATE(a.start_time_gmt) >= '{ten_weeks_ago}'
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty or 'speed' not in df.columns or df['speed'].isnull().all():
        return pd.DataFrame()

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Conversion de la vitesse de m/s en km/h
    df['speed_kmh'] = df['speed'] * 3.6
    
    # Calcul de la distance par enregistrement (par seconde)
    df.sort_values(['activity_id', 'timestamp'], inplace=True)
    df['distance_per_second'] = df.groupby('activity_id')['distance'].diff().fillna(0)
    
    # Classification par zone de Vitesse
    df['speed_zone'] = pd.cut(df['speed_kmh'], bins=speed_bins, labels=zone_labels, right=False, include_lowest=True)
    
    # Définition de la semaine commençant le Lundi
    df['week_start'] = (df['timestamp'].dt.date - pd.to_timedelta(df['timestamp'].dt.weekday, unit='d')).astype(str)
    
    # Agrégation de la distance par semaine et par zone
    weekly_zone_dist = df.groupby(['week_start', 'speed_zone'])['distance_per_second'].sum().reset_index()
    weekly_zone_dist['distance_km'] = weekly_zone_dist['distance_per_second'] / 1000
    
    # On garde uniquement les 10 semaines les plus récentes
    recent_weeks = weekly_zone_dist['week_start'].unique()[-10:]
    
    return weekly_zone_dist[weekly_zone_dist['week_start'].isin(recent_weeks)]

@st.cache_data
def calculate_daily_stress(start_date, end_date):
    """Calcule le score de stress quotidien (zTRIMP * RPE) pour la période donnée."""
    conn = sqlite3.connect(DATABASE_FILE)
    start_str, end_str = start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    query = f"""
        SELECT
            r.activity_id,
            r.heart_rate,
            a.workout_rpe,
            a.workout_feel,
            a.start_time_gmt
        FROM records r
        JOIN activities a ON r.activity_id = a.activity_id
        WHERE DATE(a.start_time_gmt) BETWEEN '{start_str}' AND '{end_str}' AND r.heart_rate IS NOT NULL
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return pd.DataFrame(columns=['activity_date', 'daily_stress_score'])

    # 1. Calcul de la charge objective (zTRIMP)
    df['hr_zone'] = pd.cut(df['heart_rate'], bins=hr_bins, labels=zone_labels, right=True)
    time_in_zones = df.groupby(['activity_id', 'hr_zone']).size().unstack(fill_value=0) / 60  # en minutes

    time_in_zones['zTRIMP'] = 0
    for zone, multiplier in hr_zone_multipliers.items():
        if zone in time_in_zones.columns:
            time_in_zones['zTRIMP'] += time_in_zones[zone] * multiplier

    # 2. Calcul du multiplicateur subjectif (RPE & Ressenti)
    activity_perception = df[['activity_id', 'workout_rpe', 'workout_feel']].drop_duplicates().set_index('activity_id')
    
    def get_rpe_multiplier(rpe):
        if rpe <= 4: return 0.9
        if rpe <= 6: return 1.0
        if rpe <= 8: return 1.15
        return 1.3

    def get_feel_adjustment(feel):
        if feel <= 30: return 0.1 # Mauvais ressenti, augmente le stress
        if feel >= 70: return -0.1 # Bon ressenti, diminue le stress
        return 0.0

    activity_perception['rpe_multiplier'] = activity_perception['workout_rpe'].apply(get_rpe_multiplier)
    activity_perception['feel_adjustment'] = activity_perception['workout_feel'].apply(get_feel_adjustment)
    activity_perception['total_multiplier'] = activity_perception['rpe_multiplier'] + activity_perception['feel_adjustment']

    # 3. Calcul du score de stress final par activité
    final_scores = time_in_zones.join(activity_perception)
    final_scores.dropna(subset=['zTRIMP', 'total_multiplier'], inplace=True)
    final_scores['activity_stress_score'] = final_scores['zTRIMP'] * final_scores['total_multiplier']

    # 4. Agrégation par jour
    activity_dates = df[['activity_id', 'start_time_gmt']].drop_duplicates().set_index('activity_id')
    activity_dates['activity_date'] = pd.to_datetime(activity_dates['start_time_gmt']).dt.date
    final_scores = final_scores.join(activity_dates)
    
    daily_stress = final_scores.groupby('activity_date')['activity_stress_score'].sum().reset_index()
    daily_stress.rename(columns={'activity_stress_score': 'daily_stress_score'}, inplace=True)

    return daily_stress
    

    # 1. Calcul de la charge objective (zTRIMP)
    df['hr_zone'] = pd.cut(df['heart_rate'], bins=hr_bins, labels=hr_zone_labels, right=True)
    time_in_zones = df.groupby(['activity_id', 'hr_zone']).size().unstack(fill_value=0) / 60  # en minutes

    time_in_zones['zTRIMP'] = 0
    for zone, multiplier in hr_zone_multipliers.items():
        if zone in time_in_zones.columns:
            time_in_zones['zTRIMP'] += time_in_zones[zone] * multiplier

    # 2. Calcul du multiplicateur subjectif (RPE & Ressenti)
    activity_perception = df[['activity_id', 'workout_rpe', 'workout_feel']].drop_duplicates().set_index('activity_id')



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
df_filtered = load_main_data(start_date, end_date)
df_weekly_volume_by_speed_zone = load_weekly_volume_by_speed_zone()
df_daily_stress = calculate_daily_stress(start_date, end_date)


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
        st.subheader("Charge d'Entraînement Quotidienne")
        if df_daily_stress.empty:
            st.info("Pas de données de charge d'entraînement pour cette période.")
        else:
            fig_stress = px.bar(
                df_daily_stress,
                x='activity_date',
                y='daily_stress_score',
                title="Évolution du Score de Stress Journalier",
                labels={'activity_date': 'Date', 'daily_stress_score': 'Score de Stress (Points)'}
            )
            fig_stress.update_layout(xaxis_title=None)
            st.plotly_chart(fig_stress, use_container_width=True)

    with col_graph2:
        st.subheader("Volume Hebdomadaire par Zone de Vitesse")
        if df_weekly_volume_by_speed_zone.empty:
            st.warning("Pas de données de course à pied avec vitesse disponibles pour les 10 dernières semaines.")
        else:
            # Création du graphique en barres empilées

            weekly_totals = df_weekly_volume_by_speed_zone.groupby('week_start')['distance_km'].sum().reset_index()




            fig_weekly = px.bar(
                df_weekly_volume_by_speed_zone,
                x='week_start',
                y='distance_km',
                color='speed_zone',
                title="Distance Hebdomadaire par Zone de Vitesse (10 dernières semaines)",
                labels={'week_start': 'Semaine du', 'distance_km': 'Distance (km)', 'speed_zone': 'Zone Vitesse'},
                color_discrete_map=zone_colors,
                category_orders={"speed_zone": zone_labels} # Pour ordonner les zones correctement
            )
            fig_weekly.update_layout(barmode='stack', xaxis_title=None,yaxis_title=None)

            fig_weekly.add_traces(
                px.scatter(
                    weekly_totals,
                    x='week_start',
                    y='distance_km',
                    text=weekly_totals['distance_km'].apply(lambda x: f'{x:.1f} km')
                ).update_traces(
                    textposition='top center',
                    mode='text'
                ).data
            )

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
