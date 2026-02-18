# Linia

Linia est une application web de visualisation et de planification de trajets de bus longue distance. Elle agrège et unifie les données de transport (GTFS) de plusieurs opérateurs pour offrir une vue consolidée du réseau de transport interurbain.

## Aperçu Fonctionnel

L'application permet aux utilisateurs de :
- Explorer interactivement les lignes de bus sur une carte dynamique.
- Rechercher des arrêts et des villes spécifiques.
- Visualiser les connexions directes entre les villes.
- Planifier des itinéraires en consultant les horaires et les parcours détaillés.
- Télécharger le jeu de données GTFS unifié généré par l'application.

## Architecture Technique

### 1. Pipeline de Données (Collecte et Unification)
Le cœur de l'application repose sur un processus de traitement de données situé dans `build_gtfs.py`.
- **Sources** : Récupération automatisée des flux GTFS statiques depuis data.gouv.fr (FlixBus et BlaBlaCar Bus).
- **Filtrage Temporel** : Sélection des services valides sur une fenêtre temporelle spécifique pour garantir la pertinence des données.
- **Unification par Ville** : Pour garantir la clarté du réseau, l'application regroupe tous les arrêts physiques d'une même ville sous un point unique ("Master Stop"). Ce processus unifie les réseaux FlixBus et BlaBlaCar à l'échelle urbaine, facilitant la recherche et la visualisation.
- **Simplification Topologique** : Élimination des redondances et filtrage des trajets aller-retour pour ne conserver qu'une structure de réseau propre et lisible.

### 2. Backend (Serveur et API)
Le serveur, implémenté avec Flask, assure la logique métier et la distribution des données :
- **Traitement Pandas** : Chargement et manipulation en mémoire des fichiers GTFS pour des réponses API rapides.
- **Points d'accès API** : Fourniture de données structurées (JSON) pour la recherche d'arrêts, les détails des voyages (shapes) et les matrices de connexion entre villes.
- **Gestion de la Localisation** : Support multilingue intégré côté serveur et client.

### 3. Frontend (Interface Utilisateur)
L'interface est conçue pour être performante et respectueuse des standards modernes :
- **Visualisation Cartographique** : Utilisation de Leaflet pour le rendu fluide des tracés géographiques avec les fonds de carte CartoDB.
- **Expérience Utilisateur** : Design responsive avec une esthétique épurée, sans dépendances lourdes (Vanilla JavaScript et CSS).
- **Internationalisation (i18n)** : Système de traduction dynamique gérant plusieurs langues.

## Structure du Projet

- `app.py` : Point d'entrée de l'application Flask et définition des routes API.
- `build_gtfs.py` : Script de traitement et d'unification des fichiers GTFS.
- `static/` : Ressources statiques (CSS, JavaScript, manifest PWA).
- `templates/` : Gabarits HTML (Accueil, Carte, Planificateur, À propos).
- `output_gtfs/` : Répertoire de stockage des données GTFS brutes et unifiées.

## Installation et Déploiement

### Prérequis
- Python 3.9+
- Pip (gestionnaire de paquets Python)
- Docker (optionnel, pour l'exécution en conteneur)

### Procédure d'installation
1. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
2. Générer les données unifiées (GTFS) :
   ```bash
   python build_gtfs.py
   ```
3. Lancer le serveur de développement :
   ```bash
   python app.py
   ```

### Déploiement Docker
Un `Dockerfile` est fourni pour faciliter le déploiement. L'image expose le port 5000 et exécute automatiquement le chargement des données au démarrage.

## Note
Les données de transport utilisées proviennent de sources ouvertes via data.gouv.fr. L'application est destinée à un usage de visualisation technique et de démonstration de traitement de données géospatiales.
