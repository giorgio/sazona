"""Fotos de los platos.

Fuente principal: Wikimedia Commons (fotos libres, sin clave). Se acredita al
autor y la licencia, con enlace a la página de la foto.
Opcional: Pexels, si hay PEXELS_API_KEY en los Secrets.
Si no aparece ninguna foto, la app muestra la ilustración de la marca.
"""

from __future__ import annotations

import html
import re

import requests

USER_AGENT = "sazon-app/1.0 (proyecto personal de recetas; https://github.com/giorgio)"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
PEXELS_BUSQUEDA = "https://api.pexels.com/v1/search"
LICENCIAS_OK = ("cc0", "public domain", "cc by", "cc-by", "dominio público")
# Palabras que no dicen QUÉ plato es (sin ellas, "Mexican salad" trae fotos de carreteras de México)
NO_PLATO = {"mexican", "ecuadorian", "ecuador", "italian", "italy", "chinese", "china", "peruvian", "peru",
            "indian", "india", "japanese", "japan", "thai", "mediterranean", "middle", "eastern", "east",
            "spanish", "french", "greek", "korean", "colombian", "argentinian", "style", "homemade", "healthy",
            "with", "and", "the", "dish", "food", "plate", "bowl", "recipe", "traditional", "fresh", "easy",
            "simple", "light", "vegan", "vegetarian", "served", "cooked"}


def palabras_plato(consulta: str) -> list[str]:
    ws = re.findall(r"[a-záéíóúñ]+", (consulta or "").lower())
    return [w for w in ws if len(w) > 2 and w not in NO_PLATO]


def _raiz(w: str) -> str:
    return w[:-3] if w.endswith("ies") else w[:-2] if w.endswith("es") and len(w) > 5 else w.rstrip("s")


# Fotos que NO son un plato servido aunque nombren el ingrediente (arrozal, mercado, planta...)
NO_ES_PLATO = ("field", "paddy", "plant", "farm", "crop", "harvest", "seed", "tree", "flower", "leaf", "leaves",
               "market", "stall", "vendor", "shop", "store", "street", "map", "flag", "logo", "icon", "sign",
               "label", "package", "packaging", "bag", "sack", "building", "church", "people", "portrait",
               "woman", "man ", "girl", "boy", "child", "festival", "statue", "museum", "drawing", "illustration",
               "diagram", "chart", "plantation", "cultivation", "garden", "raw", "kernel", "grain", "stamp",
               "coin", "poster", "advert", "menu", "truck", "farmer", "cooking class", "factory")


def es_del_plato(titulo: str, palabras: list[str]) -> bool:
    """La foto sirve solo si su nombre menciona el plato (2 palabras si hay 2 o más) y no es otra cosa."""
    t = (titulo or "").lower().replace("_", " ")
    if any(x in t for x in NO_ES_PLATO):
        return False
    raices = {_raiz(w) for w in palabras}
    aciertos = sum(1 for r in raices if r and r in t)
    return aciertos >= (2 if len(raices) >= 2 else 1)


def _texto_plano(valor: str) -> str:
    sin_etiquetas = re.sub(r"<[^>]+>", "", valor or "")
    return " ".join(html.unescape(sin_etiquetas).split())[:60]


def foto_commons(consulta: str) -> dict | None:
    try:
        r = requests.get(
            COMMONS_API,
            params={"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
                    "gsrlimit": 10, "gsrsearch": f"{consulta} food filetype:bitmap", "prop": "imageinfo",
                    "iiprop": "url|extmetadata", "iiurlwidth": 900,
                    "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl"},
            headers={"User-Agent": USER_AGENT},
            timeout=4,
        )
        r.raise_for_status()
        paginas = (r.json().get("query") or {}).get("pages") or {}
    except (requests.RequestException, ValueError):
        return False                                    # sin conexión: no vale la pena reintentar
    palabras = palabras_plato(consulta)
    for p in sorted(paginas.values(), key=lambda x: x.get("index", 99)):
        if not es_del_plato(p.get("title", ""), palabras):
            continue
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        licencia = (meta.get("LicenseShortName") or {}).get("value", "")
        if not info.get("thumburl") or not any(l in licencia.lower() for l in LICENCIAS_OK):
            continue
        return {"url": info["thumburl"], "autor": _texto_plano((meta.get("Artist") or {}).get("value", "")) or "Autor",
                "pagina": info.get("descriptionurl") or "https://commons.wikimedia.org",
                "licencia": licencia, "licencia_url": (meta.get("LicenseUrl") or {}).get("value", ""),
                "fuente": "Wikimedia Commons"}
    return None


def foto_pexels(consulta: str, clave: str) -> dict | None:
    try:
        r = requests.get(PEXELS_BUSQUEDA, params={"query": consulta, "per_page": 1, "orientation": "landscape"},
                         headers={"Authorization": clave}, timeout=4)
        if r.status_code != 200:
            return None
        f = (r.json().get("photos") or [None])[0]
    except (requests.RequestException, ValueError):
        return None
    if not f:
        return None
    src = f.get("src") or {}
    return {"url": src.get("landscape") or src.get("large"), "autor": f.get("photographer") or "Pexels",
            "pagina": f.get("url") or "https://www.pexels.com", "licencia": "", "licencia_url": "",
            "fuente": "Pexels"}


def buscar_foto(consulta: str, clave_pexels: str | None = None) -> dict | None:
    """Devuelve {'url','autor','pagina','licencia','licencia_url','fuente'} o None."""
    if not consulta:
        return None
    if clave_pexels:
        f = foto_pexels(consulta, clave_pexels)
        if f and f.get("url"):
            return f
    f = foto_commons(consulta)
    corta = " ".join(palabras_plato(consulta)[-2:])     # p. ej. "Mexican lentil salad" -> "lentil salad"
    if f is None and corta and corta != consulta.lower():   # solo si la primera respondió (f None, no False)
        f = foto_commons(corta)
    return f or None                                           # None: la app muestra el dibujo de la marca
