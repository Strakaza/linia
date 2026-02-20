import pandas as pd
import os
import logging
import json
from flask import Flask, jsonify, render_template, request, send_from_directory, redirect, url_for, Response, abort
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import traceback

# --- 1. IMPORT DES TRADUCTIONS ---
try:
    from translations import TRANSLATIONS
except ImportError:
    print("ATTENTION : Le fichier translations.py est manquant.")
    TRANSLATIONS = {"fr": {}}

GTFS_DATA_PATH = os.path.join("output_gtfs", "unified")

# --- 2. L'ARME SECRÈTE SEO : DICTIONNAIRE DES VILLES (TOP HUBS) ---
TOP_HUBS = {  
    "paris": {
        "id": "FLX_dcc0b0b8-9603-11e6-9066-549f350fcb0c",
        "name": "Paris",
        "slugs": {
            "fr": "paris",
            "en": "paris",
            "de": "paris",
            "it": "parigi",
            "es": "paris",
            "default": "paris"
        }
    },
    "marseille": {
        "id": "FLX_dcc2e206-9603-11e6-9066-549f350fcb0c",
        "name": "Marseille",
        "slugs": {
            "fr": "marseille",
            "en": "marseille",
            "de": "marseille",
            "it": "marsiglia",
            "es": "marsella",
            "default": "marseille"
        }
    },
    "lyon": {
        "id": "FLX_a546c464-28ec-42a2-a6dc-1fa708f0fe89",
        "name": "Lyon",
        "slugs": {
            "fr": "lyon",
            "en": "lyon",
            "de": "lyon",
            "it": "lione",
            "es": "lyon",
            "default": "lyon"
        }
    },
    "toulouse": {
        "id": "FLX_dcc0e74b-9603-11e6-9066-549f350fcb0c",
        "name": "Toulouse",
        "slugs": {
            "fr": "toulouse",
            "en": "toulouse",
            "default": "toulouse"
        }
    },
    "nice": {
        "id": "FLX_c3996d55-4fc0-40ae-8fe2-62b3d07fd0d7",
        "name": "Nice",
        "slugs": {
            "fr": "nice",
            "en": "nice",
            "de": "nizza",
            "it": "nizza",
            "default": "nice"
        }
    },
    "nantes": {
        "id": "FLX_6c33811e-9f58-457f-a112-44620ebba523",
        "name": "Nantes",
        "slugs": {"default": "nantes"}
    },
    "montpellier": {
        "id": "FLX_dcc0b9bc-9603-11e6-9066-549f350fcb0c",
        "name": "Montpellier",
        "slugs": {"default": "montpellier"}
    },
    "strasbourg": {
        "id": "FLX_dcbac843-9603-11e6-9066-549f350fcb0c",
        "name": "Strasbourg",
        "slugs": {
            "fr": "strasbourg",
            "en": "strasbourg",
            "de": "strassburg",
            "it": "strasburgo",
            "es": "estrasburgo",
            "default": "strasbourg"
        }
    },
    "bordeaux": {
        "id": "FLX_dcc06cc2-9603-11e6-9066-549f350fcb0c",
        "name": "Bordeaux",
        "slugs": {
            "fr": "bordeaux",
            "it": "bordeaux",
            "es": "burdeos",
            "default": "bordeaux"
        }
    },
    "lille": {
        "id": "FLX_dcbf8aeb-9603-11e6-9066-549f350fcb0c",
        "name": "Lille",
        "slugs": {
            "fr": "lille",
            "nl": "rijsel",
            "default": "lille"
        }
    },
    "rennes": {
        "id": "FLX_dcc0cced-9603-11e6-9066-549f350fcb0c",
        "name": "Rennes",
        "slugs": {"default": "rennes"}
    },
    "reims": {
        "id": "FLX_dcbfeac0-9603-11e6-9066-549f350fcb0c",
        "name": "Reims",
        "slugs": {"default": "reims"}
    },
    "toulon": {
        "id": "FLX_dcc21600-9603-11e6-9066-549f350fcb0c",
        "name": "Toulon",
        "slugs": {"default": "toulon"}
    },
    "saint_etienne": {
        "id": "FLX_dcc19252-9603-11e6-9066-549f350fcb0c",
        "name": "Saint-Étienne",
        "slugs": {"default": "saint-etienne"}
    },
    "le_havre": {
        "id": "FLX_dcc14569-9603-11e6-9066-549f350fcb0c",
        "name": "Le Havre",
        "slugs": {"default": "le-havre"}
    },
    "grenoble": {
        "id": "FLX_dcc5ad12-9603-11e6-9066-549f350fcb0c",
        "name": "Grenoble",
        "slugs": {"default": "grenoble"}
    },
    "angers": {
        "id": "FLX_dcc1007f-9603-11e6-9066-549f350fcb0c",
        "name": "Angers",
        "slugs": {"default": "angers"}
    },
    "nimes": {
        "id": "FLX_dcc0c16d-9603-11e6-9066-549f350fcb0c",
        "name": "Nîmes",
        "slugs": {"default": "nimes"}
    },
    "villeurbanne": {
        "id": "FLX_a546c464-28ec-42a2-a6dc-1fa708f0fe89",
        "name": "Villeurbanne",
        "slugs": {"default": "lyon-villeurbanne"}
    },
    "berlin": {
        "id": "FLX_dcbc32c3-9603-11e6-9066-549f350fcb0c",
        "name": "Berlin",
        "slugs": {
            "fr": "berlin",
            "en": "berlin",
            "de": "berlin",
            "it": "berlino",
            "pl": "berlin",
            "default": "berlin"
        }
    },
    "hamburg": {
        "id": "FLX_dcbada9a-9603-11e6-9066-549f350fcb0c",
        "name": "Hambourg",
        "slugs": {
            "fr": "hambourg",
            "en": "hamburg",
            "de": "hamburg",
            "it": "amburgo",
            "es": "hamburgo",
            "default": "hamburg"
        }
    },
    "munich": {
        "id": "FLX_dcbbb2f5-9603-11e6-9066-549f350fcb0c",
        "name": "Munich",
        "slugs": {
            "fr": "munich",
            "de": "muenchen",
            "en": "munich",
            "it": "monaco-di-baviera",
            "es": "munich",
            "default": "munich"
        }
    },
    "cologne": {
        "id": "FLX_dcc54142-9603-11e6-9066-549f350fcb0c",
        "name": "Cologne",
        "slugs": {
            "fr": "cologne",
            "de": "koeln",
            "en": "cologne",
            "nl": "keulen",
            "it": "colonia",
            "default": "cologne"
        }
    },
    "frankfurt": {
        "id": "FLX_dcbadca1-9603-11e6-9066-549f350fcb0c",
        "name": "Francfort",
        "slugs": {
            "fr": "francfort",
            "de": "frankfurt-am-main",
            "en": "frankfurt",
            "it": "francoforte-sul-meno",
            "default": "frankfurt"
        }
    },
    "stuttgart": {
        "id": "FLX_dcbc0c97-9603-11e6-9066-549f350fcb0c",
        "name": "Stuttgart",
        "slugs": {
            "de": "stuttgart",
            "it": "stoccarda",
            "default": "stuttgart"
        }
    },
    "dusseldorf": {
        "id": "FLX_dcbaca96-9603-11e6-9066-549f350fcb0c",
        "name": "Düsseldorf",
        "slugs": {
            "de": "duesseldorf",
            "default": "duesseldorf"
        }
    },
    "dortmund": {
        "id": "FLX_dcbaeef4-9603-11e6-9066-549f350fcb0c",
        "name": "Dortmund",
        "slugs": {"default": "dortmund"}
    },
    "essen": {
        "id": "FLX_dcbaf468-9603-11e6-9066-549f350fcb0c",
        "name": "Essen",
        "slugs": {"default": "essen"}
    },
    "leipzig": {
        "id": "FLX_dcbc3656-9603-11e6-9066-549f350fcb0c",
        "name": "Leipzig",
        "slugs": {
            "pl": "lipsk",
            "default": "leipzig"
        }
    },
    "bremen": {
        "id": "FLX_dcbb3fe6-9603-11e6-9066-549f350fcb0c",
        "name": "Brême",
        "slugs": {
            "fr": "breme",
            "de": "bremen",
            "en": "bremen",
            "default": "bremen"
        }
    },
    "dresden": {
        "id": "FLX_dcbb7a42-9603-11e6-9066-549f350fcb0c",
        "name": "Dresde",
        "slugs": {
            "fr": "dresde",
            "de": "dresden",
            "en": "dresden",
            "pl": "drezno",
            "default": "dresden"
        }
    },
    "hannover": {
        "id": "FLX_dcbb2109-9603-11e6-9066-549f350fcb0c",
        "name": "Hanovre",
        "slugs": {
            "fr": "hanovre",
            "de": "hannover",
            "en": "hanover",
            "default": "hannover"
        }
    },
    "nuremberg": {
        "id": "FLX_dcbac661-9603-11e6-9066-549f350fcb0c",
        "name": "Nuremberg",
        "slugs": {
            "fr": "nuremberg",
            "de": "nuernberg",
            "it": "norimberga",
            "default": "nuernberg"
        }
    },
    "duisburg": {
        "id": "FLX_dcbbe873-9603-11e6-9066-549f350fcb0c",
        "name": "Duisbourg",
        "slugs": {
            "fr": "duisbourg",
            "de": "duisburg",
            "default": "duisburg"
        }
    },
    "bochum": {
        "id": "FLX_dcbaefef-9603-11e6-9066-549f350fcb0c",
        "name": "Bochum",
        "slugs": {"default": "bochum"}
    },
    "wuppertal": {
        "id": "FLX_dcbb4379-9603-11e6-9066-549f350fcb0c",
        "name": "Wuppertal",
        "slugs": {"default": "wuppertal"}
    },
    "bielefeld": {
        "id": "FLX_dcbc5a46-9603-11e6-9066-549f350fcb0c",
        "name": "Bielefeld",
        "slugs": {"default": "bielefeld"}
    },
    "bonn": {
        "id": "FLX_dcbb9d17-9603-11e6-9066-549f350fcb0c",
        "name": "Bonn",
        "slugs": {"default": "bonn"}
    },
    "munster": {
        "id": "FLX_dcbb7817-9603-11e6-9066-549f350fcb0c",
        "name": "Münster",
        "slugs": {
            "de": "muenster",
            "default": "muenster"
        }
    },

    # --- ITALIE (20) ---
    "rome": {
        "id": "FLX_dcbd9538-9603-11e6-9066-549f350fcb0c",
        "name": "Rome",
        "slugs": {
            "fr": "rome",
            "it": "roma",
            "en": "rome",
            "de": "rom",
            "es": "roma",
            "default": "roma"
        }
    },
    "milan": {
        "id": "FLX_dcbc484a-9603-11e6-9066-549f350fcb0c",
        "name": "Milan",
        "slugs": {
            "fr": "milan",
            "it": "milano",
            "en": "milan",
            "de": "mailand",
            "default": "milano"
        }
    },
    "naples": {
        "id": "FLX_c284728f-da61-43f5-aff7-6f942f088419",
        "name": "Naples",
        "slugs": {
            "fr": "naples",
            "it": "napoli",
            "en": "naples",
            "de": "neapel",
            "es": "napoles",
            "default": "napoli"
        }
    },
    "turin": {
        "id": "FLX_dcbfe731-9603-11e6-9066-549f350fcb0c",
        "name": "Turin",
        "slugs": {
            "fr": "turin",
            "it": "torino",
            "en": "turin",
            "de": "turin",
            "default": "torino"
        }
    },
    "palermo": {
        "id": "FLX_4be19091-966b-41e8-9c0d-ee8945cfa8d6",
        "name": "Palerme",
        "slugs": {
            "fr": "palerme",
            "it": "palermo",
            "default": "palermo"
        }
    },
    "genoa": {
        "id": "FLX_dcc02ea8-9603-11e6-9066-549f350fcb0c",
        "name": "Gênes",
        "slugs": {
            "fr": "genes",
            "it": "genova",
            "en": "genoa",
            "de": "genua",
            "default": "genova"
        }
    },
    "bologna": {
        "id": "FLX_dcc03216-9603-11e6-9066-549f350fcb0c",
        "name": "Bologne",
        "slugs": {
            "fr": "bologne",
            "it": "bologna",
            "default": "bologna"
        }
    },
    "florence": {
        "id": "FLX_dcbcdfc1-9603-11e6-9066-549f350fcb0c",
        "name": "Florence",
        "slugs": {
            "fr": "florence",
            "it": "firenze",
            "en": "florence",
            "de": "florenz",
            "default": "firenze"
        }
    },
    "bari": {
        "id": "FLX_dcc51e2-9603-11e6-9066-549f350fcb0c",
        "name": "Bari",
        "slugs": {"default": "bari"}
    },
    "catania": {
        "id": "FLX_b96dd294-8dcf-42f3-bdfc-b8351ff9324f",
        "name": "Catane",
        "slugs": {
            "fr": "catane",
            "it": "catania",
            "default": "catania"
        }
    },
    "venice": {
        "id": "FLX_dcbdacd2-9603-11e6-9066-549f350fcb0c",
        "name": "Venise",
        "slugs": {
            "fr": "venise",
            "it": "venezia",
            "en": "venice",
            "de": "venedig",
            "default": "venezia"
        }
    },
    "verona": {
        "id": "FLX_dcbdb0fa-9603-11e6-9066-549f350fcb0c",
        "name": "Vérone",
        "slugs": {
            "fr": "verone",
            "it": "verona",
            "default": "verona"
        }
    },
    "messina": {
        "id": "FLX_682f1f0b-ebbd-424b-8e95-58f88bb23901",
        "name": "Messine",
        "slugs": {
            "fr": "messine",
            "it": "messina",
            "default": "messina"
        }
    },
    "padua": {
        "id": "FLX_dcbd8a4d-9603-11e6-9066-549f350fcb0c",
        "name": "Padoue",
        "slugs": {
            "fr": "padoue",
            "it": "padova",
            "en": "padua",
            "default": "padova"
        }
    },
    "trieste": {
        "id": "FLX_dcbda963-9603-11e6-9066-549f350fcb0c",
        "name": "Trieste",
        "slugs": {"default": "trieste"}
    },
    "brescia": {
        "id": "FLX_dcc0221c-9603-11e6-9066-549f350fcb0c",
        "name": "Brescia",
        "slugs": {"default": "brescia"}
    },
    "taranto": {
        "id": "FLX_9070422c-d126-4b9d-998c-4c35796ef809",
        "name": "Tarente",
        "slugs": {
            "fr": "tarente",
            "it": "taranto",
            "default": "taranto"
        }
    },
    "prato": {
        "id": "FLX_dcc2de9d-9603-11e6-9066-549f350fcb0c",
        "name": "Prato",
        "slugs": {"default": "prato"}
    },
    "parma": {
        "id": "FLX_dcc277af-9603-11e6-9066-549f350fcb0c",
        "name": "Parme",
        "slugs": {
            "fr": "parme",
            "it": "parma",
            "default": "parma"
        }
    },
    "modena": {
        "id": "FLX_dcc1a55b-9603-11e6-9066-549f350fcb0c",
        "name": "Modène",
        "slugs": {
            "fr": "modene",
            "it": "modena",
            "default": "modena"
        }
    },

    # --- ESPAGNE (20) ---
    "madrid": {
        "id": "FLX_1b8eaa11-e4a2-4a88-a059-403181c2eb8c",
        "name": "Madrid",
        "slugs": {
            "fr": "madrid",
            "es": "madrid",
            "en": "madrid",
            "default": "madrid"
        }
    },
    "barcelona": {
        "id": "FLX_eb5dfc25-d6c6-4feb-b562-ce82c9972cd6",
        "name": "Barcelone",
        "slugs": {
            "fr": "barcelone",
            "es": "barcelona",
            "en": "barcelona",
            "it": "barcellona",
            "de": "barcelona",
            "default": "barcelona"
        }
    },
    "valencia": {
        "id": "FLX_65bc658e-3c84-4f8a-8879-fc56c2e567c5",
        "name": "Valence",
        "slugs": {
            "fr": "valence",
            "es": "valencia",
            "en": "valencia",
            "default": "valencia"
        }
    },
    "seville": {
        "id": "FLX_4763b0c9-cd32-4764-acfb-b68f6a2bee21",
        "name": "Séville",
        "slugs": {
            "fr": "seville",
            "es": "sevilla",
            "en": "seville",
            "default": "sevilla"
        }
    },
    "zaragoza": {
        "id": "FLX_07597a10-0f4c-49d5-84c8-abf615bd5956",
        "name": "Saragosse",
        "slugs": {
            "fr": "saragosse",
            "es": "zaragoza",
            "en": "zaragoza",
            "default": "zaragoza"
        }
    },
    "malaga": {
        "id": "FLX_5e27bb0b-8dfe-4399-be62-b23800957ce7",
        "name": "Malaga",
        "slugs": {"default": "malaga"}
    },
    "murcia": {
        "id": "FLX_e3227df6-e27b-436c-8207-b77746251a53",
        "name": "Murcie",
        "slugs": {
            "fr": "murcie",
            "es": "murcia",
            "default": "murcia"
        }
    },
    "palma": {
        "id": "FLX_eb5dfc25-d6c6-4feb-b562-ce82c9972cd6",
        "name": "Palma",
        "slugs": {"default": "palma-de-mallorca"}
    },
    "bilbao": {
        "id": "FLX_3314645f-7903-4bc9-b9ef-74ff161feca2",
        "name": "Bilbao",
        "slugs": {"default": "bilbao"}
    },
    "alicante": {
        "id": "FLX_687eb82b-bc6a-45c5-93cc-3c186b7ecc06",
        "name": "Alicante",
        "slugs": {
            "es": "alicante",
            "default": "alicante"
        }
    },
    "cordoba": {
        "id": "FLX_1979f5ae-9e90-4ca5-bc29-58e6d0020e73",
        "name": "Cordoue",
        "slugs": {
            "fr": "cordoue",
            "es": "cordoba",
            "en": "cordoba",
            "default": "cordoba"
        }
    },
    "valladolid": {
        "id": "FLX_0667ba34-c22c-40a2-a1b0-3b248c37dccf",
        "name": "Valladolid",
        "slugs": {"default": "valladolid"}
    },
    "vigo": {
        "id": "FLX_458311c9-b193-4c10-b409-b7c832ecb1b4",
        "name": "Vigo",
        "slugs": {"default": "vigo"}
    },
    "gijon": {
        "id": "FLX_eb5dfc25-d6c6-4feb-b562-ce82c9972cd6",
        "name": "Gijon",
        "slugs": {"default": "gijon"}
    },
    "hospitalet": {
        "id": "FLX_eb5dfc25-d6c6-4feb-b562-ce82c9972cd6",
        "name": "L'Hospitalet",
        "slugs": {"default": "barcelona"}
    },
    "vitoria": {
        "id": "FLX_ec29a70c-933d-4056-a35b-0adc69b554aa",
        "name": "Vitoria",
        "slugs": {
            "es": "vitoria-gasteiz",
            "default": "vitoria-gasteiz"
        }
    },
    "a_coruna": {
        "id": "FLX_779481dc-ec1a-4651-9771-f0e97a5cacc9",
        "name": "La Corogne",
        "slugs": {
            "fr": "la-corogne",
            "es": "a-coruna",
            "en": "a-coruna",
            "default": "a-coruna"
        }
    },
    "elche": {
        "id": "FLX_65bc658e-3c84-4f8a-8879-fc56c2e567c5",
        "name": "Elche",
        "slugs": {
            "es": "elche",
            "default": "elche"
        }
    },
    "granada": {
        "id": "FLX_cdf5aee6-9a78-468c-84c7-8d395c6ac70f",
        "name": "Grenade",
        "slugs": {
            "fr": "grenade",
            "es": "granada",
            "en": "granada",
            "default": "granada"
        }
    },
    "badalona": {
        "id": "FLX_eb5dfc25-d6c6-4feb-b562-ce82c9972cd6",
        "name": "Badalone",
        "slugs": {"default": "barcelona"}
    },

    "warsaw": {
        "id": "FLX_bff2a20d-e42b-4166-a06e-b9083c56b6b3",
        "name": "Varsovie",
        "slugs": {
            "fr": "varsovie",
            "pl": "warszawa",
            "en": "warsaw",
            "de": "warschau",
            "default": "warszawa"
        }
    },
    "krakow": {
        "id": "FLX_dcbd0e26-9603-11e6-9066-549f350fcb0c",
        "name": "Cracovie",
        "slugs": {
            "fr": "cracovie",
            "pl": "krakow",
            "en": "krakow",
            "de": "krakau",
            "default": "krakow"
        }
    },
    "lodz": {
        "id": "FLX_e1b6a242-54f8-4108-8e51-21c195ac77d4",
        "name": "Łódź",
        "slugs": {
            "pl": "lodz",
            "default": "lodz"
        }
    },
    "wroclaw": {
        "id": "FLX_dcbcc787-9603-11e6-9066-549f350fcb0c",
        "name": "Wrocław",
        "slugs": {
            "de": "breslau",
            "pl": "wroclaw",
            "default": "wroclaw"
        }
    },
    "poznan": {
        "id": "FLX_dcc3dad0-9603-11e6-9066-549f350fcb0c",
        "name": "Poznań",
        "slugs": {
            "pl": "poznan",
            "de": "posen",
            "default": "poznan"
        }
    },
    "gdansk": {
        "id": "FLX_dcbcd754-9603-11e6-9066-549f350fcb0c",
        "name": "Gdańsk",
        "slugs": {
            "pl": "gdansk",
            "de": "danzig",
            "default": "gdansk"
        }
    },
    "szczecin": {
        "id": "FLX_9b6801c7-3ecb-11ea-8017-02437075395e",
        "name": "Szczecin",
        "slugs": {
            "de": "stettin",
            "default": "szczecin"
        }
    },
    "bydgoszcz": {
        "id": "FLX_dcbccbe5-9603-11e6-9066-549f350fcb0c",
        "name": "Bydgoszcz",
        "slugs": {"default": "bydgoszcz"}
    },
    "lublin": {
        "id": "FLX_deff7f45-3d10-4bb0-a5bd-7ddc327d9f41",
        "name": "Lublin",
        "slugs": {"default": "lublin"}
    },
    "bialystok": {
        "id": "FLX_e383decd-d064-423a-ab3b-600e6023edde",
        "name": "Białystok",
        "slugs": {"default": "bialystok"}
    },
    "katowice": {
        "id": "FLX_dcbd04b6-9603-11e6-9066-549f350fcb0c",
        "name": "Katowice",
        "slugs": {"default": "katowice"}
    },
    "gdynia": {
        "id": "FLX_e9642e51-d7b3-4a35-be40-78dc9749a922",
        "name": "Gdynia",
        "slugs": {"default": "gdynia"}
    },
    "czestochowa": {
        "id": "FLX_dcc595c6-9603-11e6-9066-549f350fcb0c",
        "name": "Częstochowa",
        "slugs": {"default": "czestochowa"}
    },
    "radom": {
        "id": "FLX_6caf963e-0be6-4925-abab-6a5931666154",
        "name": "Radom",
        "slugs": {"default": "radom"}
    },
    "sosnowiec": {
        "id": "FLX_427efa4a-627a-40f2-bbcd-0dbaa06e14c9",
        "name": "Sosnowiec",
        "slugs": {"default": "sosnowiec"}
    },
    "torun": {
        "id": "FLX_5404247b-9239-4c05-b4e8-479383d7c584",
        "name": "Toruń",
        "slugs": {
            "de": "thorn",
            "default": "torun"
        }
    },
    "kielce": {
        "id": "FLX_9563e4ca-0972-4805-a7b0-62d52b86793c",
        "name": "Kielce",
        "slugs": {"default": "kielce"}
    },
    "rzeszow": {
        "id": "FLX_dcc3ea96-9603-11e6-9066-549f350fcb0c",
        "name": "Rzeszów",
        "slugs": {"default": "rzeszow"}
    },
    "gliwice": {
        "id": "FLX_55bd2ce7-265f-433e-a9ed-ec1789f5f3ed",
        "name": "Gliwice",
        "slugs": {"default": "gliwice"}
    },
    "zabrze": {
        "id": "FLX_161bc8e8-a659-4aad-b0fd-adce57501554",
        "name": "Zabrze",
        "slugs": {"default": "zabrze"}
    },

    # --- AUTRES HUBS EUROPÉENS MAJEURS ---
    "london": {
        "id": "FLX_cab329fd-7882-4cc0-a292-d796d45b7036",
        "name": "Londres",
        "slugs": {
            "fr": "londres",
            "en": "london",
            "de": "london",
            "it": "londra",
            "es": "londres",
            "default": "london"
        }
    },
    "vienna": {
        "id": "FLX_dcbca3fc-9603-11e6-9066-549f350fcb0c",
        "name": "Vienne",
        "slugs": {
            "fr": "vienne",
            "de": "wien",
            "en": "vienna",
            "it": "vienna",
            "default": "wien"
        }
    },
    "prague": {
        "id": "FLX_dcbc6452-9603-11e6-9066-549f350fcb0c",
        "name": "Prague",
        "slugs": {
            "fr": "prague",
            "cs": "praha",
            "de": "prag",
            "en": "prague",
            "default": "praha"
        }
    },
    "amsterdam": {
        "id": "FLX_dcbc54e2-9603-11e6-9066-549f350fcb0c",
        "name": "Amsterdam",
        "slugs": {"default": "amsterdam"}
    },
    "brussels": {
        "id": "FLX_dcbfd126-9603-11e6-9066-549f350fcb0c",
        "name": "Bruxelles",
        "slugs": {
            "fr": "bruxelles",
            "nl": "brussel",
            "en": "brussels",
            "de": "bruessel",
            "default": "brussels"
        }
    },
    "lisbon": {
        "id": "FLX_301c577a-9c96-4bdf-95a1-a380cabdd28b",
        "name": "Lisbonne",
        "slugs": {
            "fr": "lisbonne",
            "pt": "lisboa",
            "en": "lisbon",
            "default": "lisboa"
        }
    },
    "budapest": {
        "id": "FLX_dcbcd0d8-9603-11e6-9066-549f350fcb0c",
        "name": "Budapest",
        "slugs": {"default": "budapest"}
    },
    "copenhagen": {
        "id": "FLX_dcbd0b4b-9603-11e6-9066-549f350fcb0c",
        "name": "Copenhague",
        "slugs": {
            "fr": "copenhague",
            "da": "koebenhavn",
            "en": "copenhagen",
            "de": "kopenhagen",
            "default": "koebenhavn"
        }
    },
    "stockholm": {
        "id": "FLX_dcc03476-9603-11e6-9066-549f350fcb0c",
        "name": "Stockholm",
        "slugs": {"default": "stockholm"}
    },
    "oslo": {
        "id": "FLX_dcc38945-9603-11e6-9066-549f350fcb0c",
        "name": "Oslo",
        "slugs": {"default": "oslo"}
    },
    "helsinki": {
        "id": "FLX_f11061e0-b4b4-4a2c-8337-519d3eeca976",
        "name": "Helsinki",
        "slugs": {"default": "helsinki"}
    },
    "zurich": {
        "id": "FLX_dcbab299-9603-11e6-9066-549f350fcb0c",
        "name": "Zurich",
        "slugs": {
            "de": "zuerich",
            "it": "zurigo",
            "default": "zuerich"
        }
    },
    "geneva": {
        "id": "FLX_dcc0627e-9603-11e6-9066-549f350fcb0c",
        "name": "Genève",
        "slugs": {
            "fr": "geneve",
            "en": "geneva",
            "de": "genf",
            "it": "ginevra",
            "default": "geneve"
        }
    },
    "istanbul": {
        "id": "FLX_9b6a8316-3ecb-11ea-8017-02437075395e",
        "name": "Istanbul",
        "slugs": {"default": "istanbul"}
    },
    "athens": {
        "id": "FLX_cab329fd-7882-4cc0-a292-d796d45b7036",
        "name": "Athènes",
        "slugs": {
            "fr": "athenes",
            "en": "athens",
            "el": "athina",
            "default": "athens"
        }
    },
    "bucharest": {
        "id": "FLX_54c7a569-1af8-4252-aa35-eba0ff50b89b",
        "name": "Bucarest",
        "slugs": {
            "fr": "bucarest",
            "ro": "bucuresti",
            "en": "bucharest",
            "default": "bucuresti"
        }
    },
    "kyiv": {
        "id": "FLX_394088d2-0c06-4dea-9fc1-5b70c8d50f9c",
        "name": "Kyiv",
        "slugs": {
            "en": "kyiv",
            "uk": "kyiv",
            "default": "kyiv"
        }
    },
    "belgrade": {
        "id": "FLX_c17eed68-17b3-421f-a8f4-3f3786cb4fca",
        "name": "Belgrade",
        "slugs": {
            "sr": "beograd",
            "default": "beograd"
        }
    },
    "zagreb": {
        "id": "FLX_dcbdbe76-9603-11e6-9066-549f350fcb0c",
        "name": "Zagreb",
        "slugs": {"default": "zagreb"}
    },
    "bratislava": {
        "id": "FLX_dcbcc605-9603-11e6-9066-549f350fcb0c",
        "name": "Bratislava",
        "slugs": {"default": "bratislava"}
    },
    "ljubljana": {
        "id": "FLX_dcbd21fc-9603-11e6-9066-549f350fcb0c",
        "name": "Ljubljana",
        "slugs": {"default": "ljubljana"}
    },
    "luxembourg": {
        "id": "FLX_dcc5d357-9603-11e6-9066-549f350fcb0c",
        "name": "Luxembourg",
        "slugs": {
            "fr": "luxembourg",
            "de": "luxemburg",
            "default": "luxembourg"
        }
    },
    "tirana": {
        "id": "FLX_c17eed68-17b3-421f-a8f4-3f3786cb4fca",
        "name": "Tirana",
        "slugs": {"default": "tirana"}
    }
}


BASE_URL = "https://liniabus.eu"
SUPPORTED_LANGS = [
    "fr", "en", "de", "es", "pt", "nl", "sq", "ca", "hr", "bg", "da", "et", "fi",
    "el", "hu", "hi", "lv", "lt", "lb", "mk", "ro", "pl", "cs", "sk", "sl", "sv",
    "tr", "uk", "ru", "be",
]
DEFAULT_LANG = "fr"

OG_LOCALES = {
    "fr": "fr_FR", "en": "en_GB", "de": "de_DE", "es": "es_ES", "it": "it_IT",
    "nl": "nl_NL", "pt": "pt_PT", "pl": "pl_PL", "sq": "sq_AL", "ca": "ca_ES",
    "hr": "hr_HR", "bg": "bg_BG", "da": "da_DK", "et": "et_EE", "fi": "fi_FI",
    "el": "el_GR", "hu": "hu_HU", "hi": "hi_IN", "lv": "lv_LV", "lt": "lt_LT",
    "lb": "lb_LU", "mk": "mk_MK", "ro": "ro_RO", "cs": "cs_CZ", "sk": "sk_SK",
    "sl": "sl_SI", "sv": "sv_SE", "tr": "tr_TR", "uk": "uk_UA", "ru": "ru_RU",
    "be": "be_BY",
}

# --- 3. DICTIONNAIRE DES URLS TRADUITES (POUR LES 30 LANGUES) ---
URL_SLUGS = {
    "map": {
        "fr": "carte", "en": "map", "de": "karte", "es": "mapa", "pt": "mapa", 
        "nl": "kaart", "sq": "harta", "ca": "mapa", "hr": "karta", "bg": "karta", 
        "da": "kort", "et": "kaart", "fi": "kartta", "el": "chartis", "hu": "terkep", 
        "hi": "naksha", "lv": "karte", "lt": "zemelapis", "lb": "kaart", "mk": "karta", 
        "ro": "harta", "pl": "mapa", "cs": "mapa", "sk": "mapa", "sl": "zemljevid", 
        "sv": "karta", "tr": "harita", "uk": "karta", "ru": "karta", "be": "karta"
    },
    "planner": {
        "fr": "planificateur", "en": "planner", "de": "reiseplaner", "es": "planificador", 
        "pt": "planeador", "nl": "planner", "sq": "planifikues", "ca": "planificador", 
        "hr": "planer", "bg": "planirovchik", "da": "planlaegger", "et": "planeerija", 
        "fi": "reittiopas", "el": "schediastis", "hu": "tervezo", "hi": "planner", 
        "lv": "planotajs", "lt": "planuoklis", "lb": "planner", "mk": "planer", 
        "ro": "planificator", "pl": "planer", "cs": "planovac", "sk": "planovac", 
        "sl": "nacrtovalec", "sv": "planerare", "tr": "planlayici", "uk": "planuvalnyk", 
        "ru": "planirovshchik", "be": "planirouschyk"
    },
    "about": {
        "fr": "a-propos", "en": "about", "de": "ueber", "es": "acerca-de", 
        "pt": "sobre", "nl": "over", "sq": "rreth", "ca": "sobre", 
        "hr": "o-nama", "bg": "za-nas", "da": "om", "et": "meist", 
        "fi": "tietoa", "el": "schetika", "hu": "rolunk", "hi": "bare-mein", 
        "lv": "par", "lt": "apie", "lb": "iwwer", "mk": "za-nas", 
        "ro": "despre", "pl": "o-nas", "cs": "o-nas", "sk": "o-nas", 
        "sl": "o-nas", "sv": "om", "tr": "hakkinda", "uk": "pro-nas", 
        "ru": "o-nas", "be": "pra-nas"
    },
    "legal": {
        "fr": "mentions-legales", "en": "legal", "de": "impressum", "es": "aviso-legal", 
        "pt": "aviso-legal", "nl": "juridisch", "sq": "kushtet-ligjore", "ca": "avis-legal", 
        "hr": "pravne-informacije", "bg": "pravni-usloviya", "da": "juridisk", "et": "oiguslik", 
        "fi": "oikeudelliset-tiedot", "el": "nomika", "hu": "jogi-nyilatkozat", "hi": "kanooni", 
        "lv": "juridiska-informacija", "lt": "teisine-informacija", "lb": "impressum", "mk": "pravni-informacii", 
        "ro": "informatii-legale", "pl": "informacje-prawne", "cs": "pravni-informace", "sk": "pravne-informacie", 
        "sl": "pravno-obvestilo", "sv": "juridisk-information", "tr": "yasal", "uk": "yurydychna-informatsiya", 
        "ru": "pravovaya-informatsiya", "be": "yurydychnaya-infarmatsyya"
    }
}

SEARCH_SYNONYMS = {
    # --- ALLEMAGNE ---
    "köln": "Cologne",
    "koln": "Cologne",
    "keulen": "Cologne",
    "colonia": "Cologne",
    "münchen": "Munich",
    "munchen": "Munich",
    "muenchen": "Munich",
    "monaco di baviera": "Munich",
    "nürnberg": "Nuremberg",
    "nurnberg": "Nuremberg",
    "nuernberg": "Nuremberg",
    "norimberga": "Nuremberg",
    "frankfurt am main": "Frankfurt",
    "frankfurt": "Frankfurt",
    "francfort": "Frankfurt",
    "francoforte": "Frankfurt",
    "hambourg": "Hamburg",
    "amburgo": "Hamburg",
    "münster": "Munster",
    "muenster": "Munster",
    "berlin": "Berlin",
    "berlino": "Berlin",
    "dresde": "Dresden",
    "dresden": "Dresden",
    "dresda": "Dresden",
    "leipzig": "Leipzig",
    "lipsia": "Leipzig",
    "stuttgart": "Stuttgart",
    "stoccarda": "Stuttgart",
    "düsseldorf": "Dusseldorf",
    "dusseldorf": "Dusseldorf",
    "düsseldorfo": "Dusseldorf",
    "essen": "Essen",
    "bremen": "Bremen",
    "brême": "Bremen",
    "brema": "Bremen",
    "hannover": "Hannover",
    "hanover": "Hannover",
    "hanovre": "Hannover",
    "hannovre": "Hannover",
    "bonn": "Bonn",
    "bielefeld": "Bielefeld",
    "karlsruhe": "Karlsruhe",
    "carlesruhe": "Karlsruhe",
    "wiesbaden": "Wiesbaden",
    "augsburg": "Augsburg",
    "augsbourg": "Augsburg",
    "augusta": "Augsburg",
    "aachen": "Aachen",
    "aix-la-chapelle": "Aachen",
    "aquisgrana": "Aachen",
    "chemnitz": "Chemnitz",
    "chemnitz": "Chemnitz",
    "kiel": "Kiel",
    "magdeburg": "Magdeburg",
    "fribourg": "Freiburg",
    "freiburg": "Freiburg",
    "friburgo": "Freiburg",
    "lübeck": "Lubeck",
    "lubeck": "Lubeck",
    "lubeca": "Lubeck",
    "erfurt": "Erfurt",
    "rostock": "Rostock",
    "potsdam": "Potsdam",
    "saarbrücken": "Saarbrücken",
    "saarbruecken": "Saarbrücken",
    "saarbrucken": "Saarbrücken",
    "kassel": "Kassel",
    "cassel": "Kassel",
    "oberhausen": "Oberhausen",
    "münchengladbach": "Mönchengladbach",
    "moenchengladbach": "Mönchengladbach",
    "monchengladbach": "Mönchengladbach",
    "bremerhaven": "Bremerhaven",
    "hagen": "Hagen",
    "hamm": "Hamm",
    "mainz": "Mainz",
    "mayence": "Mainz",
    "magonza": "Mainz",
    "heidelberg": "Heidelberg",
    "darmstadt": "Darmstadt",
    "würzburg": "Würzburg",
    "wuerzburg": "Würzburg",
    "wurzburg": "Würzburg",
    "ingolstadt": "Ingolstadt",
    "ulm": "Ulm",
    "heilbronn": "Heilbronn",
    "pforzheim": "Pforzheim",
    "reutlingen": "Reutlingen",
    "göttingen": "Göttingen",
    "goettingen": "Göttingen",
    "gottingen": "Göttingen",
    "coblenz": "Koblenz",
    "koblenz": "Koblenz",
    "coblenza": "Koblenz",
    "trier": "Trier",
    "trèves": "Trier",
    "treviri": "Trier",
    "jena": "Jena",
    "gera": "Gera",
    "hildesheim": "Hildesheim",
    "zwickau": "Zwickau",
    "flensburg": "Flensburg",
    "flensbourg": "Flensburg",
    "flensburgo": "Flensburg",
    "cuxhaven": "Cuxhaven",
    "wilhelmshaven": "Wilhelmshaven",
    "baden-baden": "Baden-Baden",
    "badenbaden": "Baden-Baden",
    "wiesloch": "Wiesloch",
    "neustadt": "Neustadt",
    "neumünster": "Neumünster",
    "neumuenster": "Neumünster",
    "neumunster": "Neumünster",
    "radebeul": "Radebeul",
    "meissen": "Meissen",
    "meißen": "Meissen",
    "freiberg": "Freiberg",
    "freiberg": "Freiberg",
    "bautzen": "Bautzen",
    "bautzen": "Bautzen",
    "gorlitz": "Görlitz",
    "goerlitz": "Görlitz",
    "carlsbad": "Karlsbad",  
    "karlsbad": "Karlsbad",

    # --- POLOGNE ---
    "warszawa": "Warsaw",
    "varsovie": "Warsaw",
    "warschau": "Warsaw",
    "kraków": "Krakow",
    "krakow": "Krakow",
    "cracovie": "Krakow",
    "krakau": "Krakow",
    "wrocław": "Wroclaw",
    "wroclaw": "Wroclaw",
    "breslau": "Wroclaw",
    "łódź": "Lodz",
    "lodz": "Lodz",
    "poznan": "Poznan",
    "poznań": "Poznan",
    "posen": "Poznan",
    "gdańsk": "Gdansk",
    "gdansk": "Gdansk",
    "danzig": "Gdansk",
    "szczecin": "Szczecin",
    "stettin": "Szczecin",
    "bydgoszcz": "Bydgoszcz",
    "bromberg": "Bydgoszcz",
    "lublin": "Lublin",
    "katowice": "Katowice",
    "kattowitz": "Katowice",
    "bialystok": "Bialystok",
    "białystok": "Bialystok",
    "gdynia": "Gdynia",
    "gdingen": "Gdynia",
    "częstochowa": "Czestochowa",
    "czestochowa": "Czestochowa",
    "radom": "Radom",
    "sosnowiec": "Sosnowiec",
    "toruń": "Torun",
    "torun": "Torun",
    "thorn": "Torun",
    "kielce": "Kielce",
    "rzeszów": "Rzeszow",
    "rzeszow": "Rzeszow",
    "opole": "Opole",
    "oppeln": "Opole",
    "zielona góra": "Zielona Gora",
    "zielona gora": "Zielona Gora",
    "gorzów wielkopolski": "Gorzow Wielkopolski",
    "gorzow wielkopolski": "Gorzow Wielkopolski",
    "wałbrzych": "Walbrzych",
    "walbrzych": "Walbrzych",
    "włocławek": "Wloclawek",
    "wloclawek": "Wloclawek",
    "tarnów": "Tarnow",
    "tarnow": "Tarnow",
    "plock": "Plock",
    "płock": "Plock",
    "chorzów": "Chorzow",
    "chorzow": "Chorzow",
    "kalisz": "Kalisz",
    "kalisz": "Kalisz",
    "koszalin": "Koszalin",
    "köslin": "Koszalin",
    "legnica": "Legnica",
    "liegnitz": "Legnica",
    "grudziądz": "Grudziadz",
    "grudziadz": "Grudziadz",
    "graudenz": "Grudziadz",
    "slupsk": "Slupsk",
    "słupsk": "Slupsk",
    "stolp": "Slupsk",
    "bielsko-biała": "Bielsko-Biala",
    "bielsko-biala": "Bielsko-Biala",

    # --- ITALIE ---
    "milano": "Milan",
    "roma": "Rome",
    "rom": "Rome",
    "firenze": "Florence",
    "florenz": "Florence",
    "venezia": "Venice",
    "venise": "Venice",
    "venedig": "Venice",
    "napoli": "Naples",
    "neapel": "Naples",
    "torino": "Turin",
    "genova": "Genoa",
    "gênes": "Genoa",
    "genua": "Genoa",
    "padova": "Padua",
    "padoue": "Padua",
    "bologna": "Bologna",
    "bologne": "Bologna",
    "palermo": "Palermo",
    "palerme": "Palermo",
    "catania": "Catania",
    "catane": "Catania",
    "messina": "Messina",
    "messine": "Messina",
    "bari": "Bari",
    "taranto": "Taranto",
    "tarente": "Taranto",
    "cagliari": "Cagliari",
    "trieste": "Trieste",
    "verona": "Verona",
    "vérone": "Verona",
    "brescia": "Brescia",
    "parma": "Parma",
    "parme": "Parma",
    "modena": "Modena",
    "modène": "Modena",
    "ravenna": "Ravenna",
    "ravenne": "Ravenna",
    "rimini": "Rimini",
    "perugia": "Perugia",
    "pérouse": "Perugia",
    "ancona": "Ancona",
    "ancône": "Ancona",
    "trento": "Trento",
    "trente": "Trento",
    "bolzano": "Bolzano",
    "bozen": "Bolzano",
    "siena": "Siena",
    "sienne": "Siena",
    "lucca": "Lucca",
    "lucques": "Lucca",
    "pisa": "Pisa",
    "pise": "Pisa",
    "livorno": "Livorno",
    "livourne": "Livorno",
    "arezzo": "Arezzo",
    "como": "Como",
    "côme": "Como",
    "varese": "Varese",
    "bergamo": "Bergamo",
    "bergame": "Bergamo",
    "cuneo": "Cuneo",
    "asti": "Asti",
    "alessandria": "Alessandria",
    "novara": "Novara",
    "vercelli": "Vercelli",
    "biella": "Biella",
    "verbania": "Verbania",
    "aosta": "Aosta",
    "aoste": "Aosta",
    "sondrio": "Sondrio",
    "lecco": "Lecco",
    "lodi": "Lodi",
    "cremona": "Cremona",
    "crémone": "Cremona",
    "mantova": "Mantua",
    "mantoue": "Mantua",
    "rovigo": "Rovigo",
    "vicenza": "Vicenza",
    "vicence": "Vicenza",
    "belluno": "Belluno",
    "treviso": "Treviso",
    "trévise": "Treviso",
    "udine": "Udine",
    "pordenone": "Pordenone",
    "gorizia": "Gorizia",
    "imperia": "Imperia",
    "savona": "Savona",
    "savone": "Savona",
    "la spezia": "La Spezia",
    "massa": "Massa",
    "pistoia": "Pistoia",
    "prato": "Prato",
    "grosseto": "Grosseto",
    "terni": "Terni",
    "foligno": "Foligno",
    "spoleto": "Spoleto",
    "spolète": "Spoleto",
    "ascoli piceno": "Ascoli Piceno",
    "macerata": "Macerata",
    "fermo": "Fermo",
    "pesaro": "Pesaro",
    "urbino": "Urbino",
    "fano": "Fano",
    "jesi": "Jesi",
    "camerino": "Camerino",
    "san benedetto del tronto": "San Benedetto del Tronto",
    "laquila": "L'Aquila",
    "l'aquila": "L'Aquila",
    "teramo": "Teramo",
    "pescara": "Pescara",
    "chieti": "Chieti",
    "campobasso": "Campobasso",
    "isernia": "Isernia",
    "caserta": "Caserta",
    "caserte": "Caserta",
    "benevento": "Benevento",
    "bénévent": "Benevento",
    "avellino": "Avellino",
    "salerno": "Salerno",
    "salerne": "Salerno",
    "foggia": "Foggia",
    "brindisi": "Brindisi",
    "lecce": "Lecce",
    "barletta": "Barletta",
    "andria": "Andria",
    "trani": "Trani",
    "catanzaro": "Catanzaro",
    "cosenza": "Cosenza",
    "crotone": "Crotone",
    "reggio calabria": "Reggio Calabria",
    "vibo valentia": "Vibo Valentia",
    "potenza": "Potenza",
    "matera": "Matera",
    "siracusa": "Syracuse",
    "syracuse": "Syracuse",
    "ragusa": "Ragusa",
    "enna": "Enna",
    "caltanissetta": "Caltanissetta",
    "agrigento": "Agrigento",
    "agrigente": "Agrigento",
    "trapani": "Trapani",
    "sassari": "Sassari",
    "nuoro": "Nuoro",
    "oristano": "Oristano",
    "olbia": "Olbia",
    "tempio pausania": "Tempio Pausania",
    "carbonia": "Carbonia",
    "iglesias": "Iglesias",

    # --- ESPAGNE ---
    "sevilla": "Seville",
    "séville": "Seville",
    "zaragoza": "Zaragoza",
    "saragosse": "Zaragoza",
    "barcellona": "Barcelona",
    "barcelone": "Barcelona",
    "madrid": "Madrid",
    "valencia": "Valencia",
    "valence": "Valencia",
    "valenza": "Valencia",
    "malaga": "Malaga",
    "málaga": "Malaga",
    "murcia": "Murcia",
    "murcie": "Murcia",
    "palma": "Palma de Mallorca",
    "palma de mallorca": "Palma de Mallorca",
    "las palmas": "Las Palmas de Gran Canaria",
    "las palmas de gran canaria": "Las Palmas de Gran Canaria",
    "bilbao": "Bilbao",
    "alicante": "Alicante",
    "cordoba": "Cordoba",
    "cordoue": "Cordoba",
    "valladolid": "Valladolid",
    "vigo": "Vigo",
    "gijon": "Gijón",
    "gijón": "Gijón",
    "coruna": "A Coruña",
    "a coruña": "A Coruña",
    "la coruña": "A Coruña",
    "vitoria": "Vitoria-Gasteiz",
    "vitoria-gasteiz": "Vitoria-Gasteiz",
    "granada": "Granada",
    "grenade": "Granada",
    "elche": "Elche",
    "oviedo": "Oviedo",
    "santa cruz de tenerife": "Santa Cruz de Tenerife",
    "badalona": "Badalona",
    "terrassa": "Terrassa",
    "sabadell": "Sabadell",
    "cartagena": "Cartagena",
    "carthagène": "Cartagena",
    "jerez": "Jerez de la Frontera",
    "jerez de la frontera": "Jerez de la Frontera",
    "pamplona": "Pamplona",
    "pampelune": "Pamplona",
    "donostia": "San Sebastián",
    "san sebastian": "San Sebastián",
    "san sebastián": "San Sebastián",
    "logroño": "Logroño",
    "logrono": "Logroño",
    "salamanca": "Salamanca",
    "salamanque": "Salamanca",
    "huelva": "Huelva",
    "lleida": "Lleida",
    "lerida": "Lleida",
    "marbella": "Marbella",
    "cadiz": "Cádiz",
    "cadix": "Cádiz",
    "algeciras": "Algeciras",
    "santander": "Santander",
    "burgos": "Burgos",
    "albacete": "Albacete",
    "almeria": "Almería",
    "almería": "Almería",
    "soria": "Soria",
    "cuenca": "Cuenca",
    "toledo": "Toledo",
    "tolède": "Toledo",
    "ciudad real": "Ciudad Real",
    "caceres": "Cáceres",
    "cáceres": "Cáceres",
    "badajoz": "Badajoz",
    "leon": "León",
    "león": "León",
    "zamora": "Zamora",
    "palencia": "Palencia",
    "avila": "Ávila",
    "ávila": "Ávila",
    "segovia": "Segovia",
    "ségovie": "Segovia",
    "guadalajara": "Guadalajara",
    "tarragona": "Tarragona",
    "tarragone": "Tarragona",
    "girona": "Girona",
    "gerone": "Girona",
    "figueres": "Figueres",
    "reus": "Reus",
    "tortosa": "Tortosa",
    "huesca": "Huesca",
    "teruel": "Teruel",
    "castellon": "Castellón de la Plana",
    "castellón de la plana": "Castellón de la Plana",
    "ourense": "Ourense",
    "pontevedra": "Pontevedra",
    "lugo": "Lugo",
    "santiago de compostela": "Santiago de Compostela",
    "compostela": "Santiago de Compostela",
    "ferrol": "Ferrol",
    "jaen": "Jaén",
    "jaén": "Jaén",

    # --- AUTRES CAPITALES & HUBS (déjà existants) ---
    "praha": "Prague",
    "prag": "Prague",
    "wien": "Vienna",
    "vienne": "Vienna",
    "genève": "Geneva",
    "geneve": "Geneva",
    "genf": "Geneva",
    "ginevra": "Geneva",
    "zürich": "Zurich",
    "zurich": "Zurich",
    "zuerich": "Zurich",
    "brüssel": "Brussels",
    "brussel": "Brussels",
    "bruxelles": "Brussels",
    "lisboa": "Lisbon",
    "lisbonne": "Lisbon",
    "koebenhavn": "Copenhagen",
    "kopenhagen": "Copenhagen",
    "copenhague": "Copenhagen",
    "bucuresti": "Bucharest",
    "bucarest": "Bucharest",
    "athenes": "Athens",
    "athina": "Athens",
    "kyiv": "Kyiv",
    "kiev": "Kyiv",
    "beograd": "Belgrade",
    "luxemburg": "Luxembourg",

    # --- NOUVELLES CAPITALES ET GRANDES VILLES ---
    "london": "London",
    "londres": "London",
    "londen": "London",
    "londra": "London",
    "paris": "Paris",
    "parigi": "Paris",
    "amsterdam": "Amsterdam",
    "stockholm": "Stockholm",
    "stoccolma": "Stockholm",
    "oslo": "Oslo",
    "helsinki": "Helsinki",
    "helsingfors": "Helsinki",
    "reykjavik": "Reykjavik",
    "reykjavík": "Reykjavik",
    "dublin": "Dublin",
    "dublino": "Dublin",
    "edinburgh": "Edinburgh",
    "edimbourg": "Edinburgh",
    "edimburgo": "Edinburgh",
    "glasgow": "Glasgow",
    "manchester": "Manchester",
    "birmingham": "Birmingham",
    "liverpool": "Liverpool",
    "bristol": "Bristol",
    "sheffield": "Sheffield",
    "leeds": "Leeds",
    "newcastle": "Newcastle upon Tyne",
    "newcastle upon tyne": "Newcastle upon Tyne",
    "bradford": "Bradford",
    "nottingham": "Nottingham",
    "hull": "Kingston upon Hull",
    "kingston upon hull": "Kingston upon Hull",
    "plymouth": "Plymouth",
    "southampton": "Southampton",
    "portsmouth": "Portsmouth",
    "aberdeen": "Aberdeen",
    "dundee": "Dundee",
    "belfast": "Belfast",
    "cardiff": "Cardiff",
    "swansea": "Swansea",
    "newport": "Newport",
    "stoke on trent": "Stoke-on-Trent",
    "coventry": "Coventry",
    "leicester": "Leicester",
    "brighton": "Brighton",
    "oxford": "Oxford",
    "cambridge": "Cambridge",
    "york": "York",
    "bath": "Bath",
    "winchester": "Winchester",
    "salisbury": "Salisbury",
    "canterbury": "Canterbury",
    "belfast": "Belfast",

    # --- FRANCE ---
    "marseille": "Marseille",
    "marsiglia": "Marseille",
    "lyon": "Lyon",
    "lione": "Lyon",
    "toulouse": "Toulouse",
    "nice": "Nice",
    "nizza": "Nice",
    "nantes": "Nantes",
    "montpellier": "Montpellier",
    "strasbourg": "Strasbourg",
    "strasburgo": "Strasbourg",
    "strassburg": "Strasbourg",
    "bordeaux": "Bordeaux",
    "lille": "Lille",
    "rennes": "Rennes",
    "reims": "Reims",
    "le havre": "Le Havre",
    "saint-etienne": "Saint-Étienne",
    "saint etienne": "Saint-Étienne",
    "toulon": "Toulon",
    "grenoble": "Grenoble",
    "dijon": "Dijon",
    "angers": "Angers",
    "nîmes": "Nîmes",
    "nimes": "Nîmes",
    "aix-en-provence": "Aix-en-Provence",
    "aix en provence": "Aix-en-Provence",
    "clermont-ferrand": "Clermont-Ferrand",
    "clermont ferrand": "Clermont-Ferrand",
    "tours": "Tours",
    "limoges": "Limoges",
    "metz": "Metz",
    "besançon": "Besançon",
    "besancon": "Besançon",
    "orléans": "Orléans",
    "orleans": "Orléans",
    "rouen": "Rouen",
    "caen": "Caen",
    "nancy": "Nancy",
    "mulhouse": "Mulhouse",
    "perpignan": "Perpignan",
    "avignon": "Avignon",
    "poitiers": "Poitiers",
    "la rochelle": "La Rochelle",
    "brest": "Brest",
    "lorient": "Lorient",
    "annecy": "Annecy",
    "chambéry": "Chambéry",
    "chambery": "Chambéry",
    "bayonne": "Bayonne",
    "biarritz": "Biarritz",
    "carcassonne": "Carcassonne",
    "arles": "Arles",
    "antibes": "Antibes",
    "cannes": "Cannes",
    "saint-tropez": "Saint-Tropez",
    "saint tropez": "Saint-Tropez",
    "monaco": "Monaco",

    # --- SUISSE ---
    "lausanne": "Lausanne",
    "bern": "Bern",
    "berne": "Bern",
    "basel": "Basel",
    "bâle": "Basel",
    "basilea": "Basel",
    "luzern": "Lucerne",
    "lucerne": "Lucerne",
    "lugano": "Lugano",
    "interlaken": "Interlaken",
    "st. gallen": "St. Gallen",
    "sankt gallen": "St. Gallen",
    "saint-gall": "St. Gallen",
    "chur": "Chur",
    "coire": "Chur",
    "fribourg": "Fribourg",
    "freiburg": "Fribourg",  # attention: Fribourg en Suisse et Freiburg en Allemagne
    "neuchâtel": "Neuchâtel",
    "neuchatel": "Neuchâtel",

    # --- AUTRICHE ---
    "salzburg": "Salzburg",
    "salzbourg": "Salzburg",
    "innsbruck": "Innsbruck",
    "graz": "Graz",
    "linz": "Linz",
    "klagenfurt": "Klagenfurt",
    "villach": "Villach",
    "wels": "Wels",
    "st. pölten": "St. Pölten",
    "sankt pölten": "St. Pölten",

    # --- PAYS-BAS ---
    "rotterdam": "Rotterdam",
    "den haag": "The Hague",
    "the hague": "The Hague",
    "la haye": "The Hague",
    "utrecht": "Utrecht",
    "eindhoven": "Eindhoven",
    "maastricht": "Maastricht",
    "groningen": "Groningen",
    "tilburg": "Tilburg",
    "almere": "Almere",
    "breda": "Breda",
    "nijmegen": "Nijmegen",
    "enschede": "Enschede",
    "haarlem": "Haarlem",
    "arnhem": "Arnhem",
    "zaanstad": "Zaanstad",
    "amersfoort": "Amersfoort",
    "den bosch": "Den Bosch",
    "s-hertogenbosch": "Den Bosch",
    "zwolle": "Zwolle",
    "leiden": "Leiden",
    "leyden": "Leiden",
    "dordrecht": "Dordrecht",

    # --- BELGIQUE ---
    "antwerpen": "Antwerp",
    "anvers": "Antwerp",
    "anversa": "Antwerp",
    "gent": "Ghent",
    "gand": "Ghent",
    "brugge": "Bruges",
    "bruges": "Bruges",
    "liège": "Liège",
    "liege": "Liège",
    "lüttich": "Liège",
    "charleroi": "Charleroi",
    "namur": "Namur",
    "namen": "Namur",
    "mons": "Mons",
    "bergen": "Mons",
    "mechelen": "Mechelen",
    "malines": "Mechelen",
    "leuven": "Leuven",
    "louvain": "Leuven",
    "kortrijk": "Kortrijk",
    "courtrai": "Kortrijk",
    "ostend": "Ostend",
    "oostende": "Ostend",
    "ostende": "Ostend",
    "sint-niklaas": "Sint-Niklaas",
    "genk": "Genk",
    "roeselare": "Roeselare",
    "roulers": "Roeselare",
    "verviers": "Verviers",

    # --- LUXEMBOURG ---
    "luxembourg": "Luxembourg",  # déjà
    "luxemburg": "Luxembourg",

    # --- DANEMARK ---
    "aarhus": "Aarhus",
    "arhus": "Aarhus",
    "odense": "Odense",
    "aalborg": "Aalborg",
    "ålborg": "Aalborg",
    "esbjerg": "Esbjerg",
    "randers": "Randers",
    "kolding": "Kolding",
    "horsens": "Horsens",
    "vejle": "Vejle",
    "roskilde": "Roskilde",

    # --- SUÈDE ---
    "gothenburg": "Gothenburg",
    "göteborg": "Gothenburg",
    "gotembourg": "Gothenburg",
    "malmö": "Malmö",
    "malmo": "Malmö",
    "uppsala": "Uppsala",
    "västerås": "Västerås",
    "vasteras": "Västerås",
    "örebro": "Örebro",
    "orebro": "Örebro",
    "linköping": "Linköping",
    "linkoping": "Linköping",
    "helsingborg": "Helsingborg",
    "jönköping": "Jönköping",
    "jonkoping": "Jönköping",
    "norrköping": "Norrköping",
    "norrkoping": "Norrköping",
    "lund": "Lund",
    "umeå": "Umeå",
    "umea": "Umeå",
    "gävle": "Gävle",
    "gavle": "Gävle",
    "södertälje": "Södertälje",
    "sodertalje": "Södertälje",
    "borås": "Borås",
    "boras": "Borås",
    "halmstad": "Halmstad",
    "växjö": "Växjö",
    "vaxjo": "Växjö",
    "eskilstuna": "Eskilstuna",
    "karlstad": "Karlstad",

    # --- NORVÈGE ---
    "bergen": "Bergen",
    "trondheim": "Trondheim",
    "nidaros": "Trondheim",
    "stavanger": "Stavanger",
    "drammen": "Drammen",
    "fredrikstad": "Fredrikstad",
    "kristiansand": "Kristiansand",
    "sandnes": "Sandnes",
    "tromsø": "Tromsø",
    "tromso": "Tromsø",
    "sarpsborg": "Sarpsborg",
    "skien": "Skien",
    "ålesund": "Ålesund",
    "alesund": "Ålesund",
    "bodø": "Bodø",
    "bodo": "Bodø",

    # --- FINLANDE ---
    "espoo": "Espoo",
    "tampere": "Tampere",
    "tammerfors": "Tampere",
    "vantaa": "Vantaa",
    "turku": "Turku",
    "åbo": "Turku",
    "oulu": "Oulu",
    "jyväskylä": "Jyväskylä",
    "jyvaskyla": "Jyväskylä",
    "lahti": "Lahti",
    "kuopio": "Kuopio",

    # --- ISLANDE ---
    "akureyri": "Akureyri",
    "keflavik": "Keflavík",
    "keflavík": "Keflavík",

    # --- IRLANDE ---
    "cork": "Cork",
    "limerick": "Limerick",
    "galway": "Galway",
    "waterford": "Waterford",

    # --- PORTUGAL ---
    "porto": "Porto",
    "oporto": "Porto",
    "braga": "Braga",
    "coimbra": "Coimbra",
    "funchal": "Funchal",
    "setúbal": "Setúbal",
    "setubal": "Setúbal",
    "faro": "Faro",
    "évora": "Évora",
    "evora": "Évora",
    "portimão": "Portimão",
    "portimao": "Portimão",
    "viseu": "Viseu",
    "aveiro": "Aveiro",
    "guimarães": "Guimarães",
    "guimaraes": "Guimarães",
    "leiria": "Leiria",
    "sintra": "Sintra",
    "cascais": "Cascais",

    # --- ANDORRE ---
    "andorra la vella": "Andorra la Vella",
    "andorre": "Andorra la Vella",

    # --- MALTE ---
    "valletta": "Valletta",
    "la valette": "Valletta",
    "mdina": "Mdina",
    "rabat": "Rabat",
    "sliema": "Sliema",
    "st julians": "St. Julian's",
    "saint julian's": "St. Julian's",

    # --- CHYPRE ---
    "nicosia": "Nicosia",
    "lefkosia": "Nicosia",
    "limassol": "Limassol",
    "lemesos": "Limassol",
    "larnaca": "Larnaca",
    "paphos": "Paphos",
    "famagusta": "Famagusta",
    "gazimağusa": "Famagusta",
    "kyrenia": "Kyrenia",
    "girne": "Kyrenia",

    # --- LIECHTENSTEIN ---
    "vaduz": "Vaduz",

    # --- SAINT-MARIN ---
    "san marino": "San Marino",

    # --- VATICAN ---
    "vatican city": "Vatican City",
    "vaticano": "Vatican City",
    "cité du vatican": "Vatican City",

    # --- TURQUIE ---
    "istanbul": "Istanbul",
    "constantinople": "Istanbul",
    "stamboul": "Istanbul",
    "ankara": "Ankara",
    "izmir": "Izmir",
    "smyrne": "Izmir",
    "bursa": "Bursa",
    "antalya": "Antalya",
    "adana": "Adana",
    "konya": "Konya",
    "gaziantep": "Gaziantep",
    "diyarbakir": "Diyarbakır",
    "mersin": "Mersin",
    "kayseri": "Kayseri",
    "eskisehir": "Eskişehir",
    "denizli": "Denizli",
    "samsun": "Samsun",
    "kahramanmaras": "Kahramanmaraş",
    "van": "Van",
    "aydin": "Aydın",
    "tekirdag": "Tekirdağ",
    "isparta": "Isparta",
    "afyon": "Afyonkarahisar",
    "malatya": "Malatya",
    "elazig": "Elazığ",
    "erzurum": "Erzurum",
    "trabzon": "Trabzon",
    "rize": "Rize",
    "ordu": "Ordu",
    "giresun": "Giresun",
    "zonguldak": "Zonguldak",
    "bolu": "Bolu",
    "duzce": "Düzce",
    "sakarya": "Sakarya",
    "kocaeli": "Kocaeli",
    "yalova": "Yalova",
    "bilecik": "Bilecik",
    "kutahya": "Kütahya",
    "manisa": "Manisa",
    "usak": "Uşak",
    "burdur": "Burdur",
    "mugla": "Muğla",
    "balikesir": "Balıkesir",
    "canakkale": "Çanakkale",
    "edirne": "Edirne",
    "kirklareli": "Kırklareli",
    "bartin": "Bartın",
    "karabuk": "Karabük",
    "kastamonu": "Kastamonu",
    "sinop": "Sinop",
    "artvin": "Artvin",
    "ardahan": "Ardahan",
    "kars": "Kars",
    "igdir": "Iğdır",
    "agri": "Ağrı",
    "bitlis": "Bitlis",
    "mus": "Muş",
    "bingol": "Bingöl",
    "tunceli": "Tunceli",
    "erzincan": "Erzincan",
    "bayburt": "Bayburt",
    "gumushane": "Gümüşhane",
    "corum": "Çorum",
    "amasya": "Amasya",
    "tokat": "Tokat",
    "sivas": "Sivas",
    "yozgat": "Yozgat",
    "nevsehir": "Nevşehir",
    "nigde": "Niğde",
    "aksaray": "Aksaray",
    "kirsehir": "Kırşehir",
    "kirikkale": "Kırıkkale",
    "cankiri": "Çankırı",
    "karaman": "Karaman",
    "hatay": "Hatay",
    "osmaniye": "Osmaniye",
    "kilis": "Kilis",
    "sanliurfa": "Şanlıurfa",
    "adiyaman": "Adıyaman",
    "batman": "Batman",
    "siirt": "Siirt",
    "sirnak": "Şırnak",
    "mardin": "Mardin",
    "hakkari": "Hakkari",

    # --- UKRAINE ---
    "kharkiv": "Kharkiv",
    "kharkov": "Kharkiv",
    "odessa": "Odesa",
    "odesa": "Odesa",
    "lviv": "Lviv",
    "lvov": "Lviv",
    "lemberg": "Lviv",
    "dnipro": "Dnipro",
    "dnipropetrovsk": "Dnipro",
    "donetsk": "Donetsk",
    "zaporizhzhia": "Zaporizhzhia",
    "zaporijjia": "Zaporizhzhia",
    "kryvyi rih": "Kryvyi Rih",
    "mykolaiv": "Mykolaiv",
    "mariupol": "Mariupol",
    "luhansk": "Luhansk",
    "vinnytsia": "Vinnytsia",
    "chernihiv": "Chernihiv",
    "poltava": "Poltava",
    "cherkasy": "Cherkasy",
    "sumy": "Sumy",
    "zhytomyr": "Zhytomyr",
    "khmelnytskyi": "Khmelnytskyi",
    "rivne": "Rivne",
    "ivano-frankivsk": "Ivano-Frankivsk",
    "ternopil": "Ternopil",
    "lutsk": "Lutsk",
    "uzhhorod": "Uzhhorod",

    # --- BIÉLORUSSIE ---
    "minsk": "Minsk",
    "gomel": "Gomel",
    "homiel": "Gomel",
    "mogilev": "Mogilev",
    "mahilyow": "Mogilev",
    "vitebsk": "Vitebsk",
    "grodno": "Grodno",
    "hrodna": "Grodno",
    "brest": "Brest",  # Brest en Biélorussie
    "babruysk": "Babruysk",
    "bobruisk": "Babruysk",

    # --- LITUANIE ---
    "vilnius": "Vilnius",
    "wilna": "Vilnius",
    "kaunas": "Kaunas",
    "kauen": "Kaunas",
    "klaipeda": "Klaipėda",
    "memel": "Klaipėda",
    "siauliai": "Šiauliai",
    "panevezys": "Panevėžys",

    # --- LETTONIE ---
    "riga": "Riga",
    "daugavpils": "Daugavpils",
    "liepaja": "Liepāja",
    "libau": "Liepāja",
    "jelgava": "Jelgava",
    "mitau": "Jelgava",

    # --- ESTONIE ---
    "tallinn": "Tallinn",
    "revel": "Tallinn",
    "tartu": "Tartu",
    "dorpat": "Tartu",
    "narva": "Narva",
    "parnu": "Pärnu",

    # --- HONGRIE ---
    "budapest": "Budapest",
    "debrecen": "Debrecen",
    "szeged": "Szeged",
    "miskolc": "Miskolc",
    "pecs": "Pécs",
    "győr": "Győr",
    "gyor": "Győr",
    "nyiregyhaza": "Nyíregyháza",
    "kecskemet": "Kecskemét",
    "székesfehérvár": "Székesfehérvár",
    "szekesfehervar": "Székesfehérvár",

    # --- SLOVAQUIE ---
    "bratislava": "Bratislava",
    "presbourg": "Bratislava",
    "kosice": "Košice",
    "kaschau": "Košice",
    "presov": "Prešov",
    "zilina": "Žilina",
    "banska bystrica": "Banská Bystrica",
    "nove zamky": "Nové Zámky",

    # --- SLOVÉNIE ---
    "ljubljana": "Ljubljana",
    "laibach": "Ljubljana",
    "maribor": "Maribor",
    "celje": "Celje",
    "kranj": "Kranj",
    "velenje": "Velenje",
    "koper": "Koper",

    # --- CROATIE ---
    "zagreb": "Zagreb",
    "split": "Split",
    "spalato": "Split",
    "dubrovnik": "Dubrovnik",
    "raguse": "Dubrovnik",
    "rijeka": "Rijeka",
    "fiume": "Rijeka",
    "zadar": "Zadar",
    "pula": "Pula",
    "sibenik": "Šibenik",
    "osijek": "Osijek",
    "slavonski brod": "Slavonski Brod",
    "varazdin": "Varaždin",

    # --- BOSNIE-HERZÉGOVINE ---
    "sarajevo": "Sarajevo",
    "banja luka": "Banja Luka",
    "mostar": "Mostar",
    "tuzla": "Tuzla",
    "zenica": "Zenica",
    "bihać": "Bihać",
    "bihac": "Bihać",

    # --- SERBIE ---
    "belgrade": "Belgrade",  # déjà avec "beograd"
    "novi sad": "Novi Sad",
    "nis": "Niš",
    "niš": "Niš",
    "kragujevac": "Kragujevac",
    "subotica": "Subotica",
    "zrenjanin": "Zrenjanin",
    "pančevo": "Pančevo",
    "pancevo": "Pančevo",
    "čačak": "Čačak",
    "cacak": "Čačak",
    "kraljevo": "Kraljevo",

    # --- MONTÉNÉGRO ---
    "podgorica": "Podgorica",
    "kotor": "Kotor",
    "budva": "Budva",
    "herceg novi": "Herceg Novi",
    "bar": "Bar",
    "nikšić": "Nikšić",
    "niksic": "Nikšić",

    # --- MACÉDOINE DU NORD ---
    "skopje": "Skopje",
    "bitola": "Bitola",
    "kumanovo": "Kumanovo",
    "prilep": "Prilep",
    "tetovo": "Tetovo",

    # --- ALBANIE ---
    "tirana": "Tirana",
    "durrës": "Durrës",
    "durres": "Durrës",
    "vlorë": "Vlorë",
    "vlore": "Vlorë",
    "shkodër": "Shkodër",
    "shkoder": "Shkodër",
    "elbasan": "Elbasan",

    # --- GRÈCE ---
    "thessaloniki": "Thessaloniki",
    "salonique": "Thessaloniki",
    "salonica": "Thessaloniki",
    "patras": "Patras",
    "heraklion": "Heraklion",
    "iráklio": "Heraklion",
    "rhodes": "Rhodes",
    "rodos": "Rhodes",
    "larissa": "Larissa",
    "volos": "Volos",
    "ioannina": "Ioannina",
    "chania": "Chania",
    "khania": "Chania",
    "kavala": "Kavala",
    "corfu": "Corfu",
    "kerkyra": "Corfu",

    # --- BULGARIE ---
    "sofia": "Sofia",
    "plovdiv": "Plovdiv",
    "varna": "Varna",
    "burgas": "Burgas",
    "broussas": "Burgas",
    "ruse": "Ruse",
    "stara zagora": "Stara Zagora",
    "pleven": "Pleven",
    "sliven": "Sliven",
    "dobrich": "Dobrich",
    "shumen": "Shumen",

    # --- ROUMANIE ---
    "cluj": "Cluj-Napoca",
    "cluj-napoca": "Cluj-Napoca",
    "klausenburg": "Cluj-Napoca",
    "timisoara": "Timișoara",
    "temeswar": "Timișoara",
    "iasi": "Iași",
    "jassy": "Iași",
    "constanta": "Constanța",
    "brasov": "Brașov",
    "kronstadt": "Brașov",
    "craiova": "Craiova",
    "galati": "Galați",
    "ploiesti": "Ploiești",
    "oradea": "Oradea",
    "sibiu": "Sibiu",
    "hermannstadt": "Sibiu",
    "arad": "Arad",
    "targu mures": "Târgu Mureș",
    "baia mare": "Baia Mare",
    "buzau": "Buzău",
    "satu mare": "Satu Mare",
    "botoșani": "Botoșani",
    "botosani": "Botoșani",
    "suceava": "Suceava",

    # --- MOLDAVIE ---
    "chisinau": "Chișinău",
    "kishinev": "Chișinău",
    "tiraspol": "Tiraspol",
    "bălți": "Bălți",
    "balți": "Bălți",
    "balti": "Bălți",
}

def find_city_by_slug(slug_input):
    """
    Retrouve la clé interne (ex: 'cologne') à partir de n'importe quel slug (ex: 'koeln').
    """
    slug_input = slug_input.lower()
    for internal_key, data in TOP_HUBS.items():
        # Vérifie si le slug correspond à une des traductions ou à la clé interne
        slugs = data.get("slugs", {})
        if slug_input in slugs.values() or slug_input == internal_key:
            return internal_key, data
    return None, None

def get_translated_slug(page_key: str, lang: str) -> str:
    """Retourne le slug traduit pour une page statique."""
    if page_key in URL_SLUGS:
        return URL_SLUGS[page_key].get(lang, URL_SLUGS[page_key].get("en", page_key))
    return page_key

def normalize_lang(lang_code: str | None) -> str:
    if not lang_code:
        return DEFAULT_LANG
    lang_code = lang_code.lower()
    return lang_code if lang_code in SUPPORTED_LANGS else DEFAULT_LANG

def build_lang_urls(page_key: str, path_slug: str | None = None) -> dict:
    """
    Génère les URLs hreflang.
    Pour les villes, 'path_slug' doit être la clé interne (ex: 'cologne').
    La fonction se charge de trouver le slug localisé (ex: 'koeln' pour 'de').
    """
    urls = {}
    
    # Si c'est une page ville, on récupère ses données pour avoir les slugs traduits
    is_city_page = (page_key == "city")
    city_data = None
    if is_city_page and path_slug:
        city_data = TOP_HUBS.get(path_slug)

    for lang in SUPPORTED_LANGS:
        current_slug = None
        
        # 1. Gestion des URLs de villes (Dynamique)
        if is_city_page and city_data:
            # On prend le slug de la langue, sinon le default
            local_slug = city_data["slugs"].get(lang, city_data["slugs"].get("default"))
            current_slug = f"bus/{local_slug}"
            
        # 2. Gestion des URLs forcées (ex: cas spécifiques non gérés par TOP_HUBS)
        elif path_slug is not None and not is_city_page:
            current_slug = path_slug
            
        # 3. Gestion des pages statiques (map, planner, etc.)
        else:
            current_slug = get_translated_slug(page_key, lang)

        # Construction de l'URL finale
        prefix = f"{BASE_URL}"
        if lang != "fr":
            prefix += f"/{lang}"
            
        if current_slug and current_slug != "home":
            urls[lang] = f"{prefix}/{current_slug}"
        else:
            urls[lang] = f"{prefix}/"

    urls["x-default"] = BASE_URL + "/"
    return urls

# Centralised SEO metadata per page and language
SEO_CONFIG = {
    "home": {
        "fr": {"title": "Linia - Planificateur d'Itinéraire Bus | FlixBus BlaBlaCar", "description": "Planifiez votre voyage en bus avec Linia. Visualisez les lignes FlixBus et BlaBlaCar Bus sur une carte interactive, comparez les connexions et créez vos itinéraires personnalisés."},
        "en": {"title": "Linia - Bus Route Planner | FlixBus and BlaBlaCar Routes", "description": "Plan your European bus journey with Linia. Visualize FlixBus and BlaBlaCar routes on an interactive map and create custom itineraries across 30+ countries."},
        "de": {"title": "Linia - Fernbus Routenplaner | FlixBus und BlaBlaCar", "description": "Planen Sie Ihre Busreise mit Linia. Visualisieren Sie FlixBus- und BlaBlaCar-Buslinien auf einer interaktiven Karte und erstellen Sie individuelle Routen."},
        "es": {"title": "Linia - Planificador de Rutas de Autobús | FlixBus y BlaBlaCar", "description": "Planifica tu viaje en autobús por Europa con Linia. Visualiza las rutas de FlixBus y BlaBlaCar en un mapa interactivo y crea itinerarios personalizados."},
        "it": {"title": "Linia - Pianificatore di Percorsi Autobus | FlixBus e BlaBlaCar", "description": "Pianifica il tuo viaggio in autobus con Linia. Visualizza le rotte FlixBus e BlaBlaCar su una mappa interattiva e crea itinerari personalizzati."},
        "nl": {"title": "Linia - Busroute Planner | FlixBus en BlaBlaCar", "description": "Plan je busreis door Europa met Linia. Visualiseer FlixBus- en BlaBlaCar-routes op een interactieve kaart en stel je eigen busroute samen."},
        "pt": {"title": "Linia - Planeador de Rotas de Autocarro | FlixBus e BlaBlaCar", "description": "Planeie a sua viagem de autocarro com a Linia. Visualize as rotas FlixBus e BlaBlaCar num mapa interativo e crie itinerários personalizados."},
        "pl": {"title": "Linia - Planer Tras Autobusowych | FlixBus i BlaBlaCar", "description": "Planuj podróże autobusem po Europie z Linia. Wyświetlaj trasy FlixBus i BlaBlaCar na interaktywnej mapie i twórz własne itineraria."},
        "sq": {"title": "Linia - Planifikues Rrugësh Autobusi | FlixBus dhe BlaBlaCar", "description": "Planifikoni udhëtimin tuaj me autobus në Evropë me Linia. Vizualizoni linjat FlixBus dhe BlaBlaCar në një hartë interaktive."},
        "ca": {"title": "Linia - Planificador de Rutes d'Autobús | FlixBus i BlaBlaCar", "description": "Planifica el teu viatge en autobús per Europa amb Linia. Visualitza les rutes de FlixBus i BlaBlaCar en un mapa interactiu."},
        "hr": {"title": "Linia - Planer Autobusnih Ruta | FlixBus i BlaBlaCar", "description": "Planirajte svoje putovanje autobusom s Linia. Vizualizirajte linije FlixBus i BlaBlaCar na interaktivnoj karti."},
        "bg": {"title": "Linia - Планировчик на Автобусни Маршрути | FlixBus и BlaBlaCar", "description": "Планирайте пътуването си с автобус с Linia. Визуализирайте линиите на FlixBus и BlaBlaCar на интерактивна карта."},
        "da": {"title": "Linia - Busrute Planlægger | FlixBus og BlaBlaCar", "description": "Planlæg din busrejse gennem Europa med Linia. Visualiser FlixBus- og BlaBlaCar-ruter på et interaktivt kort."},
        "et": {"title": "Linia - Bussiliinide Planeerija | FlixBus ja BlaBlaCar", "description": "Planeeri oma bussireis läbi Euroopa Linia abiga. Visualiseeri FlixBus ja BlaBlaCar liine interaktiivsel kaardil."},
        "fi": {"title": "Linia - Bussireitti-Suunnittelija | FlixBus ja BlaBlaCar", "description": "Suunnittele bussimatkasi Euroopassa Linian avulla. Visualisoi FlixBus- ja BlaBlaCar-reitit interaktiivisella kartalla."},
        "el": {"title": "Linia - Σχεδιασμός Διαδρομών Λεωφορείων | FlixBus και BlaBlaCar", "description": "Σχεδιάστε το ταξίδι σας με λεωφορείο στην Ευρώπη με το Linia. Οπτικοποιήστε τις διαδρομές FlixBus και BlaBlaCar."},
        "hu": {"title": "Linia - Buszútvonal Tervező | FlixBus és BlaBlaCar", "description": "Tervezze meg buszos útját Európában a Linia segítségével. Vizualizálja a FlixBus és BlaBlaCar útvonalakat interaktív térképen."},
        "hi": {"title": "Linia - बस रूट प्लानर | FlixBus और BlaBlaCar", "description": "Linia के साथ यूरोप में अपनी बस यात्रा की योजना बनाएं। इंटरैक्टिव मानचित्र पर FlixBus और BlaBlaCar मार्गों को देखें।"},
        "lv": {"title": "Linia - Autobusu Maršrutu Plānotājs | FlixBus un BlaBlaCar", "description": "Plānojiet savu autobusa ceļojumu caur Eiropu ar Linia. Vizualizējiet FlixBus un BlaBlaCar maršrutus interaktīvā kartē."},
        "lt": {"title": "Linia - Autobusų Maršrutų Planuoklis | FlixBus ir BlaBlaCar", "description": "Suplanuokite savo autobuso kelionę per Europą su Linia. Vizualizuokite FlixBus ir BlaBlaCar maršrutus interaktyviame žemėlapyje."},
        "lb": {"title": "Linia - Busroute Planner | FlixBus a BlaBlaCar", "description": "Plangt Äre Busparcours duerch Europa mat Linia. Visualiséiert d'FlixBus- a BlaBlaCar-Routen op enger interaktiver Kaart."},
        "mk": {"title": "Linia - Планер на Автобуски Рути | FlixBus и BlaBlaCar", "description": "Планирајте го вашето патување со автобус низ Европа со Linia. Визуелизирајте ги линиите на FlixBus и BlaBlaCar на интерактивна карта."},
        "ro": {"title": "Linia - Planificator Rute Autobuz | FlixBus și BlaBlaCar", "description": "Planificați călătoria cu autobuzul prin Europa cu Linia. Vizualizați rutele FlixBus și BlaBlaCar pe o hartă interactivă."},
        "cs": {"title": "Linia - Plánovač Autobusových Tras | FlixBus a BlaBlaCar", "description": "Naplánujte si cestu autobusem po Evropě s Linia. Vizualizujte linky FlixBus a BlaBlaCar na interaktivní mapě."},
        "sk": {"title": "Linia - Plánovač Autobusových Trás | FlixBus a BlaBlaCar", "description": "Naplánujte si cestu autobusom po Európe s Linia. Vizualizujte linky FlixBus a BlaBlaCar na interaktívnej mape."},
        "sl": {"title": "Linia - Načrtovalec Avtobusnih Poti | FlixBus in BlaBlaCar", "description": "Načrtujte svoje avtobusno potovanje po Evropi z Linia. Vizualizirajte linije FlixBus in BlaBlaCar na interaktivnem zemljevidu."},
        "sv": {"title": "Linia - Bussruteplanerare | FlixBus och BlaBlaCar", "description": "Planera din busresa genom Europa med Linia. Visualisera FlixBus- och BlaBlaCar-rutter på en interaktiv karta."},
        "tr": {"title": "Linia - Otobüs Güzergah Planlayıcısı | FlixBus ve BlaBlaCar", "description": "Linia ile Avrupa'daki otobüs yolculuğunuzu planlayın. FlixBus ve BlaBlaCar güzergahlarını interaktif haritada görüntüleyin."},
        "uk": {"title": "Linia - Планувальник Автобусних Маршрутів | FlixBus і BlaBlaCar", "description": "Сплануйте свою подорож автобусом Європою з Linia. Візуалізуйте маршрути FlixBus і BlaBlaCar на інтерактивній карті."},
        "ru": {"title": "Linia - Планировщик Автобусных Маршрутов | FlixBus и BlaBlaCar", "description": "Спланируйте поездку на автобусе по Европе с Linia. Визуализируйте маршруты FlixBus и BlaBlaCar на интерактивной карте."},
        "be": {"title": "Linia - Планіроўшчык Аўтобусных Маршрутаў | FlixBus і BlaBlaCar", "description": "Сплануйце сваю паездку на аўтобусе па Еўропе з Linia. Візуалізуйце маршруты FlixBus і BlaBlaCar на інтэрактыўнай карце."},
    },
    "map": {
        "fr": {"title": "Linia - Carte des Lignes de Bus | Réseau Europe", "description": "Explorez le réseau de bus FlixBus et BlaBlaCar sur une carte interactive. Trouvez tous les arrêts et lignes disponibles en Europe."},
        "en": {"title": "Linia - Bus Network Map | European Routes", "description": "Explore the FlixBus and BlaBlaCar bus network on an interactive map. Find all stops and routes available across Europe."},
        "de": {"title": "Linia - Busnetz Karte | Routen in Europa", "description": "Erkunden Sie das Busnetz von FlixBus und BlaBlaCar auf einer interaktiven Karte. Finden Sie alle Haltestellen und Linien in Europa."},
        "es": {"title": "Linia - Mapa de Rutas de Autobús | Red Europea", "description": "Explora la red de autobuses FlixBus y BlaBlaCar en un mapa interactivo. Encuentra todas las paradas y rutas disponibles en Europa."},
        "it": {"title": "Linia - Mappa della Rete Autobus | Rotte Europee", "description": "Esplora la rete di autobus FlixBus e BlaBlaCar su una mappa interattiva. Trova tutte le fermate e le rotte disponibili in Europa."},
        "nl": {"title": "Linia - Kaart Busnetwerk | Europese Routes", "description": "Verken het busnetwerk van FlixBus en BlaBlaCar op een interactieve kaart. Vind alle haltes en routes in Europa."},
        "pt": {"title": "Linia - Mapa de Rotas de Autocarro | Rede Europeia", "description": "Explore a rede de autocarros FlixBus e BlaBlaCar num mapa interativo. Encontre todas as paragens e rotas disponíveis na Europa."},
        "pl": {"title": "Linia - Mapa Połączeń Autobusowych | Trasy Europejskie", "description": "Odkryj sieć autobusową FlixBus i BlaBlaCar na interaktywnej mapie. Znajdź wszystkie przystanki i trasy dostępne w Europie."},
        "sq": {"title": "Linia - Harta e Rrjetit të Autobusëve | Rrugët Evropiane", "description": "Eksploroni rrjetin e autobusëve FlixBus dhe BlaBlaCar në një hartë interaktive. Gjeni të gjitha ndalesat dhe rrugët në Evropë."},
        "ca": {"title": "Linia - Mapa de Rutes d'Autobús | Xarxa Europea", "description": "Explora la xarxa d'autobusos FlixBus i BlaBlaCar en un mapa interactiu. Troba totes les parades i rutes disponibles a Europa."},
        "hr": {"title": "Linia - Karta Autobusne Mreže | Europske Rute", "description": "Istražite mrežu autobusa FlixBus i BlaBlaCar na interaktivnoj karti. Pronađite sva stajališta i rute dostupne u Europi."},
        "bg": {"title": "Linia - Карта на Автобусната Мрежа | Европейски Маршрути", "description": "Разгледайте автобусната мрежа на FlixBus и BlaBlaCar на интерактивна карта. Намерете всички спирки и маршрути."},
        "da": {"title": "Linia - Busnetværkskort | Europæiske Ruter", "description": "Udforsk FlixBus og BlaBlaCar busnetværket på et interaktivt kort. Find alle stoppesteder og ruter i Europa."},
        "et": {"title": "Linia - Bussivõrgu Kaart | Euroopa Marsruudid", "description": "Avasta FlixBusi ja BlaBlaCari bussivõrk interaktiivsel kaardil. Leia kõik peatused ja marsruudid Euroopas."},
        "fi": {"title": "Linia - Bussiverkostokartta | Euroopan Reitit", "description": "Tutki FlixBusin ja BlaBlaCarin bussiverkostoa interaktiivisella kartalla. Löydä kaikki pysäkit ja reitit Euroopassa."},
        "el": {"title": "Linia - Χάρτης Δικτύου Λεωφορείων | Ευρωπαϊκές Διαδρομές", "description": "Εξερευνήστε το δίκτυο λεωφορείων FlixBus και BlaBlaCar σε διαδραστικό χάρτη. Βρείτε όλες τις στάσεις και διαδρομές στην Ευρώπη."},
        "hu": {"title": "Linia - Buszhálózat Térkép | Európai Útvonalak", "description": "Fedezze fel a FlixBus és BlaBlaCar buszhálózatot interaktív térképen. Találja meg az összes megállót és útvonalat Európában."},
        "hi": {"title": "Linia - बस नेटवर्क मानचित्र | यूरोपीय मार्ग", "description": "इंटरैक्टिव मानचित्र पर FlixBus और BlaBlaCar बस नेटवर्क का अन्वेषण करें। यूरोप में उपलब्ध सभी स्टॉप और मार्ग खोजें।"},
        "lv": {"title": "Linia - Autobusu Tīkla Karte | Eiropas Maršruti", "description": "Izpētiet FlixBus un BlaBlaCar autobusu tīklu interaktīvā kartē. Atrodiet visas pieturas un maršrutus Eiropā."},
        "lt": {"title": "Linia - Autobusų Tinklo Žemėlapis | Europos Maršrutai", "description": "Tyrinėkite FlixBus ir BlaBlaCar autobusų tinklą interaktyviame žemėlapyje. Raskite visas stoteles ir maršrutus Europoje."},
        "lb": {"title": "Linia - Busnetzwierk Kaart | Europäesch Routen", "description": "Entdeckt de FlixBus a BlaBlaCar Busnetzwierk op enger interaktiver Kaart. Fannt all Arrêten a Routen an Europa."},
        "mk": {"title": "Linia - Карта на Автобуска Мрежа | Европски Рути", "description": "Истражете ја мрежата на автобуси FlixBus и BlaBlaCar на интерактивна карта. Најдете ги сите постојки и рути во Европа."},
        "ro": {"title": "Linia - Harta Rețelei de Autobuze | Rute Europene", "description": "Explorați rețeaua de autobuze FlixBus și BlaBlaCar pe o hartă interactivă. Găsiți toate stațiile și rutele disponibile în Europa."},
        "cs": {"title": "Linia - Mapa Autobusové Sítě | Evropské Trasy", "description": "Prozkoumejte autobusovou síť FlixBus a BlaBlaCar na interaktivní mapě. Najděte všechny zastávky a trasy v Evropě."},
        "sk": {"title": "Linia - Mapa Autobusovej Siete | Európske Trasy", "description": "Preskúmajte autobusovú sieť FlixBus a BlaBlaCar na interaktívnej mape. Nájdite všetky zastávky a trasy v Európe."},
        "sl": {"title": "Linia - Zemljevid Avtobusnega Omrežja | Evropske Poti", "description": "Raziščite omrežje avtobusov FlixBus in BlaBlaCar na interaktivnem zemljevidu. Poiščite vsa postajališča in poti v Evropi."},
        "sv": {"title": "Linia - Bussnätskarta | Europeiska Rutter", "description": "Utforska bussnätet för FlixBus och BlaBlaCar på en interaktiv karta. Hitta alla hållplatser och rutter i Europa."},
        "tr": {"title": "Linia - Otobüs Ağı Haritası | Avrupa Rotaları", "description": "FlixBus ve BlaBlaCar otobüs ağını interaktif haritada keşfedin. Avrupa'daki tüm durakları ve rotaları bulun."},
        "uk": {"title": "Linia - Карта Автобусної Мережі | Європейські Маршрути", "description": "Досліджуйте мережу автобусів FlixBus і BlaBlaCar на інтерактивній карті. Знайдіть усі зупинки та маршрути в Європі."},
        "ru": {"title": "Linia - Карта Автобусной Сети | Европейские Маршруты", "description": "Изучите сеть автобусов FlixBus и BlaBlaCar на интерактивной карте. Найдите все остановки и маршруты в Европе."},
        "be": {"title": "Linia - Карта Аўтобуснай Сеткі | Еўрапейскія Маршруты", "description": "Даследуйце сетку аўтобусаў FlixBus і BlaBlaCar на інтэрактыўнай карце. Знайдзіце ўсе прыпынкі і маршруты ў Еўропе."},
    },
    "planner": {
        "fr": {"title": "Linia - Créateur d'Itinéraire Bus | Comparateur", "description": "Créez votre itinéraire bus étape par étape. Sélectionnez vos villes et découvrez les connexions directes FlixBus et BlaBlaCar."},
        "en": {"title": "Linia - Bus Itinerary Builder | Route Planner", "description": "Build your bus itinerary step by step. Choose cities, see direct FlixBus and BlaBlaCar connections and export your route."},
        "de": {"title": "Linia - Busreiseplaner | Route Erstellen", "description": "Erstellen Sie Ihren Busreiseplan Schritt für Schritt. Wählen Sie Städte und entdecken Sie direkte Verbindungen mit FlixBus und BlaBlaCar."},
        "es": {"title": "Linia - Creador de Itinerarios de Autobús | Planificador", "description": "Construye tu itinerario de autobús paso a paso. Elige ciudades, ve conexiones directas de FlixBus y BlaBlaCar y exporta tu ruta."},
        "it": {"title": "Linia - Creatore di Itinerari Autobus | Pianificatore", "description": "Costruisci il tuo itinerario in autobus passo dopo passo. Scegli le città, vedi le connessioni dirette e crea il tuo viaggio."},
        "nl": {"title": "Linia - Busreisplanner | Route Samenstellen", "description": "Bouw je busreis stap voor stap. Kies steden, bekijk directe FlixBus- en BlaBlaCar-verbindingen en exporteer je route."},
        "pt": {"title": "Linia - Criador de Itinerários de Autocarro | Planeador", "description": "Construa o seu itinerário de autocarro passo a passo. Escolha cidades, veja ligações diretas da FlixBus e BlaBlaCar."},
        "pl": {"title": "Linia - Kreator Planu Podróży | Planer Autobusowy", "description": "Zbuduj swój plan podróży autobusem krok po kroku. Wybierz miasta, sprawdź bezpośrednie połączenia FlixBus i BlaBlaCar."},
        "sq": {"title": "Linia - Krijuesi i Itinerarit të Autobusit | Planifikues", "description": "Ndërtoni itinerarin tuaj të autobusit hap pas hapi. Zgjidhni qytetet, shihni lidhjet direkte dhe eksportoni rrugën tuaj."},
        "ca": {"title": "Linia - Creador d'Itineraris d'Autobús | Planificador", "description": "Construeix el teu itinerari d'autobús pas a pas. Tria ciutats, veuràs connexions directes i podràs exportar la teva ruta."},
        "hr": {"title": "Linia - Kreator Plana Puta Autobusom | Planer", "description": "Izradite svoj plan puta autobusom korak po korak. Odaberite gradove, pogledajte izravne veze FlixBusa i BlaBlaCara."},
        "bg": {"title": "Linia - Създател на Автобусни Маршрути | Планировчик", "description": "Изградете своя автобусен маршрут стъпка по стъпка. Изберете градове и вижте директните връзки."},
        "da": {"title": "Linia - Busrejseplanlægger | Rutebygger", "description": "Byg din busrejse trin for trin. Vælg byer, se direkte forbindelser med FlixBus og BlaBlaCar og eksporter din rute."},
        "et": {"title": "Linia - Bussireisi Planeerija | Marsruudi Koostaja", "description": "Koosta oma bussireis samm-sammult. Vali linnad, vaata otseseid ühendusi ja loo oma marsruut."},
        "fi": {"title": "Linia - Bussimatkan Suunnittelija | Reittiopas", "description": "Rakenna bussimatkasi vaihe vaiheelta. Valitse kaupungit, katso suorat yhteydet ja vie reittisi."},
        "el": {"title": "Linia - Δημιουργός Διαδρομών Λεωφορείων | Σχεδιαστής", "description": "Δημιουργήστε το δρομολόγιο του λεωφορείου σας βήμα προς βήμα. Επιλέξτε πόλεις και δείτε απευθείας συνδέσεις."},
        "hu": {"title": "Linia - Buszos Útvonaltervező | Utazásszervező", "description": "Építse fel buszos útitervét lépésről lépésre. Válasszon városokat, és tekintse meg a közvetlen FlixBus és BlaBlaCar csatlakozásokat."},
        "hi": {"title": "Linia - बस यात्रा कार्यक्रम निर्माता | रूट प्लानर", "description": "चरण-दर-चरण अपनी बस यात्रा कार्यक्रम बनाएं। शहर चुनें, सीधे FlixBus और BlaBlaCar कनेक्शन देखें।"},
        "lv": {"title": "Linia - Autobusu Maršrutu Veidotājs | Plānotājs", "description": "Veidojiet savu autobusa maršrutu soli pa solim. Izvēlieties pilsētas un skatiet tiešos savienojumus."},
        "lt": {"title": "Linia - Autobusų Maršrutų Kūrėjas | Planuoklis", "description": "Kurkite savo autobuso maršrutą žingsnis po žingsnio. Pasirinkite miestus ir matykite tiesioginius ryšius."},
        "lb": {"title": "Linia - Busrees Planner | Rees Creator", "description": "Baut Är Busrees Schrëtt fir Schrëtt. Wielt Stied, kuckt direkt Verbindungen an exportéiert Är Route."},
        "mk": {"title": "Linia - Креатор на Автобуски Итинерар | Планер", "description": "Изградете го вашиот план за патување со автобус чекор по чекор. Изберете градове и видете директни врски."},
        "ro": {"title": "Linia - Creator de Itinerarii Autobuz | Planificator", "description": "Construiți-vă itinerariul de autobuz pas cu pas. Alegeți orașe, vedeți conexiunile directe și exportați ruta."},
        "cs": {"title": "Linia - Tvůrce Autobusových Itinerářů | Plánovač", "description": "Sestavte si svůj autobusový itinerář krok za krokem. Vyberte města, podívejte se na přímá spojení a exportujte trasu."},
        "sk": {"title": "Linia - Tvorca Autobusových Itinerárov | Plánovač", "description": "Zostavte si svoj autobusový itinerár krok za krokom. Vyberte mestá, pozrite si priame spojenia a exportujte trasu."},
        "sl": {"title": "Linia - Ustvarjalec Avtobusnih Poti | Načrtovalec", "description": "Sestavite svoj načrt poti z avtobusom korak za korakom. Izberite mesta in si oglejte neposredne povezave."},
        "sv": {"title": "Linia - Bussreseplanerare | Ruttbyggare", "description": "Bygg din bussresa steg för steg. Välj städer, se direkta FlixBus- och BlaBlaCar-förbindelser och exportera din rutt."},
        "tr": {"title": "Linia - Otobüs Güzergah Oluşturucu | Planlayıcı", "description": "Otobüs güzergahınızı adım adım oluşturun. Şehirleri seçin, doğrudan bağlantıları görün ve rotanızı dışa aktarın."},
        "uk": {"title": "Linia - Конструктор Маршрутів | Планувальник", "description": "Створіть свій автобусний маршрут крок за кроком. Обирайте міста, дивіться прямі сполучення та експортуйте маршрут."},
        "ru": {"title": "Linia - Конструктор Маршрутов | Планировщик", "description": "Постройте свой автобусный маршрут шаг за шагом. Выбирайте города, смотрите прямые рейсы и экспортируйте маршрут."},
        "be": {"title": "Linia - Канструктар Маршрутаў | Планіроўшчык", "description": "Стварыце свой аўтобусны маршрут крок за крокам. Выбірайце гарады, глядзіце прамыя злучэнні і экспартуйце маршрут."},
    },
    "about": {
        "fr": {"title": "À Propos de Linia | Données Bus Europe", "description": "Découvrez le projet Linia, un outil open-data pour visualiser les réseaux de transport longue distance en Europe."},
        "en": {"title": "About Linia | European Bus Data Project", "description": "Learn about the Linia project, an open-data tool to visualize long-distance transport networks across Europe."},
        "de": {"title": "Über Linia | Busdaten Projekt Europa", "description": "Erfahren Sie mehr über das Projekt Linia, ein Open-Data-Tool zur Visualisierung von Fernverkehrsnetzen in Europa."},
        "es": {"title": "Sobre Linia | Proyecto de Datos de Autobús", "description": "Conoce el proyecto Linia, una herramienta de datos abiertos para visualizar redes de transporte de larga distancia en Europa."},
        "it": {"title": "Informazioni su Linia | Dati Autobus Europa", "description": "Scopri il progetto Linia, uno strumento open-data per visualizzare le reti di trasporto a lunga percorrenza in Europa."},
        "nl": {"title": "Over Linia | Europees Bus Data Project", "description": "Leer meer over het Linia-project, een open-data tool om langeafstandstransportnetwerken in Europa te visualiseren."},
        "pt": {"title": "Sobre a Linia | Dados de Autocarro Europa", "description": "Saiba mais sobre o projeto Linia, uma ferramenta de dados abertos para visualizar redes de transporte de longa distância."},
        "pl": {"title": "O Linia | Dane Autobusowe Europa", "description": "Poznaj projekt Linia, narzędzie open-data do wizualizacji sieci transportu dalekobieżnego w Europie."},
        "sq": {"title": "Rreth Linia | Të dhënat e Autobusëve Evropë", "description": "Mësoni rreth projektit Linia, një mjet me të dhëna të hapura për vizualizimin e rrjeteve të transportit."},
        "ca": {"title": "Sobre Linia | Projecte de Dades d'Autobús", "description": "Coneix el projecte Linia, una eina de dades obertes per visualitzar xarxes de transport de llarga distància a Europa."},
        "hr": {"title": "O Linia | Podaci o Autobusima Europa", "description": "Saznajte više o projektu Linia, alatu otvorenih podataka za vizualizaciju mreža dugolinijskog prijevoza."},
        "bg": {"title": "За Linia | Данни за Автобуси Европа", "description": "Научете за проекта Linia, инструмент с отворени данни за визуализация на транспортни мрежи в Европа."},
        "da": {"title": "Om Linia | Europæisk Busdata Projekt", "description": "Lær om Linia-projektet, et open data-værktøj til visualisering af langdistancetransportnetværk i Europa."},
        "et": {"title": "Linia Kohta | Euroopa Bussiandmed", "description": "Lisateave Linia projekti kohta, mis on avatud andmete tööriist pikamaatranspordivõrkude visualiseerimiseks."},
        "fi": {"title": "Tietoa Liniasta | Euroopan Bussidata", "description": "Lue lisää Linia-projektista, avoimen datan työkalusta kaukoliikenneverkkojen visualisointiin Euroopassa."},
        "el": {"title": "Σχετικά με το Linia | Δεδομένα Λεωφορείων", "description": "Μάθετε για το έργο Linia, ένα εργαλείο ανοιχτών δεδομένων για την οπτικοποίηση δικτύων μεταφορών μεγάλων αποστάσεων."},
        "hu": {"title": "A Linia-ról | Európai Buszadatok", "description": "Ismerje meg a Linia projektet, egy nyílt adatforrású eszközt az európai távolsági közlekedési hálózatok vizualizálására."},
        "hi": {"title": "Linia के बारे में | यूरोपीय बस डेटा", "description": "Linia प्रोजेक्ट के बारे में जानें, जो यूरोप में लंबी दूरी के परिवहन नेटवर्क की कल्पना करने के लिए एक ओपन-डेटा टूल है।"},
        "lv": {"title": "Par Linia | Eiropas Autobusu Dati", "description": "Uzziniet par Linia projektu, atvērto datu rīku tālsatiksmes transporta tīklu vizualizēšanai Eiropā."},
        "lt": {"title": "Apie Linia | Europos Autobusų Duomenys", "description": "Sužinokite apie Linia projektą, atvirų duomenų įrankį tolimojo susisiekimo tinklams vizualizuoti."},
        "lb": {"title": "Iwwer Linia | Busdaten Projet Europa", "description": "Léiert méi iwwer de Projet Linia, en Open-Data-Tool fir d'Visualiséierung vu laangstrecke Transportnetzer."},
        "mk": {"title": "За Linia | Податоци за Автобуси Европа", "description": "Дознајте за проектот Linia, алатка со отворени податоци за визуелизација на мрежи за транспорт на долги релации."},
        "ro": {"title": "Despre Linia | Date Autobuz Europa", "description": "Aflați despre proiectul Linia, un instrument open-data pentru vizualizarea rețelelor de transport pe distanțe lungi."},
        "cs": {"title": "O Linii | Data o Autobusech Evropa", "description": "Zjistěte více o projektu Linia, nástroji s otevřenými daty pro vizualizaci dálkových dopravních sítí v Evropě."},
        "sk": {"title": "O Linii | Údaje o Autobusoch Európa", "description": "Zistite viac o projekte Linia, nástroji s otvorenými údajmi na vizualizáciu diaľkových dopravných sietí."},
        "sl": {"title": "O Linii | Podatki o Avtobusih Evropa", "description": "Spoznajte projekt Linia, orodje odprtih podatkov za vizualizacijo omrežij dolgega prometa v Evropi."},
        "sv": {"title": "Om Linia | Europeiska Bussdata", "description": "Läs om Linia-projektet, ett verktyg med öppna data för att visualisera långdistansnätverk i Europa."},
        "tr": {"title": "Linia Hakkında | Avrupa Otobüs Verileri", "description": "Avrupa'daki uzun mesafe ulaşım ağlarını görselleştirmek için açık veri aracı olan Linia projesi hakkında bilgi edinin."},
        "uk": {"title": "Про Linia | Дані про Автобуси Європа", "description": "Дізнайтеся про проект Linia, інструмент відкритих даних для візуалізації мереж далекого сполучення в Європі."},
        "ru": {"title": "О Linia | Данные об Автобусах Европа", "description": "Узнайте о проекте Linia, инструменте открытых данных для визуализации сетей дальнего транспорта в Европе."},
        "be": {"title": "Пра Linia | Дадзеныя пра Аўтобусы Еўропа", "description": "Даведайцеся пра праект Linia, інструмент адкрытых дадзеных для візуалізацыі сетак далёкага транспарту ў Еўропе."},
    },
    "legal": {
        "fr": {"title": "Mentions Légales - Linia", "description": "Informations légales, éditeur, hébergement et conditions d'utilisation des données GTFS sur Linia."},
        "en": {"title": "Legal Notice - Linia", "description": "Legal information, publisher, hosting, and terms of use for GTFS data on Linia."},
        "de": {"title": "Impressum - Linia", "description": "Rechtliche Informationen, Herausgeber, Hosting und Nutzungsbedingungen für GTFS-Daten auf Linia."},
        "es": {"title": "Aviso Legal - Linia", "description": "Información legal, editor, alojamiento y condiciones de uso de los datos GTFS en Linia."},
        "it": {"title": "Note Legali - Linia", "description": "Informazioni legali, editore, hosting e condizioni d'uso dei dati GTFS su Linia."},
        "nl": {"title": "Juridische Informatie - Linia", "description": "Juridische informatie, uitgever, hosting en gebruiksvoorwaarden voor GTFS-gegevens op Linia."},
        "pt": {"title": "Aviso Legal - Linia", "description": "Informações legais, editor, alojamento e termos de uso dos dados GTFS na Linia."},
        "pl": {"title": "Informacje Prawne - Linia", "description": "Informacje prawne, wydawca, hosting i warunki korzystania z danych GTFS w serwisie Linia."},
        "sq": {"title": "Njoftim Ligjor - Linia", "description": "Informacion ligjor, botuesi, pritja dhe kushtet e përdorimit për të dhënat GTFS në Linia."},
        "ca": {"title": "Avís Legal - Linia", "description": "Informació legal, editor, allotjament i condicions d'ús de les dades GTFS a Linia."},
        "hr": {"title": "Pravna Obavijest - Linia", "description": "Pravne informacije, izdavač, hosting i uvjeti korištenja GTFS podataka na Linia."},
        "bg": {"title": "Правна Информация - Linia", "description": "Правна информация, издател, хостинг и условия за ползване на GTFS данни в Linia."},
        "da": {"title": "Juridisk Meddelelse - Linia", "description": "Juridiske oplysninger, udgiver, hosting og vilkår for brug af GTFS-data på Linia."},
        "et": {"title": "Õigusalane Teave - Linia", "description": "Õiguslik teave, väljaandja, majutus ja GTFS-andmete kasutustingimused Linias."},
        "fi": {"title": "Oikeudellinen Huomautus - Linia", "description": "Oikeudelliset tiedot, julkaisija, isännöinti ja GTFS-tietojen käyttöehdot Liniassa."},
        "el": {"title": "Νομική Σημείωση - Linia", "description": "Νομικές πληροφορίες, εκδότης, φιλοξενία και όροι χρήσης δεδομένων GTFS στο Linia."},
        "hu": {"title": "Jogi Nyilatkozat - Linia", "description": "Jogi információk, kiadó, tárhely és a GTFS adatok felhasználási feltételei a Linia-n."},
        "hi": {"title": "कानूनी नोटिस - Linia", "description": "कानूनी जानकारी, प्रकाशक, होस्टिंग, और Linia पर GTFS डेटा के उपयोग की शर्तें।"},
        "lv": {"title": "Juridiskais Paziņojums - Linia", "description": "Juridiskā informācija, izdevējs, hostings un GTFS datu lietošanas noteikumi vietnē Linia."},
        "lt": {"title": "Teisinė Informacija - Linia", "description": "Teisinė informacija, leidėjas, priegloba ir GTFS duomenų naudojimo sąlygos Linia."},
        "lb": {"title": "Impressum - Linia", "description": "Juristesch Informatiounen, Editeur, Hosting an Notzungsbedéngunge fir GTFS-Daten op Linia."},
        "mk": {"title": "Правна Напомена - Linia", "description": "Правни информации, издавач, хостинг и услови за користење на податоците GTFS на Linia."},
        "ro": {"title": "Notă Legală - Linia", "description": "Informații legale, editor, găzduire și termeni de utilizare a datelor GTFS pe Linia."},
        "cs": {"title": "Právní Upozornění - Linia", "description": "Právní informace, vydavatel, hosting a podmínky použití dat GTFS na Linii."},
        "sk": {"title": "Právne Oznámenie - Linia", "description": "Právne informácie, vydavateľ, hosting a podmienky používania údajov GTFS na Linii."},
        "sl": {"title": "Pravno Obvestilo - Linia", "description": "Pravne informacije, založnik, gostovanje in pogoji uporabe podatkov GTFS na Linia."},
        "sv": {"title": "Juridiskt Meddelande - Linia", "description": "Juridisk information, utgivare, hosting och användarvillkor för GTFS-data på Linia."},
        "tr": {"title": "Yasal Uyarı - Linia", "description": "Yasal bilgiler, yayıncı, barındırma ve Linia üzerindeki GTFS verilerinin kullanım koşulları."},
        "uk": {"title": "Юридичне Повідомлення - Linia", "description": "Юридична інформація, видавець, хостинг та умови використання даних GTFS на Linia."},
        "ru": {"title": "Правовая Информация - Linia", "description": "Юридическая информация, издатель, хостинг и условия использования данных GTFS на Linia."},
        "be": {"title": "Юрыдычнае Паведамленне - Linia", "description": "Юрыдычная інфармацыя, выдавец, хостынг і ўмовы выкарыстання дадзеных GTFS на Linia."},
    }
}


def normalize_lang(lang_code: str | None) -> str:
    """
    Normalise un code langue provenant de l’URL.
    Retourne toujours une langue supportée.
    """
    if not lang_code:
        return DEFAULT_LANG
    lang_code = lang_code.lower()
    return lang_code if lang_code in SUPPORTED_LANGS else DEFAULT_LANG


def build_lang_urls(page_key: str, path_slug: str | None = None) -> dict:
    """
    Construit les URLs par langue.
    Utilise le dictionnaire URL_SLUGS pour avoir de belles URLs traduites.
    """
    urls = {}
    
    # Si c'est une page de ville, on récupère les données pour accéder aux slugs traduits
    is_city_page = (page_key == "city")
    city_data = None
    if is_city_page and path_slug:
        city_data = TOP_HUBS.get(path_slug)

    for lang in SUPPORTED_LANGS:
        current_slug = None
        
        # 1. Gestion dynamique des villes (ex: cologne -> koeln pour 'de')
        if is_city_page and city_data:
            # On cherche le slug spécifique à la langue, sinon le default
            local_slug = city_data.get("slugs", {}).get(lang, city_data.get("slugs", {}).get("default"))
            current_slug = f"bus/{local_slug}"
            
        # 2. Gestion des URLs forcées (hors villes)
        elif path_slug is not None and not is_city_page:
            current_slug = path_slug
            
        # 3. Gestion des pages statiques (map, about, etc.) via dictionnaire
        else:
            current_slug = get_translated_slug(page_key, lang)

        # Construction de l'URL finale
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

log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)
app.logger.setLevel(log_level)

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

@app.before_request
def log_request_info():
    app.logger.info(f"Requête reçue: [ANONYME] [{request.method}] {request.url}")

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
    app.logger.info("== DÉBUT DU CHARGEMENT DE TOUTES LES DONNÉES GTFS ==")

    for key, filename in files_to_load.items():
        file_path = os.path.join(GTFS_DATA_PATH, filename)
        try:
            if key == "shapes" and not os.path.exists(file_path):
                data_frames[key] = pd.DataFrame() 
                all_loaded_successfully = False 
                continue 

            df = pd.read_csv(file_path, dtype=str, keep_default_na=False, na_values=['', ' '])
            
            if key == "stops":
                for col in ['stop_lat', 'stop_lon']: df[col] = pd.to_numeric(df[col], errors='coerce')
            elif key == "stop_times":
                if 'stop_sequence' in df.columns: df['stop_sequence'] = pd.to_numeric(df['stop_sequence'], errors='coerce').fillna(0).astype(int)
            elif key == "shapes": 
                if 'shape_pt_sequence' in df.columns: df['shape_pt_sequence'] = pd.to_numeric(df['shape_pt_sequence'], errors='coerce').fillna(0).astype(int)
                for col_num in ['shape_pt_lat', 'shape_pt_lon']:
                    if col_num in df.columns: df[col_num] = pd.to_numeric(df[col_num], errors='coerce')
            
            data_frames[key] = df
            app.logger.info(f"Chargé avec succès : {filename} ({len(data_frames[key])} lignes)")

        except FileNotFoundError:
            data_frames[key] = pd.DataFrame() 
            all_loaded_successfully = False
            if key != "shapes": 
                essential_files_loaded = False
        except Exception as e:
            app.logger.error(f"ERREUR (Exception) lors du chargement de {filename}: {e}")
            data_frames[key] = pd.DataFrame() 
            all_loaded_successfully = False
            if key != "shapes":
                essential_files_loaded = False

    return essential_files_loaded

load_gtfs_data()

# =========================================================================
# === LOGIQUE GTFS RESTAURÉE POUR AFFICHER CORRECTEMENT LES LIGNES ========
# =========================================================================

def get_stop_info_and_routes(stop_id_input):
    required_dfs = ["stops", "stop_times", "trips", "routes"]
    if not all(key in data_frames and not data_frames[key].empty for key in required_dfs):
        return {"error": "Les données GTFS de base ne sont pas chargées."}
    
    stops_df, stop_times_df, trips_df, routes_df = (data_frames[k] for k in required_dfs)
    stop_info_series = stops_df[stops_df['stop_id'] == str(stop_id_input)]
    
    if stop_info_series.empty: 
        return {"error": f"L'arrêt avec l'ID '{stop_id_input}' n'a pas été trouvé."}
    
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
        return { "stop_info": stop_details, "routes": [], "message": "Aucun voyage correspondant." }

    merged_trips_routes = pd.merge(relevant_trips, routes_df, on='route_id', how='left')
    if merged_trips_routes.empty:
         return { "stop_info": stop_details, "routes": [] }

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
    if not all(key in data_frames and not data_frames[key].empty for key in required_dfs):
        return {"error": "Données GTFS de base non chargées."}

    stops_df, stop_times_df, trips_df = (data_frames[k] for k in required_dfs)
    shapes_df = data_frames.get("shapes", pd.DataFrame())
    
    trip_info = trips_df[trips_df['trip_id'] == str(trip_id_input)]
    if trip_info.empty: return {"error": f"Voyage non trouvé."}
    
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
    if shape_id and not shapes_df.empty: 
        shape_data = shapes_df[shapes_df['shape_id'] == str(shape_id)]
        if not shape_data.empty:
            shape_data = shape_data.sort_values(by='shape_pt_sequence')
            for _, row_sh in shape_data.iterrows():
                trip_shape_points.append([row_sh['shape_pt_lat'], row_sh['shape_pt_lon']])
                
    return {"trip_id": trip_id_input, "stops": ordered_stops, "shape_points": trip_shape_points, "operator": operator}


# --- OUTILS DE RECHERCHE ET DE FALLBACK POUR LE SEO ---

def simple_slugify(text):
    """Transforme 'Saint-Étienne' en 'saint-etienne' pour la comparaison"""
    text = str(text).lower()
    text = text.replace('é', 'e').replace('è', 'e').replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
    return text.replace(' ', '-').replace("'", "-")

def try_find_stop_by_slug(slug):
    """
    Essaie de trouver un arrêt dans le DataFrame complet qui correspond au slug.
    C'est une opération de secours (Fallback) pour les villes qui ne sont pas dans TOP_HUBS.
    """
    if "stops" not in data_frames or data_frames["stops"].empty:
        return None
        
    stops_df = data_frames["stops"]
    
    try:
        # On cherche les arrêts dont le nom "slugifié" correspond au slug de l'URL
        mask = stops_df['stop_name'].apply(simple_slugify) == slug
        results = stops_df[mask]
        
        if not results.empty:
            row = results.iloc[0]
            return {
                "id": row['stop_id'],
                "name": row['stop_name'],
                "slugs": {"default": slug} 
            }
    except Exception as e:
        app.logger.error(f"Erreur recherche dynamique slug: {e}")
        
    return None

# --- FONCTION DE RENDU PRINCIPALE ---

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
        "url_for_page": get_url 
    }
    context.update(kwargs)
    return render_template(template_name, **context)

# --- ROUTES ---

@app.route("/")
def index():
    detected_lang = request.accept_languages.best_match(SUPPORTED_LANGS)
    if detected_lang and detected_lang != DEFAULT_LANG:
        return redirect(f"/{detected_lang}/")
    return _render_page("home", "fr", "landing.html")

@app.route("/<path:path>", strict_slashes=False)
def universal_router(path):
    parts = path.strip('/').split('/')
    
    # 1. Cas : Juste un code langue
    if len(parts) == 1 and parts[0] in SUPPORTED_LANGS:
        return _render_page("home", parts[0], "landing.html")
        
    # 2. Cas : Villes SEO en Français (ex: /bus/berlin)
    if len(parts) == 2 and parts[0] == "bus":
        return city_seo_page(parts[1], "fr")
        
    # 3. Cas : Villes SEO avec langue (ex: /de/bus/berlin)
    if len(parts) == 3 and parts[0] in SUPPORTED_LANGS and parts[1] == "bus":
        return city_seo_page(parts[2], parts[0])
        
    # 4. Cas : Pages statiques (FR)
    if len(parts) == 1:
        slug = parts[0]
        for page_key, translations in URL_SLUGS.items():
            if slug == translations.get("fr", page_key):
                return _render_page(page_key, "fr", f"{page_key}.html")
                
    # 5. Cas : Pages statiques (Langue)
    if len(parts) == 2 and parts[0] in SUPPORTED_LANGS:
        lang = parts[0]
        slug = parts[1]
        for page_key, translations in URL_SLUGS.items():
            expected_slug = translations.get(lang, translations.get("en", page_key))
            if slug == expected_slug:
                return _render_page(page_key, lang, f"{page_key}.html")
                
    abort(404)

def get_ssr_connected_stops(stop_id, current_lang):
    """
    Récupère les villes desservies en direct depuis un stop_id 
    pour les injecter dans le HTML côté serveur (Maillage interne SEO).
    """
    required_dfs = ["stops", "stop_times"]
    if not all(key in data_frames and not data_frames[key].empty for key in required_dfs):
        return []

    stops_df = data_frames["stops"]
    stop_times_df = data_frames["stop_times"]

    try:
        # Trouver tous les trips qui passent par cet arrêt
        trips_through_stop = stop_times_df[stop_times_df['stop_id'] == str(stop_id)]['trip_id'].unique()
        if len(trips_through_stop) == 0:
            return []

        # Trouver tous les arrêts de ces trips (sauf l'arrêt de départ)
        all_stop_times = stop_times_df[stop_times_df['trip_id'].isin(trips_through_stop)][['stop_id']]
        all_stop_times = all_stop_times[all_stop_times['stop_id'] != str(stop_id)]
        
        connected_stop_ids = all_stop_times['stop_id'].unique()
        if len(connected_stop_ids) == 0:
            return []

        # Récupérer les infos des arrêts connectés
        connected_stops = stops_df[stops_df['stop_id'].isin(connected_stop_ids)]
        connected_stops = connected_stops.drop_duplicates(subset=['stop_name']).sort_values(by='stop_name')

        results = []
        for _, row in connected_stops.iterrows():
            s_id = row['stop_id']
            s_name = row['stop_name']
            
            # 1. Cherche si cette ville est un TOP_HUB pour avoir le slug traduit parfait
            city_slug = None
            for hub_key, hub_data in TOP_HUBS.items():
                if hub_data["id"] == s_id:
                    city_slug = hub_data["slugs"].get(current_lang, hub_data["slugs"].get("default"))
                    break
            
            # 2. Sinon, on génère un slug simple de secours
            if not city_slug:
                city_slug = simple_slugify(s_name)

            # 3. Construit l'URL complète
            prefix = f"{BASE_URL}"
            if current_lang != "fr":
                prefix += f"/{current_lang}"
            
            link_url = f"{prefix}/bus/{city_slug}"

            results.append({
                "name": s_name,
                "url": link_url
            })
        
        # On limite à 80 destinations pour ne pas surcharger le DOM inutilement
        return results[:80]
        
    except Exception as e:
        app.logger.error(f"Erreur SSR connected_stops : {e}")
        return []

def city_seo_page(url_slug, lang_code=None):
    current_lang = normalize_lang(lang_code)
    
    # 1. Recherche dans TOP_HUBS (Prioritaire)
    internal_key, city_info = find_city_by_slug(url_slug)
    
    # 2. FALLBACK : Si pas dans TOP_HUBS, on cherche dans le GTFS
    is_generic_city = False
    if not city_info:
        city_info = try_find_stop_by_slug(url_slug)
        is_generic_city = True
    
    # 3. Si toujours rien, redirection vers l'accueil
    if not city_info:
        return redirect(url_for('index', lang_code=normalize_lang(lang_code)))
        
    city_name = city_info["name"]
    stop_id = city_info["id"]
    
    # Textes SEO
    seo_titles = {
    "fr": f"Bus depuis {city_name} : Lignes directes FlixBus et BlaBlaCar",
    "en": f"Buses from {city_name}: Direct routes by FlixBus & BlaBlaCar",
    "de": f"Fernbus ab {city_name}: Direkte Routen von FlixBus & BlaBlaCar",
    "es": f"Autobuses desde {city_name}: Rutas directas de FlixBus y BlaBlaCar",
    "pt": f"Autocarros de {city_name}: Rotas diretas da FlixBus e BlaBlaCar",
    "nl": f"Bussen van {city_name}: Directe routes van FlixBus & BlaBlaCar",
    "sq": f"Autobusë nga {city_name}: Linja direkte nga FlixBus dhe BlaBlaCar",
    "ca": f"Autobusos des de {city_name}: Rutes directes de FlixBus i BlaBlaCar",
    "hr": f"Autobusi od {city_name}: Izravne rute FlixBus i BlaBlaCar",
    "bg": f"Автобуси от {city_name}: Директни маршрути на FlixBus и BlaBlaCar",
    "da": f"Busser fra {city_name}: Direkte ruter med FlixBus & BlaBlaCar",
    "et": f"Bussid {city_name}st: FlixBusi ja BlaBlaCar'i otseliinid",
    "fi": f"Bussit {city_name}stä: FlixBusin ja BlaBlaCarin suorat reitit",
    "el": f"Λεωφορεία από {city_name}: Απευθείας διαδρομές με FlixBus και BlaBlaCar",
    "hu": f"Buszok {city_name}-ból: FlixBus és BlaBlaCar közvetlen útvonalai",
    "hi": f"{city_name} से बसें: फ्लिक्सबस और ब्लाब्लाकार द्वारा सीधे मार्ग",
    "lv": f"Autobusi no {city_name}: FlixBus un BlaBlaCar tiešie maršruti",
    "lt": f"Autobusai iš {city_name}: Tiesioginiai maršrutai su FlixBus ir BlaBlaCar",
    "lb": f"Busse vu {city_name}: Direkt Strecke vu FlixBus & BlaBlaCar",
    "mk": f"Автобуси од {city_name}: Директни линии на FlixBus и BlaBlaCar",
    "ro": f"Autobuze din {city_name}: Rute directe FlixBus și BlaBlaCar",
    "pl": f"Autobusy z {city_name}: Bezpośrednie trasy FlixBus i BlaBlaCar",
    "cs": f"Autobusy z {city_name}: Přímé trasy FlixBus a BlaBlaCar",
    "sk": f"Autobusy z {city_name}: Priame trasy FlixBus a BlaBlaCar",
    "sl": f"Avtobusi iz {city_name}: Neposredne poti FlixBus in BlaBlaCar",
    "sv": f"Bussar från {city_name}: Direkta rutter med FlixBus & BlaBlaCar",
    "tr": f"{city_name} şehrinden otobüsler: FlixBus ve BlaBlaCar ile direkt hatlar",
    "uk": f"Автобуси з {city_name}: Прямі рейси FlixBus та BlaBlaCar",
    "ru": f"Автобусы из {city_name}: Прямые рейсы FlixBus и BlaBlaCar",
    "be": f"Аўтобусы з {city_name}: Прамыя рэйсы FlixBus і BlaBlaCar",
}

    seo_descs = {
    "fr": f"Découvrez toutes les destinations et lignes de bus directes au départ de {city_name}. Comparez Flixbus et BlaBlaCar sur notre carte interactive.",
    "en": f"Discover all destinations and direct bus routes departing from {city_name}. Compare FlixBus and BlaBlaCar on our interactive map.",
    "de": f"Entdecken Sie alle Ziele und direkte Busverbindungen ab {city_name}. Vergleichen Sie FlixBus und BlaBlaCar auf unserer interaktiven Karte.",
    "es": f"Descubre todos los destinos y rutas de autobús directas que salen de {city_name}. Compara FlixBus y BlaBlaCar en nuestro mapa interactivo.",
    "pt": f"Descubra todos os destinos e rotas de autocarros diretos com partida de {city_name}. Compare a FlixBus e a BlaBlaCar no nosso mapa interativo.",
    "nl": f"Ontdek alle bestemmingen en directe busroutes vertrekkend vanuit {city_name}. Vergelijk FlixBus en BlaBlaCar op onze interactieve kaart.",
    "sq": f"Zbuloni të gjitha destinacionet dhe linjat direkte të autobusëve që nisen nga {city_name}. Krahasoni FlixBus dhe BlaBlaCar në hartën tonë interaktive.",
    "ca": f"Descobreix totes les destinacions i rutes d'autobús directes que surten de {city_name}. Compara FlixBus i BlaBlaCar al nostre mapa interactiu.",
    "hr": f"Otkrijte sve destinacije i izravne autobusne rute koje polaze iz {city_name}. Usporedite FlixBus i BlaBlaCar na našoj interaktivnoj karti.",
    "bg": f"Открийте всички дестинации и директни автобусни линии, тръгващи от {city_name}. Сравнете FlixBus и BlaBlaCar на нашата интерактивна карта.",
    "da": f"Opdag alle destinationer og direkte busruter, der afgår fra {city_name}. Sammenlign FlixBus og BlaBlaCar på vores interaktive kort.",
    "et": f"Avastage kõik sihtkohad ja otseliinid, mis väljuvad {city_name}st. Võrrelge FlixBusi ja BlaBlaCar'i meie interaktiivsel kaardil.",
    "fi": f"Löydä kaikki kohteet ja suorat bussireitit, jotka lähtevät {city_name}stä. Vertaile FlixBussia ja BlaBlaCaria interaktiivisella kartallamme.",
    "el": f"Ανακαλύψτε όλους τους προορισμούς και τα απευθείας δρομολόγια λεωφορείων που αναχωρούν από {city_name}. Συγκρίνετε τα FlixBus και BlaBlaCar στον διαδραστικό μας χάρτη.",
    "hu": f"Fedezze fel az összes úti célt és közvetlen buszjáratot, amely {city_name} városból indul. Hasonlítsa össze a FlixBus-t és a BlaBlaCar-t interaktív térképünkön.",
    "hi": f"{city_name} से निकलने वाले सभी गंतव्यों और सीधे बस मार्गों की खोज करें। हमारे इंटरैक्टिव मानचित्र पर FlixBus और BlaBlaCar की तुलना करें।",
    "lv": f"Atklājiet visus galamērķus un tiešos autobusu maršrutus, kas izbrauc no {city_name}. Salīdziniet FlixBus un BlaBlaCar mūsu interaktīvajā kartē.",
    "lt": f"Atraskite visas kelionės kryptis ir tiesioginius autobusų maršrutus, išvykstančius iš {city_name}. Palyginkite „FlixBus“ ir „BlaBlaCar“ mūsų interaktyviame žemėlapyje.",
    "lb": f"Entdeckt all Destinatiounen an direkt Busstrecken déi vu {city_name} fortfueren. Vergläicht FlixBus a BlaBlaCar op eiser interaktiver Kaart.",
    "mk": f"Откријте ги сите дестинации и директни автобуски линии кои поаѓаат од {city_name}. Споредете ги FlixBus и BlaBlaCar на нашата интерактивна мапа.",
    "ro": f"Descoperiți toate destinațiile și rutele directe de autobuz care pleacă din {city_name}. Comparați FlixBus și BlaBlaCar pe harta noastră interactivă.",
    "pl": f"Odkryj wszystkie destynacje i bezpośrednie trasy autobusowe odjeżdżające z {city_name}. Porównaj FlixBus i BlaBlaCar na naszej interaktywnej mapie.",
    "cs": f"Objevte všechny destinace a přímé autobusové trasy odjíždějící z {city_name}. Porovnejte FlixBus a BlaBlaCar na naší interaktivní mapě.",
    "sk": f"Objavte všetky destinácie a priame autobusové trasy odchádzajúce z {city_name}. Porovnajte FlixBus a BlaBlaCar na našej interaktívnej mape.",
    "sl": f"Odkrijte vse destinacije in neposredne avtobusne poti, ki odhajajo iz {city_name}. Primerjajte FlixBus in BlaBlaCar na našem interaktivnem zemljevidu.",
    "sv": f"Upptäck alla destinationer och direkta busslinjer som avgår från {city_name}. Jämför FlixBus och BlaBlaCar på vår interaktiva karta.",
    "tr": f"{city_name} şehrinden kalkan tüm destinasyonları ve doğrudan otobüs hatlarını keşfedin. FlixBus ve BlaBlaCar'ı interaktif haritamızda karşılaştırın.",
    "uk": f"Відкрийте для себе всі напрямки та прямі автобусні рейси, що відправляються з {city_name}. Порівняйте FlixBus та BlaBlaCar на нашій інтерактивній карті.",
    "ru": f"Откройте для себя все направления и прямые автобусные рейсы, отправляющиеся из {city_name}. Сравните FlixBus и BlaBlaCar на нашей интерактивной карте.",
    "be": f"Адкрыйце для сябе ўсе кірункі і прамыя аўтобусныя рэйсы, якія адпраўляюцца з {city_name}. Параўнайце FlixBus і BlaBlaCar на нашай інтэрактыўнай карце.",
}   
    
    title = seo_titles.get(current_lang, seo_titles.get("en", f"Bus from {city_name}"))
    desc = seo_descs.get(current_lang, seo_descs.get("en", f"Direct routes from {city_name}"))
    
    lang_urls = {}
    if not is_generic_city:
        # Pour les TOP_HUBS on a des belles URLs traduites
        lang_urls = build_lang_urls("city", path_slug=internal_key)
    else:
        # Pour le fallback, on garde le slug actuel sur toutes les langues
        current_path = f"bus/{url_slug}"
        lang_urls = {
            "x-default": f"{BASE_URL}/{current_path}",
            current_lang: f"{BASE_URL}/{current_lang if current_lang != 'fr' else ''}/{current_path}".replace('//', '/')
        }

    current_url = lang_urls.get(current_lang, BASE_URL + "/")
    og_locale = OG_LOCALES.get(current_lang, OG_LOCALES.get(DEFAULT_LANG))
    og_locale_alternates = [OG_LOCALES[l] for l in SUPPORTED_LANGS if l in OG_LOCALES and l != current_lang]
    
    custom_seo = {
        "page_title": title,
        "page_description": desc,
        "canonical_url": current_url,
        "og_title": title,
        "og_description": desc,
        "og_url": current_url,
        "og_locale": og_locale,
        "og_locale_alternates": og_locale_alternates,
        "hreflang_urls": lang_urls,
    }

    # -- L'ARME FATALE SEO : On récupère les liaisons côté serveur --
    connected_dests = get_ssr_connected_stops(stop_id, current_lang)
    
    return _render_page(
        page_key="city", 
        lang_code=current_lang, 
        template_name="map.html", 
        path_slug=f"bus/{url_slug}", 
        seo_meta_override=custom_seo,
        preloaded_stop_id=stop_id,
        preloaded_stop_name=city_name,
        connected_destinations=connected_dests # <-- Injection des données
    )

# --- ROUTES STATIQUES ---

@app.route('/download/gtfs_unifie')
def download_unified_gtfs():
    try:
        static_downloads_path = os.path.join(app.root_path, app.static_folder, 'downloads')
        return send_from_directory(static_downloads_path, 'gtfs_unifie.zip', as_attachment=True)
    except Exception:
        abort(404)

@app.route('/robots.txt')
def robots_txt():
    return send_from_directory(app.static_folder, request.path[1:])

@app.route('/sitemap.xml')
def sitemap():
    pages = ["home", "map", "planner", "about", "legal"]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
    
    for page in pages:
        urls = build_lang_urls(page)
        for lang in SUPPORTED_LANGS:
            if lang not in urls: continue
            xml += f'  <url>\n    <loc>{urls[lang]}</loc>\n'
            for alt_lang, alt_url in urls.items():
                xml += f'    <xhtml:link rel="alternate" hreflang="{alt_lang}" href="{alt_url}" />\n'
            xml += '  </url>\n'

    for city_key in TOP_HUBS.keys():
        urls = build_lang_urls("city", path_slug=city_key)
        for lang in SUPPORTED_LANGS:
            if lang not in urls: continue
            xml += f'  <url>\n    <loc>{urls[lang]}</loc>\n'
            for alt_lang, alt_url in urls.items():
                xml += f'    <xhtml:link rel="alternate" hreflang="{alt_lang}" href="{alt_url}" />\n'
            xml += '  </url>\n'
            
    xml += '</urlset>'
    return Response(xml, mimetype='application/xml')

# --- API ENDPOINTS ---

@app.route('/api/search_stops', methods=['GET'])
def api_search_stops():
    query_term = request.args.get('query', default='', type=str).strip()
    
    if not query_term or len(query_term) < 2: 
        return jsonify([]), 200
        
    if "stops" not in data_frames or data_frames["stops"] is None:
        return jsonify({"error": "Data not loaded"}), 500
        
    stops_df = data_frames["stops"]
    query_lower = query_term.lower()
    
    # 1. On crée un ensemble de termes de recherche
    # On y met toujours ce que l'utilisateur tape (pour trouver les villes normales)
    search_targets = {query_term}
    
    # 2. On parcourt le dictionnaire de synonymes
    for synonym, standard_name in SEARCH_SYNONYMS.items():
        # Si ce que l'utilisateur tape est LE DÉBUT d'un synonyme
        # Exemple : "vars" est au début de "varsovie" -> on ajoute "Warsaw" aux cibles
        if synonym.startswith(query_lower):
            search_targets.add(standard_name)
    
    try:
        # 3. On construit un filtre combiné pour Pandas
        # On initialise un masque avec des "False" partout
        mask = pd.Series(False, index=stops_df.index)
        
        # On ajoute (avec l'opérateur OR '|') chaque cible trouvée au masque
        for target in search_targets:
            mask = mask | stops_df['stop_name'].astype(str).str.contains(target, case=False, na=False, regex=False)
            
        matching_stops = stops_df[mask]
        
    except Exception as e:
        app.logger.error(f"Search error: {e}")
        return jsonify({"error": "Internal search error"}), 500
        
    # On renvoie les 10 premiers résultats
    results = [{"stop_id": row['stop_id'], "stop_name": row['stop_name']} for _, row in matching_stops.head(10).iterrows()]
    return jsonify(results)

@app.route('/api/stop_info/<stop_id>', methods=['GET'])
def api_get_stop_info(stop_id):
    try:
        data = get_stop_info_and_routes(stop_id)
        if "error" in data: return jsonify(data), 404
        return jsonify(data)
    except Exception: return jsonify({"error": "Server error"}), 500

@app.route('/api/trip_details/<trip_id>', methods=['GET'])
def api_get_trip_details(trip_id):
    try:
        data = get_trip_details_and_shape(trip_id)
        if "error" in data: return jsonify(data), 404
        return jsonify(data)
    except Exception: return jsonify({"error": "Server error"}), 500

@app.route('/api/connected_stops/<stop_id>', methods=['GET'])
def api_get_connected_stops(stop_id):
    required_dfs = ["stops", "stop_times", "trips"]
    if not all(key in data_frames and not data_frames[key].empty for key in required_dfs):
        return jsonify({"error": "Données GTFS non chargées."}), 500

    stops_df = data_frames["stops"]
    stop_times_df = data_frames["stop_times"]
    trips_df = data_frames["trips"]

    stop_exists = stops_df[stops_df['stop_id'] == str(stop_id)]
    if stop_exists.empty:
        return jsonify({"error": f"Arrêt non trouvé."}), 404

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

        return jsonify(results)

    except Exception as e:
        app.logger.error(f"Erreur API connected_stops : {e}")
        return jsonify({"error": "Erreur interne."}), 500

if __name__ == "__main__":
    app.logger.info("--- DÉMARRAGE MODE DÉVELOPPEMENT ---")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))