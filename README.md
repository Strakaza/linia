# Linia

Linia est une application web de visualisation et de planification de trajets de bus longue distance. Elle agrège les données de transport (GTFS) de plusieurs opérateurs pour offrir une vue consolidée du réseau de transport interurbain européen.

L'application permet d'explorer les lignes sur une carte interactive, de rechercher des itinéraires et de télécharger le jeu de données unifié généré par le pipeline de traitement.

---

## Fonctionnalités

*   **Visualisation Cartographique** : Affichage des lignes de bus et des arrêts sur une carte interactive (Leaflet).
*   **Recherche et Planification** : Recherche d'arrêts par nom (gestion des synonymes) et visualisation des connexions directes entre villes.
*   **Agrégation Multi-opérateurs** : Fusion des réseaux FlixBus et BlaBlaCar Bus en un seul graphe cohérent.
*   **Unification des Arrêts** : Regroupement des arrêts physiques par ville (*Master Stops*) pour simplifier la lecture du réseau.
*   **Multilingue** : Interface traduite en plusieurs langues avec gestion des slugs SEO localisés.
*   **Export de Données** : Téléchargement d'une archive GTFS unifiée au format ZIP.

---

## Architecture Technique

### Stack Technique
*   **Backend** : Python, Flask.
*   **Base de Données** : SQLite (stockage et requête des données GTFS).
*   **Frontend** : HTML5, CSS3, JavaScript (Vanilla), Leaflet.
*   **Traitement de Données** : Pandas, NumPy.

### Pipeline de Données (`build_gtfs.py`)
Le script `build_gtfs.py` assure la collecte, le nettoyage et l'unification des données :

1.  **Téléchargement** : Récupération des flux GTFS depuis `data.gouv.fr`.
3.  **Agrégation par Ville** : Les arrêts physiques sont regroupés sous un identifiant de ville unique pour éviter la redondance.
4.  **Simplification** : Suppression des trajets aller-retour redondants pour alléger le modèle de données.
5.  **Génération** : Création des fichiers GTFS unifiés (CSV), de la base de données SQLite et de l'archive ZIP de téléchargement.

### Serveur et Routes (`app.py`)
L'application repose sur Flask pour servir l'interface et une API REST :

*   **Routes SEO** : Génération de pages dynamiques pour les villes principales (`/bus/paris`, `/bus/berlin`) avec balisage Schema.org, sitemaps et balises `hreflang`.
*   **API** : Endpoints pour la recherche d'arrêts (`/api/search_stops`), les détails des trajets (`/api/trip_details`) et les connexions (`/api/connected_stops`).

---

## Installation et Lancement

### Prérequis
*   Python 3.9+
*   Pip

### Installation Locale

1.  **Cloner le dépôt** :
    ```bash
    git clone https://github.com/votre-utilisateur/linia.git
    cd linia
    ```

2.  **Installer les dépendances** :
    ```bash
    pip install -r requirements.txt
    ```

3.  **Générer les données** (Nécessite un accès internet pour télécharger les GTFS) :
    ```bash
    python build_gtfs.py
    ```

4.  **Lancer l'application** :
    ```bash
    python app.py
    ```
    L'application est accessible par défaut à l'adresse `http://0.0.0.0:5000`.

### Déploiement Docker

L'application peut être conteneurisée via le `Dockerfile` fourni.

```bash
docker build -t linia-app .
docker run -p 5000:5000 linia-app
```

---

## Configuration

La configuration principale se trouve dans `config_data.py` :

*   `TOP_HUBS` : Liste des villes majeures avec leurs identifiants et slugs traduits.
*   `SUPPORTED_LANGS` : Liste des langues supportées.
*   `SEARCH_SYNONYMS` : Dictionnaire pour normaliser les noms de villes lors de la recherche (ex: "Köln" -> "Cologne").

---

## Sources des Données

Les données de transport proviennent de sources ouvertes :

*   **FlixBus** : Via data.gouv.fr
*   **BlaBlaCar Bus** : Via data.gouv.fr
```