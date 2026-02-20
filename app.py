import pandas as pd
import os
import sqlite3
import logging
import json
from flask import Flask, jsonify, render_template, request, send_from_directory, redirect, url_for, Response, abort
from flask_cors import CORS
from flask_talisman import Talisman
from flask_caching import Cache
from werkzeug.middleware.proxy_fix import ProxyFix
import traceback
from contextlib import closing

try:
    with open('translations.json', 'r', encoding='utf-8') as f:
        TRANSLATIONS = json.load(f)
except Exception as e:
    print(f"Erreur de chargement du fichier de traduction JSON: {e}")
    TRANSLATIONS = {"fr": {}}

GTFS_DATA_PATH = os.path.join("output_gtfs", "unified")

from config_data import TOP_HUBS, BASE_URL, SUPPORTED_LANGS, DEFAULT_LANG, OG_LOCALES, URL_SLUGS, SEARCH_SYNONYMS, SEO_CONFIG


def find_city_by_slug(slug_input):
    slug_input = slug_input.lower()
    for internal_key, data in TOP_HUBS.items():
        slugs = data.get("slugs", {})
        if slug_input in slugs.values() or slug_input == internal_key:
            return internal_key, data
    return None, None

def get_translated_slug(page_key: str, lang: str) -> str:
    if page_key in URL_SLUGS:
        return URL_SLUGS[page_key].get(lang, URL_SLUGS[page_key].get("en", page_key))
    return page_key

def normalize_lang(lang_code: str | None) -> str:
    if not lang_code:
        return DEFAULT_LANG
    lang_code = lang_code.lower()
    return lang_code if lang_code in SUPPORTED_LANGS else DEFAULT_LANG

def build_lang_urls(page_key: str, path_slug: str | None = None) -> dict:
    urls = {}

    is_city_page = (page_key == "city")
    city_data = None
    if is_city_page and path_slug:
        city_data = TOP_HUBS.get(path_slug)

    for lang in SUPPORTED_LANGS:
        current_slug = None

        if is_city_page and city_data:
            local_slug = city_data["slugs"].get(lang, city_data["slugs"].get("default"))
            current_slug = f"bus/{local_slug}"

        elif path_slug is not None and not is_city_page:
            current_slug = path_slug

        else:
            current_slug = get_translated_slug(page_key, lang)

        prefix = f"{BASE_URL}"
        if lang != "fr":
            prefix += f"/{lang}"

        if current_slug and current_slug != "home":
            urls[lang] = f"{prefix}/{current_slug}"
        else:
            urls[lang] = f"{prefix}/"

    urls["x-default"] = BASE_URL + "/"
    return urls


def get_seo_meta(page_key: str, lang: str, path_slug: str | None = None) -> dict:
    lang = normalize_lang(lang)
    page_conf = SEO_CONFIG.get(page_key, {})
    lang_conf = page_conf.get(lang) or page_conf.get(DEFAULT_LANG, {})

    lang_urls = build_lang_urls(page_key, path_slug=path_slug)
    current_url = lang_urls.get(lang, BASE_URL + "/")

    title = lang_conf.get("title", "Linia")
    description = lang_conf.get("description", "Linia - Visualisation et planification de lignes de bus longue distance en Europe.")

    og_locale = OG_LOCALES.get(lang, OG_LOCALES.get(DEFAULT_LANG))
    og_locale_alternates = [OG_LOCALES[l] for l in SUPPORTED_LANGS if l in OG_LOCALES and l != lang]

    return {
        "page_title": title,
        "page_description": description,
        "canonical_url": current_url,
        "og_title": title,
        "og_description": description,
        "og_url": current_url,
        "og_locale": og_locale,
        "og_locale_alternates": og_locale_alternates,
        "hreflang_urls": lang_urls,
    }


def get_structured_data(page_key: str, lang: str, current_url: str) -> str | None:
    data = []

    if page_key == "home":
        data.append({"@context": "https://schema.org", "@type": "Organization", "name": "Linia", "url": BASE_URL + "/", "logo": BASE_URL + "/static/logo.png"})
        data.append({
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "Linia - Bus Route Planner",
            "url": BASE_URL + "/",
            "potentialAction": {
                "@type": "SearchAction",
                "target": BASE_URL + "/" + get_translated_slug("planner", lang) + "?q={search_term_string}",
                "query-input": "required name=search_term_string",
            },
        })

    if page_key == "planner":
        data.append({
            "@context": "https://schema.org", "@type": "Trip", "name": "European bus itinerary planner",
            "description": "Interactive tool to plan multi-step bus itineraries across Europe using FlixBus and BlaBlaCar routes.",
            "url": current_url, "provider": {"@type": "Organization", "name": "Linia", "url": BASE_URL + "/"},
            "areaServed": {"@type": "AdministrativeArea", "name": "Europe"},
        })

    if page_key == "about" and lang == "fr":
        data.append({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": "Linia est-il gratuit ?", "acceptedAnswer": {"@type": "Answer", "text": "Oui, l'outil est entièrement gratuit et sans publicité."}},
                {"@type": "Question", "name": "Quels sont les pays couverts par Linia ?", "acceptedAnswer": {"@type": "Answer", "text": "Linia couvre principalement l'Europe : France, Allemagne, Espagne, Italie, Benelux, et d'autres pays européens desservis par FlixBus et BlaBlaCar Bus."}},
                {"@type": "Question", "name": "À quelle fréquence les données sont-elles mises à jour ?", "acceptedAnswer": {"@type": "Answer", "text": "Les données GTFS sont mises à jour le premier jour de chaque mois."}},
                {"@type": "Question", "name": "Comment signaler une erreur ou proposer une amélioration ?", "acceptedAnswer": {"@type": "Answer", "text": "Vous pouvez ouvrir une issue sur le dépôt GitHub du projet ou contacter le développeur via contact@liniabus.eu"}},
            ],
        })

    if page_key in {"home", "map", "planner", "about", "legal"}:
        items = [{"@type": "ListItem", "position": 1, "name": "Linia", "item": BASE_URL + "/"}]
        if page_key != "home":
            name_map = {"map": "Map", "planner": "Planner", "about": "About", "legal": "Legal"}
            items.append({"@type": "ListItem", "position": 2, "name": name_map.get(page_key, page_key.title()), "item": current_url})
        data.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items})

    if not data: return None
    try: return json.dumps(data, ensure_ascii=False)
    except Exception: return None


app = Flask(__name__)
CORS(app)

csp = {
    'default-src': "'self'",
    'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", "https://api.mapbox.com", "https://cdn.jsdelivr.net", "https://unpkg.com"],
    'style-src': ["'self'", "'unsafe-inline'", "https://api.mapbox.com", "https://fonts.googleapis.com", "https://cdn.jsdelivr.net", "https://unpkg.com"],
    'img-src': ["'self'", "data:", "blob:", "https://*.mapbox.com", "https://liniabus.eu", "https://*.tile.openstreetmap.org", "https://*.basemaps.cartocdn.com"],
    'font-src': ["'self'", "https://fonts.gstatic.com", "https://cdn.jsdelivr.net"],
    'connect-src': ["'self'", "https://api.mapbox.com", "https://events.mapbox.com", "https://unpkg.com", "https://router.project-osrm.org"],
    'worker-src': ["'self'", "blob:"],
    'child-src': ["'self'", "blob:"],
}
Talisman(app, content_security_policy=csp, force_https=False)

cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 3600})

log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)
app.logger.setLevel(log_level)

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

@app.before_request
def log_request_info():
    app.logger.info(f"Requête reçue: [ANONYME] [{request.method}] {request.url}")

def get_operator_from_id(item_id):
    if item_id is None or not isinstance(item_id, str): return "unknown"
    if item_id.startswith("FLX-"): return "flixbus"
    if item_id.startswith("BLA-"): return "blablacar_bus"
    if item_id.startswith("FLX_"): return "flixbus"
    if item_id.startswith("BLA_"): return "blablacar_bus"
    return "unknown"

def get_db():
    db_path = os.path.join(GTFS_DATA_PATH, "gtfs.sqlite")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn





def get_stop_info_and_routes(stop_id_input):
    try:
        with closing(get_db()) as conn:
            stop_row = conn.execute(
                "SELECT stop_id, stop_name, stop_lat, stop_lon FROM stops WHERE stop_id = ?",
                (str(stop_id_input),)
            ).fetchone()

            if not stop_row:
                return {"error": f"L'arrêt avec l'ID '{stop_id_input}' n'a pas été trouvé."}

            stop_details = {
                "stop_id": stop_row['stop_id'],
                "stop_name": stop_row['stop_name'] or '',
                "stop_lat": stop_row['stop_lat'],
                "stop_lon": stop_row['stop_lon']
            }

            query = """
                SELECT DISTINCT
                    t.trip_id,
                    t.route_id,
                    t.trip_headsign,
                    r.route_long_name,
                    r.route_short_name
                FROM stop_times st
                JOIN trips t ON st.trip_id = t.trip_id
                JOIN routes r ON t.route_id = r.route_id
                WHERE st.stop_id = ?
            """

            routes_cursor = conn.execute(query, (str(stop_id_input),))
            passing_routes = []
            seen_routes = set()

            for row in routes_cursor:
                trip_headsign = row['trip_headsign'] or ''
                route_long_name = row['route_long_name'] or ''
                route_short_name = row['route_short_name'] or ''
                route_id = row['route_id']

                operator = get_operator_from_id(route_id)
                display_name = trip_headsign if trip_headsign else route_long_name
                display_name = display_name if display_name else (route_short_name or 'Itinéraire sans nom')

                uniq_key = (route_id, display_name, operator)
                if uniq_key not in seen_routes:
                    seen_routes.add(uniq_key)
                    passing_routes.append({
                        "trip_id": row['trip_id'],
                        "route_id": route_id,
                        "trip_headsign": trip_headsign,
                        "route_long_name": route_long_name,
                        "display_name": display_name,
                        "operator": operator
                    })

            if not passing_routes:
                return { "stop_info": stop_details, "routes": [], "message": "Aucun itinéraire pour cet arrêt." }

            return { "stop_info": stop_details, "routes": passing_routes }

    except Exception as e:
        app.logger.error(f"SQL Error in get_stop_info_and_routes: {e}")
        return {"error": "Erreur serveur lors de la récupération des données GTFS."}

def get_trip_details_and_shape(trip_id_input):
    try:
        with closing(get_db()) as conn:
            trip_row = conn.execute(
                "SELECT trip_id, shape_id FROM trips WHERE trip_id = ?",
                (str(trip_id_input),)
            ).fetchone()

            if not trip_row:
                return {"error": f"Voyage non trouvé."}

            shape_id = trip_row['shape_id']
            operator = get_operator_from_id(str(trip_id_input))

            stops_query = """
                SELECT
                    s.stop_id,
                    s.stop_name,
                    s.stop_lat,
                    s.stop_lon,
                    st.stop_sequence
                FROM stop_times st
                JOIN stops s ON st.stop_id = s.stop_id
                WHERE st.trip_id = ?
                ORDER BY CAST(st.stop_sequence AS INTEGER)
            """

            ordered_stops = []
            for row in conn.execute(stops_query, (str(trip_id_input),)):
                ordered_stops.append({
                    "stop_id": row['stop_id'],
                    "stop_name": row['stop_name'] or '',
                    "stop_lat": row['stop_lat'],
                    "stop_lon": row['stop_lon'],
                    "stop_sequence": int(row['stop_sequence']) if row['stop_sequence'] else 0
                })

            trip_shape_points = []
            if shape_id:
                shape_query = """
                    SELECT shape_pt_lat, shape_pt_lon
                    FROM shapes
                    WHERE shape_id = ?
                    ORDER BY CAST(shape_pt_sequence AS INTEGER)
                """
                for row in conn.execute(shape_query, (str(shape_id),)):
                    trip_shape_points.append([row['shape_pt_lat'], row['shape_pt_lon']])

            return {
                "trip_id": trip_id_input,
                "stops": ordered_stops,
                "shape_points": trip_shape_points,
                "operator": operator
            }
    except Exception as e:
        app.logger.error(f"SQL Error in get_trip_details_and_shape: {e}")
        return {"error": "Erreur serveur lors de la récupération des données de voyage."}

def simple_slugify(text):
    text = str(text).lower()
    text = text.replace('é', 'e').replace('è', 'e').replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
    return text.replace(' ', '-').replace("'", "-")

def try_find_stop_by_slug(slug):

    try:
        with closing(get_db()) as conn:
            cursor = conn.execute("SELECT stop_id, stop_name FROM stops")
            for row in cursor:
                if simple_slugify(row['stop_name']) == slug:
                    return {
                        "id": row['stop_id'],
                        "name": row['stop_name'],
                        "slugs": {"default": slug}
                    }
    except Exception as e:
        app.logger.error(f"Erreur recherche dynamique slug: {e}")

    return None


def _render_page(page_key: str, lang_code: str | None, template_name: str, path_slug: str | None = None, **kwargs):
    current_lang = normalize_lang(lang_code)

    if "seo_meta_override" in kwargs:
        seo_meta = kwargs.pop("seo_meta_override")
        structured_jsonld = None
    else:
        seo_meta = get_seo_meta(page_key, current_lang, path_slug=path_slug)
        structured_jsonld = get_structured_data(
            page_key, current_lang, seo_meta.get("canonical_url", BASE_URL + "/")
        )

    def translate(key, **t_kwargs):
        dict_lang = TRANSLATIONS.get(current_lang, TRANSLATIONS.get('fr', {}))

        if 'count' in t_kwargs:
            count = t_kwargs['count']
            plural_key = f"{key}_one" if count == 1 else f"{key}_other"
            if plural_key in dict_lang:
                key = plural_key

        text = dict_lang.get(key, key)

        for k, v in t_kwargs.items():
            text = text.replace(f"{{{k}}}", str(v))
        return text

    def get_url(page_key_target):
        if page_key_target == "home":
            return "/" if current_lang == "fr" else f"/{current_lang}/"
        slug = get_translated_slug(page_key_target, current_lang)
        return f"/{slug}" if current_lang == "fr" else f"/{current_lang}/{slug}"

    dict_lang = TRANSLATIONS.get(current_lang, TRANSLATIONS.get('fr', {}))

    context = {
        "current_lang": current_lang,
        "page_title": seo_meta["page_title"],
        "page_description": seo_meta["page_description"],
        "canonical_url": seo_meta["canonical_url"],
        "og_title": seo_meta["og_title"],
        "og_description": seo_meta["og_description"],
        "og_url": seo_meta["og_url"],
        "og_locale": seo_meta.get("og_locale"),
        "hreflang_urls": seo_meta["hreflang_urls"],
        "structured_data_jsonld": structured_jsonld,
        "t": translate,
        "t_dict": dict_lang,
        "url_for_page": get_url
    }
    context.update(kwargs)
    return render_template(template_name, **context)


@app.route("/")
def index():
    detected_lang = request.accept_languages.best_match(SUPPORTED_LANGS)
    if detected_lang and detected_lang != DEFAULT_LANG:
        return redirect(f"/{detected_lang}/")
    return _render_page("home", "fr", "landing.html")

@app.route("/<path:path>", strict_slashes=False)
def universal_router(path):
    parts = path.strip('/').split('/')

    if len(parts) == 1 and parts[0] in SUPPORTED_LANGS:
        return _render_page("home", parts[0], "landing.html")

    if len(parts) == 2 and parts[0] == "bus":
        return city_seo_page(parts[1], "fr")

    if len(parts) == 3 and parts[0] in SUPPORTED_LANGS and parts[1] == "bus":
        return city_seo_page(parts[2], parts[0])

    if len(parts) == 1:
        slug = parts[0]
        for page_key, translations in URL_SLUGS.items():
            if slug == translations.get("fr", page_key):
                return _render_page(page_key, "fr", f"{page_key}.html")

    if len(parts) == 2 and parts[0] in SUPPORTED_LANGS:
        lang = parts[0]
        slug = parts[1]
        for page_key, translations in URL_SLUGS.items():
            expected_slug = translations.get(lang, translations.get("en", page_key))
            if slug == expected_slug:
                return _render_page(page_key, lang, f"{page_key}.html")

    abort(404)

def get_ssr_connected_stops(stop_id, current_lang):

    try:
        query = """
            SELECT DISTINCT s.stop_id, s.stop_name
            FROM stop_times st1
            JOIN stop_times st2 ON st1.trip_id = st2.trip_id
            JOIN stops s ON st2.stop_id = s.stop_id
            WHERE st1.stop_id = ? AND st2.stop_id != ?
            ORDER BY s.stop_name
            LIMIT 80

            SELECT
                s.stop_id,
                s.stop_name,
                s.stop_lat,
                s.stop_lon,
                t.route_id
            FROM stop_times st1
            JOIN stop_times st2 ON st1.trip_id = st2.trip_id
            JOIN stops s ON st2.stop_id = s.stop_id
            JOIN trips t ON st1.trip_id = t.trip_id
            WHERE st1.stop_id = ? AND st2.stop_id != ?
        """
        with closing(get_db()) as conn:
            cursor = conn.execute(query, (str(stop_id), str(stop_id)))

            stop_map = {}
            for row in cursor:
                s_id = row['stop_id']
                if s_id not in stop_map:
                    stop_map[s_id] = {
                        "stop_id": s_id,
                        "stop_name": row['stop_name'] or '',
                        "stop_lat": float(row['stop_lat']) if row['stop_lat'] else None,
                        "stop_lon": float(row['stop_lon']) if row['stop_lon'] else None,
                        "operators_set": set()
                    }
                op = get_operator_from_id(row['route_id'])
                if op and op != 'unknown':
                    stop_map[s_id]['operators_set'].add(op)

            results = []
            for s_id, data in stop_map.items():
                ops = sorted(list(data['operators_set']))
                if not ops:
                    ops = ['flixbus']
                data['operators'] = ops
                del data['operators_set']
                results.append(data)

            results.sort(key=lambda x: x["stop_name"])
            return jsonify(results)

    except Exception as e:
        app.logger.error(f"Erreur API connected_stops : {e}")
        return jsonify({"error": "Erreur interne."}), 500

if __name__ == "__main__":
    app.logger.info("--- DÉMARRAGE MODE DÉVELOPPEMENT ---")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))