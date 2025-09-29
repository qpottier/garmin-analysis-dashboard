# Garmin Personal Training & Analysis Dashboard

Ce projet est un pipeline de données et un tableau de bord d'analyse entièrement automatisés pour les données de fitness personnelles Garmin. Il télécharge les fichiers bruts FIT et JSON d'un compte Garmin, les traite dans une base de données SQLite structurée et prépare les données pour une analyse et une visualisation avancées.

L'objectif principal est d'aller au-delà des métriques de base fournies par Garmin Connect et de construire un outil personnalisé pour suivre la charge d'entraînement, la récupération et l'état de forme en se basant sur des principes scientifiques.

<<<<<<< HEAD
[Image d'un tableau de bord moderne d'analyse de données avec des graphiques (a ajouter)]
=======
[Image d'un tableau de bord moderne d'analyse de données avec des graphiques]
>>>>>>> d0c17e0b89da4bc7dd3460b18e3339b33707c86f

---

## Fonctionnalités Clés

- **Pipeline de Données Automatisé** : Un unique script shell (`run_garmin_pipeline.sh`) gère l'ensemble du processus ETL (Extract, Transform, Load). Il télécharge de manière incrémentielle les dernières données et met à jour la base de données locale.
- **Base de Données SQLite Structurée** : Les données brutes sont parsées et organisées dans une base de données relationnelle propre avec des tables pour les activités, les tours (laps), le sommeil et les enregistrements seconde par seconde.
- **Calcul de Charge d'Entraînement Avancé** : Implémente un score de charge d'entraînement basé sur les zones cardiaques (zTRIMP) en calculant le temps passé dans 5 zones de fréquence cardiaque personnalisées pour chaque activité, fournissant une mesure très précise du stress de l'entraînement.
- **Analyse du Sommeil & de la Récupération** : Intègre les données de sommeil quotidiennes, y compris les phases de sommeil, la VFC (HRV) nocturne et la fréquence cardiaque au repos, pour quantifier la récupération.
- **Prêt pour l'Analyse** : Un Jupyter Notebook (`analysis/analysis.ipynb`) est configuré pour l'exploration des données et le prototypage de nouvelles métriques et visualisations.
- **(En cours) Tableau de Bord Interactif** : Le projet est conçu pour utiliser Streamlit afin de construire un tableau de bord web pour visualiser toutes les métriques clés.

---

## Stack Technique

- **Ingestion de Données** : Python, `garmindb`
- **Traitement des Données** : Python, `fitparse`, Pandas
- **Base de Données** : SQLite
- **Analyse & Prototypage** : Jupyter Notebook, Plotly
- **Tableau de Bord** : Streamlit

---

## Structure du Projet

garmin_project/
├── analysis/
│   └── analysis.ipynb        # Jupyter Notebook pour l'exploration des données.
├── data_import_db_creation/
│   ├── functions.py          # Logique principale pour le parsing et le remplissage de la BDD.
│   ├── main.py               # Script principal pour lancer le processus d'import.
│   └── dashboard.py          # (En cours) Application du tableau de bord Streamlit.
├── HealthData/               # (Non versionné avec Git) Données brutes Garmin téléchargées.
├── garmin_data.db            # (Non versionné avec Git) La base de données SQLite finale.
├── run_garmin_pipeline.sh    # Le script principal d'automatisation.
└── README.md                 # Ce fichier.


---

## Installation

1.  **Clonez le dépôt :**
    ```bash
    git clone <votre-url-de-repo>
    cd garmin_project
    ```

2.  **Installez les dépendances :** Il est recommandé d'utiliser un environnement virtuel.
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Configurez `garmindb` :** L'outil `garmindb` nécessite vos identifiants Garmin Connect. Il est préférable de le configurer en utilisant des variables d'environnement ou un fichier de configuration comme décrit dans la [documentation de garmindb](https://github.com/matin/garmindb).

<<<<<<< HEAD
Pour ce faire vous pouvez dans le terminal les commandes suivantes : 
mkdir ~/.GarminDB
touch ~/.GarminDB/GarminConnectConfig.json

Et remplissez le fichier de la façon suivante : 
{
    "db": {
        "type"                          : "sqlite"
    },
    "garmin": {
        "domain"                        : "garmin.com"
    },
    "credentials": {
        "user"                          : "account_email",
        "secure_password"               : false,
        "password"                      : "password",
        "password_file"                 : null
    },
    "data": {
        "weight_start_date"             : "01/01/2025",
        "sleep_start_date"              : "01/01/2025",
        "rhr_start_date"                : "01/01/2025",
        "monitoring_start_date"         : "01/01/2025",
        "download_latest_activities"    : 25,
        "download_all_activities"       : 1000
    },
    "directories": {
        "relative_to_home"              : false,
        "base_dir"                      : "./HealthData",
        "mount_dir"                     : "./Volumes/GARMIN"
    },
    "enabled_stats": {
        "monitoring"                    : true,
        "steps"                         : false,
        "itime"                         : false,
        "sleep"                         : true,
        "rhr"                           : false,
        "activities"                    : true
    },
    "course_views": {
        "steps"                         : []
    },
    "modes": {
    },
    "activities": {
        "display"                       : []
    },
    "settings": {
        "metric"                        : true,
        "default_display_activities": ["running", "cycling", "cardio"]
    },
    "checkup": {
        "look_back_days"                : 90
    }
}

=======
>>>>>>> d0c17e0b89da4bc7dd3460b18e3339b33707c86f
---

## Utilisation

1.  **Lancez le Pipeline Complet :** Pour télécharger vos données et remplir la base de données, lancez le script d'automatisation depuis le répertoire racine du projet.
    ```bash
    ./run_garmin_pipeline.sh
    ```
    La première fois, il téléchargera toutes vos données. Les exécutions suivantes ne téléchargeront que les dernières activités et données de sommeil.

2.  **Lancez le Tableau de Bord (En cours) :**
    ```bash
    streamlit run data_import_db_creation/dashboard.py
    ```