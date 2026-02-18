import pandas as pd
import os
import logging
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import traceback

GTFS_DATA_PATH = os.path.join("output_gtfs", "unified")

app = Flask(__name__)
CORS(app)

log_level_str = os.environ.get('LOG_LEVEL', 'INFO').upper()
log_level = getattr(logging, log_level_str, logging.INFO)
app.logger.setLevel(log_level)

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

@app.before_request
def log_request_info():
    app.logger.info(
        f"Requête reçue: [ANONYME] [{request.method}] {request.url}"
    )

data_frames = {}

def get_operator_from_id(item_id): 
    if pd.isna(item_id) or not isinstance(item_id, str): return "unknown"
    if item_id.startswith("FLX-"): return "flixbus"
    if item_id.startswith("BLA-"): return "blablacar_bus"
    if item_id.startswith("FLX_"): return "flixbus"
    if item_id.startswith("BLA_"): return "blablacar_bus"
    return "unknown"

def load_gtfs_data(): 
    global data_frames
    files_to_load = {
        "stops": "stops.txt", "stop_times": "stop_times.txt",
        "trips": "trips.txt", "routes": "routes.txt",
        "shapes": "shapes.txt", 
        "agency": "agency.txt"
    }
    all_loaded_successfully = True
    essential_files_loaded = True
    app.logger.info("== DÉBUT DU CHARGEMENT DE TOUTES LES DONNÉES GTFS  ==")

    for key, filename in files_to_load.items():
        file_path = os.path.join(GTFS_DATA_PATH, filename)
        app.logger.info(f"Tentative de chargement de : {key} depuis {file_path}")
        try:
            if key == "shapes" and not os.path.exists(file_path):
                app.logger.warning(f"AVERTISSEMENT: Le fichier shapes.txt ({file_path}) n'existe pas. DataFrame vide créé.")
                data_frames[key] = pd.DataFrame() 
                all_loaded_successfully = False 
                continue 

            df = pd.read_csv(file_path, dtype=str, keep_default_na=False, na_values=['', ' '])
            
            if key == "stops":
                for col in ['stop_lat', 'stop_lon']: df[col] = pd.to_numeric(df[col], errors='coerce')
                for col_int_opt in ['location_type', 'wheelchair_boarding']: 
                    if col_int_opt in df.columns: df[col_int_opt] = pd.to_numeric(df[col_int_opt], errors='coerce').fillna(0).astype(int)
            elif key == "stop_times":
                if 'stop_sequence' in df.columns: df['stop_sequence'] = pd.to_numeric(df['stop_sequence'], errors='coerce').fillna(0).astype(int)
                for col_int_opt in ['pickup_type', 'drop_off_type', 'timepoint']:
                    if col_int_opt in df.columns: df[col_int_opt] = pd.to_numeric(df[col_int_opt], errors='coerce').fillna(0).astype(int)
                if 'shape_dist_traveled' in df.columns: df['shape_dist_traveled'] = pd.to_numeric(df['shape_dist_traveled'], errors='coerce')
            elif key == "shapes": 
                if 'shape_pt_sequence' in df.columns: df['shape_pt_sequence'] = pd.to_numeric(df['shape_pt_sequence'], errors='coerce').fillna(0).astype(int)
                for col_num in ['shape_pt_lat', 'shape_pt_lon', 'shape_dist_traveled']:
                    if col_num in df.columns: df[col_num] = pd.to_numeric(df[col_num], errors='coerce')
            
            data_frames[key] = df
            app.logger.info(f"Chargé avec succès : {filename} ({len(data_frames[key])} lignes)")

        except FileNotFoundError:
            app.logger.error(f"ERREUR (FileNotFoundError) pour {filename}: Fichier non trouvé.")
            data_frames[key] = pd.DataFrame() 
            all_loaded_successfully = False
            if key != "shapes": 
                essential_files_loaded = False
        except Exception as e:
            app.logger.error(f"ERREUR (Exception) lors du chargement de {filename}: {e}")
            app.logger.error(traceback.format_exc())
            data_frames[key] = pd.DataFrame() 
            all_loaded_successfully = False
            if key != "shapes":
                essential_files_loaded = False

    app.logger.info("== FIN DU CHARGEMENT DE TOUTES LES DONNÉES GTFS (y compris shapes.txt) ==")
    if not essential_files_loaded: 
        app.logger.critical("CRITIQUE: Au moins un fichier GTFS essentiel (non-shapes) est manquant ou a échoué au chargement.")
    elif not all_loaded_successfully:
        app.logger.warning("AVERTISSEMENT: Au moins un fichier GTFS (probablement shapes.txt) n'a pas pu être chargé.")
    else:
        app.logger.info("Tous les fichiers GTFS ont été chargés avec succès.")
        
    return essential_files_loaded

app.logger.info("APPEL GLOBAL DE load_gtfs_data() au démarrage de l'application...")
load_gtfs_data() 
app.logger.info("Fin de l'appel global à load_gtfs_data(). L'application continue son initialisation.")

def get_stop_info_and_routes(stop_id_input):
    required_dfs = ["stops", "stop_times", "trips", "routes"]
    if not all(key in data_frames and data_frames[key] is not None and not data_frames[key].empty for key in required_dfs):
        app.logger.error("ERREUR get_stop_info_and_routes: Données GTFS de base non chargées ou vides.")
        return {"error": "Les données GTFS de base ne sont pas chargées."}
    
    stops_df, stop_times_df, trips_df, routes_df = (data_frames[k] for k in required_dfs)
    stop_info_series = stops_df[stops_df['stop_id'] == str(stop_id_input)]
    if stop_info_series.empty: return {"error": f"L'arrêt avec l'ID '{stop_id_input}' n'a pas été trouvé."}
    
    stop_record = stop_info_series.iloc[0]
    stop_details = {
        "stop_id": stop_record['stop_id'], 
        "stop_name": stop_record.get('stop_name', ''), 
        "stop_lat": stop_record['stop_lat'], 
        "stop_lon": stop_record['stop_lon']
    }
    
    relevant_stop_times = stop_times_df[stop_times_df['stop_id'] == str(stop_id_input)]
    if relevant_stop_times.empty: 
        return { "stop_info": stop_details, "routes": [], "message": "Aucun itinéraire pour cet arrêt." }
        
    unique_trip_ids = relevant_stop_times['trip_id'].unique()
    relevant_trips = trips_df[trips_df['trip_id'].isin(unique_trip_ids)]
    if relevant_trips.empty:
        return { "stop_info": stop_details, "routes": [], "message": "Aucun voyage correspondant aux horaires pour cet arrêt." }

    merged_trips_routes = pd.merge(relevant_trips, routes_df, on='route_id', how='left')
    if merged_trips_routes.empty:
         return { "stop_info": stop_details, "routes": [], "message": "Impossible de joindre les voyages et les routes." }

    cols_to_clean_for_str = ['trip_headsign', 'route_long_name', 'route_short_name']
    for col in cols_to_clean_for_str:
        if col in merged_trips_routes.columns: 
            merged_trips_routes[col] = merged_trips_routes[col].fillna('')
        else: 
            merged_trips_routes[col] = ''
            
    merged_trips_routes['operator'] = merged_trips_routes['route_id'].apply(get_operator_from_id)
    merged_trips_routes['display_name'] = merged_trips_routes.apply(
        lambda row: row['trip_headsign'] if row['trip_headsign'] != '' else row['route_long_name'], axis=1
    )
    merged_trips_routes['display_name'] = merged_trips_routes.apply(
        lambda row: row['display_name'] if row['display_name'] != '' else row.get('route_short_name', 'Itinéraire sans nom'), axis=1
    )
    merged_trips_routes['display_name'] = merged_trips_routes['display_name'].replace('', 'Itinéraire sans nom')
    
    unique_display_routes = merged_trips_routes.drop_duplicates(subset=['route_id', 'display_name', 'operator'])
    
    passing_routes = []
    for _, row in unique_display_routes.iterrows():
        passing_routes.append({
            "trip_id": row['trip_id'], "route_id": row['route_id'],
            "trip_headsign": row.get('trip_headsign', ''), 
            "route_long_name": row.get('route_long_name', ''),
            "display_name": row['display_name'], 
            "operator": row['operator'],
        })
        
    return { "stop_info": stop_details, "routes": passing_routes }

def get_trip_details_and_shape(trip_id_input):
    required_dfs = ["stops", "stop_times", "trips"]
    if not all(key in data_frames and data_frames[key] is not None and not data_frames[key].empty for key in required_dfs):
        app.logger.error("ERREUR get_trip_details_and_shape: Données GTFS de base pour détails voyage non chargées ou vides.")
        return {"error": "Données GTFS de base pour détails voyage non chargées."}

    stops_df, stop_times_df, trips_df = (data_frames[k] for k in required_dfs)
    shapes_df = data_frames.get("shapes", pd.DataFrame())
    
    trip_info = trips_df[trips_df['trip_id'] == str(trip_id_input)]
    if trip_info.empty: return {"error": f"Voyage ID '{trip_id_input}' non trouvé."}
    
    operator = get_operator_from_id(trip_id_input)
    shape_id_val = trip_info.iloc[0].get('shape_id')
    shape_id = shape_id_val if pd.notna(shape_id_val) and shape_id_val != '' else None
    
    trip_stop_times = stop_times_df[stop_times_df['trip_id'] == str(trip_id_input)]
    ordered_stops = []
    if not trip_stop_times.empty:
        trip_stops_details = pd.merge(trip_stop_times, stops_df, on='stop_id', how='inner')
        if not trip_stops_details.empty:
            trip_stops_details = trip_stops_details.sort_values(by='stop_sequence')
            for _, row_sd in trip_stops_details.iterrows():
                ordered_stops.append({ 
                    "stop_id": row_sd['stop_id'], "stop_name": row_sd.get('stop_name', ''),
                    "stop_lat": row_sd['stop_lat'], "stop_lon": row_sd['stop_lon'],
                    "stop_sequence": int(row_sd['stop_sequence']) if pd.notna(row_sd['stop_sequence']) and row_sd['stop_sequence']!='' else 0
                })
                
    trip_shape_points = []
    if shape_id and shapes_df is not None and not shapes_df.empty: 
        shape_data = shapes_df[shapes_df['shape_id'] == str(shape_id)]
        if not shape_data.empty:
            shape_data = shape_data.sort_values(by='shape_pt_sequence')
            for _, row_sh in shape_data.iterrows():
                trip_shape_points.append([row_sh['shape_pt_lat'], row_sh['shape_pt_lon']])
                
    return {"trip_id": trip_id_input, "stops": ordered_stops, "shape_points": trip_shape_points, "operator": operator}

@app.route('/')
def index():
    app.logger.debug(f"Requête pour la page d'accueil depuis {request.remote_addr}")
    return render_template('landing.html')

@app.route('/map')
def map_page():
    app.logger.debug(f"Requête pour la page carte depuis {request.remote_addr}")
    return render_template('map.html')

@app.route('/about')
def about_page():
    app.logger.debug(f"Requête pour la page à propos depuis {request.remote_addr}")
    return render_template('about.html')

@app.route('/planner')
def planner_page():
    app.logger.debug(f"Requête pour la page planificateur depuis {request.remote_addr}")
    return render_template('planner.html')

@app.route('/download/gtfs_unifie')
def download_unified_gtfs():
    try:
        static_downloads_path = os.path.join(app.root_path, app.static_folder, 'downloads')
        zip_filename = 'gtfs_unifie.zip' 
        app.logger.info(f"Tentative de téléchargement de {zip_filename} depuis {static_downloads_path} par {request.remote_addr}")
        return send_from_directory(static_downloads_path, zip_filename, as_attachment=True)
    except FileNotFoundError:
        app.logger.error(f"Fichier {zip_filename} non trouvé dans {static_downloads_path} pour téléchargement demandé par {request.remote_addr}")
        return jsonify({"error": "Fichier GTFS unifié non trouvé."}), 404
    except Exception as e:
        app.logger.error(f"Erreur lors du téléchargement du fichier GTFS par {request.remote_addr}: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Erreur interne du serveur lors du téléchargement."}), 500

@app.route('/api/search_stops', methods=['GET'])
def api_search_stops():
    query_term = request.args.get('query', default='', type=str).strip()
    
    if not query_term or len(query_term) < 2: 
        return jsonify([]), 200
        
    if "stops" not in data_frames or data_frames["stops"] is None or data_frames["stops"].empty:
        app.logger.error("ERREUR API /api/search_stops: data_frames['stops'] non chargé ou vide.")
        return jsonify({"error": "Les données des arrêts ne sont pas chargées ou sont vides."}), 500
        
    stops_df = data_frames["stops"]
    try:
        if 'stop_name' not in stops_df.columns:
            app.logger.error("ERREUR API /api/search_stops: Colonne 'stop_name' manquante dans stops_df.")
            return jsonify({"error": "Données d'arrêt malformées (colonne manquante)."}), 500
            
        matching_stops = stops_df[
            stops_df['stop_name'].astype(str).str.contains(query_term, case=False, na=False, regex=False)
        ]
    except Exception as e:
        app.logger.error(f"Erreur interne lors de la recherche d'arrêts pour query='{query_term}': {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Erreur interne lors de la recherche d'arrêts."}), 500
        
    results = [{"stop_id": row['stop_id'], "stop_name": row['stop_name']} for _, row in matching_stops.head(10).iterrows()]
    app.logger.debug(f"API /api/search_stops - Résultats pour '{query_term}': {len(results)} trouvés.")
    return jsonify(results)

@app.route('/api/stop_info/<stop_id>', methods=['GET'])
def api_get_stop_info(stop_id):
    try:
        data = get_stop_info_and_routes(stop_id)
        if "error" in data:
            status = 404 if "non trouvé" in data["error"].lower() else 500
            app.logger.warning(f"API /api/stop_info - Erreur pour stop_id {stop_id}: {data['error']} (status {status})")
            return jsonify(data), status
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"Erreur majeure inattendue dans /api/stop_info/{stop_id}: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Erreur serveur inattendue."}), 500

@app.route('/api/trip_details/<trip_id>', methods=['GET'])
def api_get_trip_details(trip_id):
    try:
        data = get_trip_details_and_shape(trip_id)
        if "error" in data:
            status = 404 if "non trouvé" in data["error"].lower() else 500
            app.logger.warning(f"API /api/trip_details - Erreur pour trip_id {trip_id}: {data['error']} (status {status})")
            return jsonify(data), status
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"Erreur majeure inattendue dans /api/trip_details/{trip_id}: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Erreur serveur inattendue."}), 500

@app.route('/api/connected_stops/<stop_id>', methods=['GET'])
def api_get_connected_stops(stop_id):
    required_dfs = ["stops", "stop_times", "trips"]
    if not all(key in data_frames and data_frames[key] is not None and not data_frames[key].empty for key in required_dfs):
        app.logger.error("ERREUR api_get_connected_stops: Données GTFS non chargées.")
        return jsonify({"error": "Données GTFS non chargées."}), 500

    stops_df = data_frames["stops"]
    stop_times_df = data_frames["stop_times"]
    trips_df = data_frames["trips"]

    stop_exists = stops_df[stops_df['stop_id'] == str(stop_id)]
    if stop_exists.empty:
        return jsonify({"error": f"Arrêt '{stop_id}' non trouvé."}), 404

    try:
        trips_through_stop = stop_times_df[stop_times_df['stop_id'] == str(stop_id)]['trip_id'].unique()

        if len(trips_through_stop) == 0:
            return jsonify([])

        relevant_trips = trips_df[trips_df['trip_id'].isin(trips_through_stop)][['trip_id', 'route_id']].copy()
        relevant_trips['operator'] = relevant_trips['route_id'].apply(get_operator_from_id)

        all_stop_times_for_trips = stop_times_df[stop_times_df['trip_id'].isin(trips_through_stop)][['trip_id', 'stop_id']]
        all_stop_times_for_trips = all_stop_times_for_trips[all_stop_times_for_trips['stop_id'] != str(stop_id)]

        if all_stop_times_for_trips.empty:
            return jsonify([])

        stop_with_operator = pd.merge(all_stop_times_for_trips, relevant_trips[['trip_id', 'operator']], on='trip_id', how='left')
        stop_with_operator = stop_with_operator[stop_with_operator['operator'].notna()]
        stop_with_operator = stop_with_operator[~stop_with_operator['operator'].isin(['unknown', 'NaN', 'nan'])]

        stop_operators = stop_with_operator.groupby('stop_id')['operator'].apply(lambda x: sorted(set(x))).reset_index()
        stop_operators.columns = ['stop_id', 'operators']

        connected_stops = pd.merge(stop_operators, stops_df, on='stop_id', how='inner')
        connected_stops = connected_stops.drop_duplicates(subset=['stop_name'])
        connected_stops = connected_stops.sort_values(by='stop_name')

        results = []
        for _, row in connected_stops.iterrows():
            operators = [op for op in row['operators'] if op not in ('unknown', 'NaN', 'nan')]
            if not operators:
                operators = ['flixbus'] 
            results.append({
                "stop_id": row['stop_id'],
                "stop_name": row.get('stop_name', ''),
                "stop_lat": float(row['stop_lat']) if pd.notna(row['stop_lat']) else None,
                "stop_lon": float(row['stop_lon']) if pd.notna(row['stop_lon']) else None,
                "operators": operators
            })

        app.logger.debug(f"API /api/connected_stops/{stop_id}: {len(results)} villes connectées trouvées.")
        return jsonify(results)

    except Exception as e:
        app.logger.error(f"Erreur dans /api/connected_stops/{stop_id}: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Erreur interne."}), 500

if __name__ == "__main__":
    app.logger.info("--- DÉMARRAGE EN MODE DÉVELOPPEMENT LOCAL ---")
    app.logger.info(f"Niveau de log actuel : {logging.getLevelName(app.logger.getEffectiveLevel())}")
    app.logger.info(f"Lancement du serveur de développement Flask sur http://0.0.0.0:{os.environ.get('PORT', 5000)}")
    app.logger.warning("ATTENTION : Ce serveur est pour le DÉVELOPPEMENT uniquement. NE PAS UTILISER EN PRODUCTION avec le serveur de dev Flask.")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))