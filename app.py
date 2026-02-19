import pandas as pd
import os
import logging
import json
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import traceback

GTFS_DATA_PATH = os.path.join("output_gtfs", "unified")

# SEO / internationalisation configuration
BASE_URL = "https://liniabus.eu"
# Doit refléter toutes les langues disponibles dans static/i18n.js
SUPPORTED_LANGS = [
    "fr",
    "en",
    "de",
    "es",
    "pt",
    "nl",
    "sq",
    "ca",
    "hr",
    "bg",
    "da",
    "et",
    "fi",
    "el",
    "hu",
    "hi",
    "lv",
    "lt",
    "lb",
    "mk",
    "ro",
    "pl",
    "cs",
    "sk",
    "sl",
    "sv",
    "tr",
    "uk",
    "ru",
    "be",
]
DEFAULT_LANG = "fr"

# Simple mapping for Open Graph locales
OG_LOCALES = {
    "fr": "fr_FR",
    "en": "en_GB",
    "de": "de_DE",
    "es": "es_ES",
    "it": "it_IT",
    "nl": "nl_NL",
    "pt": "pt_PT",
    "pl": "pl_PL",
    "sq": "sq_AL",
    "ca": "ca_ES",
    "hr": "hr_HR",
    "bg": "bg_BG",
    "da": "da_DK",
    "et": "et_EE",
    "fi": "fi_FI",
    "el": "el_GR",
    "hu": "hu_HU",
    "hi": "hi_IN",
    "lv": "lv_LV",
    "lt": "lt_LT",
    "lb": "lb_LU",
    "mk": "mk_MK",
    "ro": "ro_RO",
    "cs": "cs_CZ",
    "sk": "sk_SK",
    "sl": "sl_SI",
    "sv": "sv_SE",
    "tr": "tr_TR",
    "uk": "uk_UA",
    "ru": "ru_RU",
    "be": "be_BY",
}

# Centralised SEO metadata per page and language
SEO_CONFIG = {
    "home": {
        "fr": {
            "title": "Linia - Planificateur d'Itinéraire Bus | FlixBus BlaBlaCar",
            "description": "Planifiez votre voyage en bus avec Linia. Visualisez les lignes FlixBus et BlaBlaCar Bus sur une carte interactive, comparez les connexions et créez vos itinéraires personnalisés.",
        },
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
    Construit les URLs par langue et la version x-default pour une page donnée.
    - page_key: clé dans SEO_CONFIG (ex: 'home', 'map', ...)
    - path_slug: segment de chemin sans langue ('', 'map', 'planner', ...)
    """
    if path_slug is None:
        path_slug = ""

    def _path_for(lang: str) -> str:
        # FR reste à la racine sans préfixe de langue
        if lang == "fr":
            if path_slug:
                return f"/{path_slug}"
            return "/"
        # autres langues avec préfixe
        if path_slug:
            return f"/{lang}/{path_slug}"
        return f"/{lang}/"

    urls = {}
    for lang in SUPPORTED_LANGS:
        urls[lang] = BASE_URL + _path_for(lang)

    # x-default pointe sur la racine (FR par défaut)
    urls["x-default"] = BASE_URL + "/"
    return urls


def get_seo_meta(page_key: str, lang: str, path_slug: str | None = None) -> dict:
    """
    Retourne un dict avec les champs SEO de base pour une page et une langue données.
    """
    lang = normalize_lang(lang)
    page_conf = SEO_CONFIG.get(page_key, {})
    lang_conf = page_conf.get(lang) or page_conf.get(DEFAULT_LANG, {})

    lang_urls = build_lang_urls(page_key, path_slug=path_slug)
    current_url = lang_urls.get(lang, BASE_URL + "/")

    title = lang_conf.get("title", "Linia")
    description = lang_conf.get(
        "description",
        "Linia - Visualisation et planification de lignes de bus longue distance en Europe.",
    )

    og_locale = OG_LOCALES.get(lang, OG_LOCALES.get(DEFAULT_LANG))
    og_locale_alternates = [
        OG_LOCALES[l] for l in SUPPORTED_LANGS if l in OG_LOCALES and l != lang
    ]

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
    """
    Construit les blocs JSON-LD pour la page courante.
    Retourne une chaîne JSON ou None.
    """
    data = []

    if page_key == "home":
        data.append(
            {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "Linia",
                "url": BASE_URL + "/",
                "logo": BASE_URL + "/static/logo.png",
            }
        )
        data.append(
            {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": "Linia - Bus Route Planner",
                "url": BASE_URL + "/",
                "potentialAction": {
                    "@type": "SearchAction",
                    "target": BASE_URL + "/planner?q={search_term_string}",
                    "query-input": "required name=search_term_string",
                },
            }
        )

    if page_key == "planner":
        data.append(
            {
                "@context": "https://schema.org",
                "@type": "Trip",
                "name": "European bus itinerary planner",
                "description": "Interactive tool to plan multi-step bus itineraries across Europe using FlixBus and BlaBlaCar routes.",
                "url": current_url,
                "provider": {
                    "@type": "Organization",
                    "name": "Linia",
                    "url": BASE_URL + "/",
                },
                "areaServed": {
                    "@type": "AdministrativeArea",
                    "name": "Europe",
                },
            }
        )

    if page_key == "about" and lang == "fr":
        # FAQ générique à propos de Linia (FR uniquement pour l’instant)
        data.append(
            {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": "Linia est-il gratuit ?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Oui, l'outil est entièrement gratuit et sans publicité."
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "Quels sont les pays couverts par Linia ?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Linia couvre principalement l'Europe : France, Allemagne, Espagne, Italie, Benelux, et d'autres pays européens desservis par FlixBus et BlaBlaCar Bus."
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "À quelle fréquence les données sont-elles mises à jour ?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Les données GTFS sont mises à jour le premier jour de chaque mois."
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "Comment signaler une erreur ou proposer une amélioration ?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Vous pouvez ouvrir une issue sur le dépôt GitHub du projet ou contacter le développeur via contact@liniabus.eu"
                        },
                    },
                ],
            }
        )

    # Breadcrumbs pour toutes les pages principales
    if page_key in {"home", "map", "planner", "about", "legal"}:
        items = [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Linia",
                "item": BASE_URL + "/",
            }
        ]
        if page_key != "home":
            name_map = {
                "map": "Map",
                "planner": "Planner",
                "about": "About",
                "legal": "Legal",
            }
            items.append(
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": name_map.get(page_key, page_key.title()),
                    "item": current_url,
                }
            )

        data.append(
            {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": items,
            }
        )

    if not data:
        return None

    try:
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return None


app = Flask(__name__)
CORS(app)

log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
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

def _render_page(page_key: str, lang_code: str | None, template_name: str, path_slug: str | None = None):
    """
    Helper générique pour rendre une page avec le contexte SEO / i18n.
    """
    current_lang = normalize_lang(lang_code)
    seo_meta = get_seo_meta(page_key, current_lang, path_slug=path_slug)
    structured_jsonld = get_structured_data(
        page_key, current_lang, seo_meta.get("canonical_url", BASE_URL + "/")
    )

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
    }
    return render_template(template_name, **context)


@app.route("/")
@app.route("/<lang_code>/")
def index(lang_code=None):
    app.logger.debug(f"Requête pour la page d'accueil depuis {request.remote_addr}")
    return _render_page("home", lang_code, "landing.html", path_slug="")

@app.route("/map")
@app.route("/<lang_code>/map")
def map_page(lang_code=None):
    app.logger.debug(f"Requête pour la page carte depuis {request.remote_addr}")
    return _render_page("map", lang_code, "map.html", path_slug="map")

@app.route("/about")
@app.route("/<lang_code>/about")
def about_page(lang_code=None):
    app.logger.debug(f"Requête pour la page à propos depuis {request.remote_addr}")
    return _render_page("about", lang_code, "about.html", path_slug="about")

@app.route("/planner")
@app.route("/<lang_code>/planner")
def planner_page(lang_code=None):
    app.logger.debug(f"Requête pour la page planificateur depuis {request.remote_addr}")
    return _render_page("planner", lang_code, "planner.html", path_slug="planner")

@app.route("/legal")
@app.route("/<lang_code>/legal")
def legal_page(lang_code=None):
    app.logger.debug(f"Requête pour les mentions légales depuis {request.remote_addr}")
    return _render_page("legal", lang_code, "legal.html", path_slug="legal")

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

@app.route('/robots.txt')
@app.route('/sitemap.xml')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])

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