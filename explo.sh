#!/bin/bash

# --- Configuration ---
# Se déplace systématiquement à la racine du projet pour que les chemins relatifs fonctionnent
cd "$(dirname "$0")"

# --- CONFIGURATION UTILISATEUR ---
USER_ID="qpottier"
# Chemin complet vers VOTRE fichier de configuration spécifique
USER_CONFIG_PATH="$HOME/.GarminDB/GarminConnectConfig_${USER_ID}.json"
# Chemin vers le fichier que garmindb recherche par DÉFAUT
DEFAULT_CONFIG_PATH="$HOME/.GarminDB/GarminConnectConfig.json"
# Dossier de destination pour les données
HEALTH_DATA_DIR="./HealthData_${USER_ID}"


echo "--- Lancement du pipeline pour l'utilisateur : $USER_ID ---"

# --- SSL Certificate fix for macOS ---
export SSL_CERT_FILE=$(python3 -m certifi)
export REQUESTS_CA_BUNDLE=$(python3 -m certifi)

# --- ÉTAPE 1: Téléchargement des données ---

# Astuce : On renomme temporairement votre fichier de config pour qu'il corresponde au nom par défaut
# que garmindb recherche. C'est plus fiable que de passer le chemin en argument.
echo "Préparation du fichier de configuration..."
mv "$USER_CONFIG_PATH" "$DEFAULT_CONFIG_PATH"

# # Logique de téléchargement
# if [ ! -d "$HEALTH_DATA_DIR" ]; then
#     echo "Dossier de données non trouvé. Lancement du téléchargement initial..."
#     # On lance la commande SANS l'option --config, elle trouvera le fichier par défaut
#     garmindb_cli.py --activities --sleep --download
# else
#     echo "Dossier de données trouvé. Lancement de la mise à jour..."
#     garmindb_cli.py --activities --sleep --latest --download
# fi

# **IMPORTANT** : On remet le fichier de config à son nom d'origine après le téléchargement
echo "Restauration du fichier de configuration..."
mv "$DEFAULT_CONFIG_PATH" "$USER_CONFIG_PATH"


# --- ÉTAPE 2: Importation dans la base de données ---
echo "Lancement du script d'importation vers la base de données..."
# Script doesn't need arguments since paths are hardcoded
.venv/bin/python scripts/main.py


echo "--- Pipeline pour l'utilisateur $USER_ID terminé. ---"