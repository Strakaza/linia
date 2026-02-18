

set -e


if [ -f "static/downloads/gtfs_unifie.zip" ]; then
    echo "✅ Fichier GTFS présent"
else
    echo "❌ ERREUR: Fichier GTFS manquant!"
    exit 1
fi


docker build -t votre-app .