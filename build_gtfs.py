import pandas as pd
import numpy as np
import requests
import zipfile
import io
import os
import logging
import re
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime, timedelta
import shutil


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)



SOURCES = {
    "flixbus": {
        "url": "https://www.data.gouv.fr/api/1/datasets/r/30d94e83-48a4-4c44-8a96-c082377f5221",
        "prefix": "FLX_",
    },
    "blablacar": {
        "url": "https://www.data.gouv.fr/api/1/datasets/r/fd54f81f-4389-4e73-be75-491133d011c3",
        "prefix": "BLA_",
    }
}

OUTPUT_DIR = "output_gtfs"
UNIFIED_DIR = os.path.join(OUTPUT_DIR, "unified")
MAPPING_DIR = os.path.join(OUTPUT_DIR, "mapping")

MAJOR_CITIES = [
    "Berlin", "Paris", "Londres", "London", "Rome", "Madrid", "Barcelona", "Barcelone", 
    "Munich", "München", "Milan", "Milano", "Amsterdam", "Vienna", "Wien", "Prague", "Praha", 
    "Warsaw", "Warszawa", "Brussels", "Bruxelles", "Budapest", "Lyon", "Marseille", 
    "Toulouse", "Bordeaux", "Lille", "Strasbourg", "Frankfurt", "Francfort", "Hamburg", "Hambourg", 
    "Cologne", "Köln", "Naples", "Napoli", "Turin", "Torino", "Lisbon", "Lisboa", "Porto",
    "Stockholm", "Copenhagen", "Copenhague", "Oslo", "Helsinki", "Zurich", "Zürich", "Geneva", "Genève",
    "Nantes", "Rennes", "Montpellier", "Nice", "Bremen", "Hannover", "Stuttgart", "Leipzig", "Dresden",
    "Krakow", "Kraków", "Sevilla", "Seville", "Valencia", "Valence", "Zaragoza", "Malaga"
]

def clean_display_name(name):
    if not name or not isinstance(name, str):
        return "Itinéraire inconnu"
    name = name.strip()
    if " > " in name:
        parts = [p.strip() for p in name.split(" > ")]
        if len(parts) > 2:
            return f"{parts[0]} > {parts[-1]}"
        return name
    if " - " in name:
        parts = [p.strip() for p in name.split(" - ")]
        if len(parts) > 2:
            return f"{parts[0]} - {parts[-1]}"
        return name
    return name

def get_city_name(stop_name):
    if not stop_name or not isinstance(stop_name, str):
        return "Unknown"
    
    cleaned_name = stop_name.strip()

    separators = [" - ", " (", ", ", " – ", " — ", " | "]
    for sep in separators:
        if sep in cleaned_name:
            cleaned_name = cleaned_name.split(sep)[0].strip()

    lower_name = cleaned_name.lower()
    for city in MAJOR_CITIES:
        lower_city = city.lower()
        if lower_name.startswith(lower_city + " ") or lower_name.startswith(lower_city + "-"):
            return city
        if lower_name == lower_city:
            return city

    suffixes_to_remove = [
        " central bus station", " central station", " bus station", 
        " airport", " aéroport", " aeroport", " hbf", " zob", " p+r",
        " gare routière", " gare", " sud", " nord", " est", " ouest"
    ]
    for suffix in suffixes_to_remove:
        if cleaned_name.lower().endswith(suffix):
            cleaned_name = cleaned_name[:len(cleaned_name)-len(suffix)].strip()
            
    return cleaned_name

def download_and_extract(url, operator_key):
    logger.info(f"Téléchargement de {operator_key}...")
    try:
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        temp_dir = os.path.join(OUTPUT_DIR, f"temp_{operator_key}")
        os.makedirs(temp_dir, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            z.extractall(temp_dir)
        return temp_dir
    except Exception as e:
        logger.error(f"Erreur téléchargement {operator_key}: {e}")
        return None

def load_gtfs_file(path, filename, prefix):
    file_path = os.path.join(path, filename)
    if not os.path.exists(file_path):
        return pd.DataFrame()
    try:
        df = pd.read_csv(file_path, dtype=str, keep_default_na=False, na_values=['', ' '])
    except pd.errors.EmptyDataError:
        return pd.DataFrame()

    id_cols = ['stop_id', 'trip_id', 'route_id', 'agency_id', 'shape_id', 'service_id', 'from_stop_id', 'to_stop_id']
    for col in df.columns:
        if col in id_cols:
            df[col] = df[col].apply(lambda x: f"{prefix}{x}" if pd.notna(x) and x != '' else x)
    return df

def get_valid_services(calendar_df, calendar_dates_df, start_date, end_date):
    valid_services = set()
    
    if not calendar_df.empty:
        for _, row in calendar_df.iterrows():
            svc_id = row.get('service_id')
            start_svc = row.get('start_date')
            end_svc = row.get('end_date')
            
            if not svc_id or not start_svc or not end_svc:
                continue
            try:
                d_start = datetime.strptime(str(start_svc), '%Y%m%d')
                d_end = datetime.strptime(str(end_svc), '%Y%m%d')
                if d_start <= end_date and d_end >= start_date:
                    valid_services.add(svc_id)
            except ValueError:
                continue

    if not calendar_dates_df.empty:
        adds = calendar_dates_df[calendar_dates_df['exception_type'] == '1']
        for _, row in adds.iterrows():
            svc_id = row.get('service_id')
            date_svc = row.get('date')
            if not svc_id or not date_svc:
                continue
            try:
                d_svc = datetime.strptime(str(date_svc), '%Y%m%d')
                if start_date <= d_svc <= end_date:
                    valid_services.add(svc_id)
            except ValueError:
                continue

    return valid_services


def aggregate_by_city_select_flixbus(stops_df):
    logger.info("Étape : Agrégation par ville (Sélection arrêt FlixBus réel)...")
    
    stops_df['city_name'] = stops_df['stop_name'].apply(get_city_name)
    stops_df['lat_num'] = pd.to_numeric(stops_df['stop_lat'], errors='coerce')
    stops_df['lon_num'] = pd.to_numeric(stops_df['stop_lon'], errors='coerce')
    
    stops_df['is_flixbus'] = stops_df['stop_id'].str.startswith('FLX_')
    
    stops_df_sorted = stops_df.sort_values(by='is_flixbus', ascending=False)
    master_stops = stops_df_sorted.drop_duplicates(subset=['city_name'], keep='first').copy()
    
    city_to_master_id = dict(zip(master_stops['city_name'], master_stops['stop_id']))
    stop_to_city = dict(zip(stops_df['stop_id'], stops_df['city_name']))
    
    stop_mapping = {}
    for stop_id, city in stop_to_city.items():
        stop_mapping[stop_id] = city_to_master_id.get(city, stop_id)

    final_stops = master_stops.copy()
    final_stops['stop_name'] = final_stops['city_name']
    final_stops['stop_lat'] = final_stops['lat_num']
    final_stops['stop_lon'] = final_stops['lon_num']
    
    cols_to_keep = ['stop_id', 'stop_name', 'stop_lat', 'stop_lon', 'location_type', 'parent_station']
    for col in cols_to_keep:
        if col not in final_stops.columns:
            final_stops[col] = ''
            
    final_stops = final_stops[cols_to_keep]
    final_stops['location_type'] = '1' 
    
    logger.info(f"Création de {len(final_stops)} villes uniques (points réels).")
    
    return final_stops, stop_mapping

def clean_stop_sequences(stop_times_df, stop_mapping):
    logger.info("Nettoyage des séquences d'arrêts...")
    
    stop_times_df['stop_id'] = stop_times_df['stop_id'].map(stop_mapping).fillna(stop_times_df['stop_id'])
    stop_times_df['stop_sequence'] = pd.to_numeric(stop_times_df['stop_sequence'], errors='coerce')
    stop_times_df = stop_times_df.sort_values(['trip_id', 'stop_sequence'])
    
    stop_times_df['prev_stop_id'] = stop_times_df.groupby('trip_id')['stop_id'].shift(1)
    
    cleaned_df = stop_times_df[
        (stop_times_df['prev_stop_id'] != stop_times_df['stop_id']) | 
        (stop_times_df['prev_stop_id'].isna())
    ].copy()
    
    cleaned_df['stop_sequence'] = cleaned_df.groupby('trip_id').cumcount() + 1
    cleaned_df = cleaned_df.drop(columns=['prev_stop_id'])
    
    logger.info(f"Séquences nettoyées : {len(stop_times_df)} -> {len(cleaned_df)} arrêts.")
    return cleaned_df

def simplify_trips(trips_df, stop_times_df):
    logger.info("Simplification des trajets (Suppression aller-retours)...")
    if stop_times_df.empty or trips_df.empty:
        return trips_df, stop_times_df

    
    stop_times_sorted = stop_times_df.sort_values(['trip_id', 'stop_sequence'])
    trip_signatures = stop_times_sorted.groupby('trip_id')['stop_id'].apply(lambda x: "|".join(x)).reset_index()
    trip_signatures.columns = ['trip_id', 'stop_sequence_signature']
    
    trips_merged = pd.merge(trips_df, trip_signatures, on='trip_id', how='left')
    
    
    def reverse_signature(sig):
        if not sig or not isinstance(sig, str): return ""
        parts = sig.split("|")
        return "|".join(parts[::-1])
    
    trips_merged['reverse_signature'] = trips_merged['stop_sequence_signature'].apply(reverse_signature)
    
    
    
    trips_merged = trips_merged.sort_values('trip_id')
    
    kept_signatures = set()
    indices_to_keep = []
    
    
    for index, row in trips_merged.iterrows():
        sig = row['stop_sequence_signature']
        rev_sig = row['reverse_signature']
        
        
        if sig not in kept_signatures and rev_sig not in kept_signatures:
            kept_signatures.add(sig)
            indices_to_keep.append(index)
            
    unique_trips = trips_merged.loc[indices_to_keep].copy()
    
    
    unique_trips = unique_trips.drop(columns=['stop_sequence_signature', 'reverse_signature'])
    
    logger.info(f"Réduction de {len(trips_df)} trajets à {len(unique_trips)} trajets uniques (1 sens unique).")
    
    valid_trip_ids = unique_trips['trip_id'].unique()
    simplified_stop_times = stop_times_df[stop_times_df['trip_id'].isin(valid_trip_ids)]
    
    return unique_trips, simplified_stop_times



def main():
    logger.info("=== DÉBUT DU PROCESSUS (Suppression Aller-Retours) ===")
    
    os.makedirs(UNIFIED_DIR, exist_ok=True)
    os.makedirs(MAPPING_DIR, exist_ok=True)
    
    all_data = {}
    
    
    start_window = datetime(2026, 2, 1)
    end_window = datetime(2026, 12, 31)
    
    
    for key, config in SOURCES.items():
        temp_dir = download_and_extract(config['url'], key)
        if temp_dir:
            trips = load_gtfs_file(temp_dir, 'trips.txt', config['prefix'])
            routes = load_gtfs_file(temp_dir, 'routes.txt', config['prefix'])
            stops = load_gtfs_file(temp_dir, 'stops.txt', config['prefix'])
            stop_times = load_gtfs_file(temp_dir, 'stop_times.txt', config['prefix'])
            shapes = load_gtfs_file(temp_dir, 'shapes.txt', config['prefix'])
            agency = load_gtfs_file(temp_dir, 'agency.txt', config['prefix'])
            
            calendar = load_gtfs_file(temp_dir, 'calendar.txt', config['prefix'])
            calendar_dates = load_gtfs_file(temp_dir, 'calendar_dates.txt', config['prefix'])
            
            valid_services = get_valid_services(calendar, calendar_dates, start_window, end_window)
            
            initial_count = len(trips)
            if not trips.empty and valid_services:
                trips = trips[trips['service_id'].isin(valid_services)]
                logger.info(f"{key}: {len(trips)} trajets valides sur {initial_count}.")
                valid_trip_ids = trips['trip_id'].unique()
                stop_times = stop_times[stop_times['trip_id'].isin(valid_trip_ids)]
            else:
                logger.warning(f"{key}: Conservation de tous les trajets (pas de filtre date applicable).")
            
            all_data[key] = {
                'stops': stops,
                'trips': trips,
                'routes': routes,
                'stop_times': stop_times,
                'shapes': shapes,
                'agency': agency
            }

    if "flixbus" not in all_data or "blablacar" not in all_data:
        logger.error("Données manquantes. Arrêt.")
        return
    unified_stops = pd.concat([all_data['flixbus']['stops'], all_data['blablacar']['stops']], ignore_index=True)
    unified_stop_times = pd.concat([all_data['flixbus']['stop_times'], all_data['blablacar']['stop_times']], ignore_index=True)

    city_stops, city_mapping = aggregate_by_city_select_flixbus(unified_stops)
    
    unified_trips = pd.concat([all_data['flixbus']['trips'], all_data['blablacar']['trips']], ignore_index=True)
    unified_routes = pd.concat([all_data['flixbus']['routes'], all_data['blablacar']['routes']], ignore_index=True)
    unified_shapes = pd.concat([all_data['flixbus']['shapes'], all_data['blablacar']['shapes']], ignore_index=True)

    
    logger.info("Nettoyage des noms de trajets...")
    bla_trips = unified_trips[unified_trips['trip_id'].str.startswith('BLA_')]
    bla_merge = pd.merge(bla_trips, unified_routes[['route_id', 'route_long_name']], on='route_id', how='left')
    bla_merge['trip_headsign'] = bla_merge['route_long_name'].apply(clean_display_name)
    bla_merge = bla_merge.drop(columns=['route_long_name'])
    
    flix_trips = unified_trips[unified_trips['trip_id'].str.startswith('FLX_')]
    flix_merge = pd.merge(flix_trips, unified_routes[['route_id', 'route_long_name']], on='route_id', how='left')
    flix_merge['trip_headsign'] = flix_merge.apply(lambda r: r['trip_headsign'] if len(str(r['trip_headsign']))>3 else clean_display_name(r['route_long_name']), axis=1)
    flix_merge = flix_merge.drop(columns=['route_long_name'])
    
    unified_trips = pd.concat([flix_merge, bla_merge], ignore_index=True)

    
    final_stop_times = clean_stop_sequences(unified_stop_times, city_mapping)

    
    final_trips, final_stop_times = simplify_trips(unified_trips, final_stop_times)

    
    valid_routes = final_trips['route_id'].unique()
    final_routes = unified_routes[unified_routes['route_id'].isin(valid_routes)]
    
    final_shapes = pd.DataFrame()
    if 'shape_id' in final_trips.columns and not final_trips['shape_id'].dropna().empty:
        valid_shapes = final_trips['shape_id'].dropna().unique()
        final_shapes = unified_shapes[unified_shapes['shape_id'].isin(valid_shapes)]

    final_agency = pd.concat([all_data['flixbus']['agency'].head(1), all_data['blablacar']['agency'].head(1)], ignore_index=True)

    
    logger.info(f"Écriture finale...")
    
    files_to_save = {
        'agency.txt': final_agency,
        'stops.txt': city_stops, 
        'routes.txt': final_routes,
        'trips.txt': final_trips,
        'stop_times.txt': final_stop_times,
        'shapes.txt': final_shapes
    }
    
    for fname, df in files_to_save.items():
        path = os.path.join(UNIFIED_DIR, fname)
        df.to_csv(path, index=False)
        
    logger.info("=== TERMINÉ ===")

    logger.info("Création de l'archive ZIP pour le téléchargement...")
    try:
        
        static_downloads_dir = os.path.join("static", "downloads")
        os.makedirs(static_downloads_dir, exist_ok=True)
        zip_path = os.path.join(static_downloads_dir, "gtfs_unifie")
        
        
        if os.path.exists(zip_path + ".zip"):
            os.remove(zip_path + ".zip")
            
        
        shutil.make_archive(zip_path, 'zip', UNIFIED_DIR)
        logger.info(f"Archive créée : {zip_path}.zip")
        
    except Exception as e:
        logger.error(f"Erreur lors de la création du ZIP : {e}")

if __name__ == "__main__":
    main()
