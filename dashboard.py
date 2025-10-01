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
