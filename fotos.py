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
UNSPLASH_BUSQUEDA = "https://api.unsplash.com/search/photos"
APP = "sazona"
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


# Palabras que dicen QUÉ PLATO es (no un ingrediente): si la búsqueda tiene una, la foto debe mostrarla
TIPO_PLATO = {"salad", "soup", "stew", "sandwich", "omelette", "omelet", "tortilla", "scrambled", "fried", "ceviche",
              "curry", "pasta", "spaghetti", "noodles", "risotto", "pizza", "burger", "taco", "tacos", "burrito",
              "empanada", "empanadas", "cake", "pie", "pudding", "smoothie", "juice", "porridge", "oatmeal", "pancake",
              "pancakes", "casserole", "roast", "grilled", "baked", "skewer", "skewers", "dumplings", "wrap", "bowl",
              "chowder", "broth", "puree", "mash", "mashed", "patties", "fritters", "croquettes", "rolls", "tart",
              "toast", "breakfast", "plantain", "locro", "encebollado", "bolon", "menestra"}


# La base y la proteína tienen que coincidir: arroz no es fideo, pollo no es pescado
GRUPOS = [
    {"rice": ("rice",), "noodles": ("noodle", "ramen", "lo mein", "chow mein"), "pasta": ("pasta", "spaghetti", "macaroni", "penne", "lasagna"),
     "potato": ("potato", "fries"), "bread": ("bread", "toast", "sandwich", "bun"), "quinoa": ("quinoa",),
     "plantain": ("plantain",), "tortilla": ("tortilla", "taco", "burrito")},
    {"chicken": ("chicken",), "beef": ("beef", "steak"), "pork": ("pork", "bacon", "ham"), "fish": ("fish", "salmon", "tuna", "tilapia"),
     "shrimp": ("shrimp", "prawn"), "egg": ("egg",)},
]


def _choca(t: str, palabras: list[str]) -> bool:
    """True si la foto no tiene la base/proteína de la receta o muestra otra que choca con ella."""
    q = " ".join(palabras)
    bases, proteinas = GRUPOS
    for grupo, estricto in ((bases, False), (proteinas, True)):
        en_receta = {k for k, vs in grupo.items() if any(v in q for v in vs)}
        en_foto = {k for k, vs in grupo.items() if any(v in t for v in vs)}
        if en_receta and not (en_receta & en_foto):
            return True                     # la receta es de arroz y la foto no tiene arroz
        extra = en_foto - en_receta
        if extra and (en_receta or estricto):
            return True                     # arroz -> fideos en la foto; ensalada sin carne -> pollo en la foto
    return False


def es_del_plato(titulo: str, palabras: list[str], minimo: int | None = None) -> bool:
    """La foto sirve solo si su nombre menciona el plato (2 palabras si hay 2 o más) y no es otra cosa."""
    t = (titulo or "").lower().replace("_", " ")
    if any(x in t for x in NO_ES_PLATO):
        return False
    if _choca(t, palabras):
        return False
    tipos = [w for w in palabras if w in TIPO_PLATO]
    if tipos and not any(_raiz(w) in t for w in tipos):
        return False                                  # "tomato salad" no acepta una foto de tomates sueltos
    raices = {_raiz(w) for w in palabras}
    aciertos = sum(1 for r in raices if r and r in t)
    if minimo is None:
        minimo = 2 if len(raices) >= 2 else 1
    return aciertos >= minimo


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


def avisar_descarga(f: dict, clave: str) -> None:
    """Unsplash pide avisar cuando la app usa una foto (cuenta para el fotógrafo). Si falla, no pasa nada."""
    url = (f.get("links") or {}).get("download_location")
    if not url:
        return
    try:
        requests.get(url, headers={"Authorization": f"Client-ID {clave}", "Accept-Version": "v1"}, timeout=3)
    except requests.RequestException:
        pass


def _unsplash(query: str, clave: str) -> list[dict]:
    try:
        r = requests.get(UNSPLASH_BUSQUEDA, params={"query": query, "per_page": 10, "orientation": "landscape",
                                                     "content_filter": "high", "order_by": "relevant"},
                         headers={"Authorization": f"Client-ID {clave}", "Accept-Version": "v1"}, timeout=4)
        if r.status_code != 200:
            print(f"[foto] Unsplash respondió {r.status_code} (quedan {r.headers.get('X-Ratelimit-Remaining', '?')})", flush=True)
            return []
        return r.json().get("results") or []
    except (requests.RequestException, ValueError):
        return []


def _texto_unsplash(f: dict) -> str:
    tags = " ".join(t.get("title", "") for t in (f.get("tags") or []))
    return " ".join([f.get("alt_description") or "", f.get("description") or "", tags]).lower()


GASTRO = ("plate", "bowl", "dish", "served", "table", "close-up", "closeup", "meal", "food photography",
          "restaurant", "plated", "breakfast", "lunch", "dinner")


def candidatos_unsplash(consulta: str, clave: str, maximo: int = 3) -> list[dict]:
    """Varias fotos posibles del plato, de la más probable a la menos (luego la IA las revisa una por una)."""
    palabras = palabras_plato(consulta)
    intentos = [consulta]
    if len(palabras) >= 2:
        intentos += [" ".join(palabras[:2]), " ".join(palabras[-2:])]
    vistos, salida, ids = set(), [], set()
    for q in intentos:
        if q in vistos or len(salida) >= maximo:
            continue
        vistos.add(q)
        fotos = _unsplash(q + " food", clave)            # 1 sola búsqueda por intento: la cuota es de 50 por hora
        fotos = [f for f in fotos if f.get("id") not in ids and not any(x in _texto_unsplash(f) for x in NO_ES_PLATO)]
        # primero las que nombran el plato y se ven servidas
        fotos.sort(key=lambda f: (-es_del_plato(_texto_unsplash(f), palabras, minimo=1),
                                  -sum(g in _texto_unsplash(f) for g in GASTRO)))
        for f in fotos[:maximo - len(salida)]:          # una sola búsqueda suele bastar (ahorra cuota)
            ids.add(f.get("id"))
            u = f.get("user") or {}
            utm = f"?utm_source={APP}&utm_medium=referral"
            salida.append({"url": (f.get("urls") or {}).get("regular"),
                           "url_chica": (f.get("urls") or {}).get("small") or (f.get("urls") or {}).get("regular"),
                           "autor": u.get("name") or "Unsplash",
                           "pagina": ((u.get("links") or {}).get("html") or "https://unsplash.com") + utm,
                           "licencia": "", "licencia_url": "", "fuente": "Unsplash",
                           "fuente_url": "https://unsplash.com/" + utm, "_crudo": f})
    return salida[:maximo]


def buscar_foto(consulta: str, clave_pexels: str | None = None, clave_unsplash: str | None = None,
                verificar=None) -> dict | None:
    """Devuelve {'url','autor','pagina','licencia','licencia_url','fuente'} o None.
    verificar(url_imagen) -> bool: si se pasa, cada candidata se muestra solo si la IA confirma que es el plato."""
    if not consulta:
        return None
    candidatas = []
    if clave_unsplash:
        candidatas += candidatos_unsplash(consulta, clave_unsplash)
    if clave_pexels:
        f = foto_pexels(consulta, clave_pexels)
        if f and f.get("url"):
            candidatas.append(f)
    def commons():
        f = foto_commons(consulta)
        corta = " ".join(palabras_plato(consulta)[-2:])
        if f is None and corta and corta != consulta.lower():
            f = foto_commons(corta)
        return [f] if f else []

    if not candidatas or verificar is None:
        candidatas += commons()
        probado_commons = True
    else:
        probado_commons = False
    print(f"[foto] {consulta!r}: {len(candidatas)} candidatas "
          f"({', '.join(sorted({c.get('fuente', '?') for c in candidatas})) or 'ninguna'})", flush=True)
    while candidatas:
        c = candidatas.pop(0)
        if verificar is not None and not verificar(c.get("url_chica") or c["url"]):
            if not candidatas and not probado_commons:   # ninguna de Unsplash sirvió: probar Wikimedia
                candidatas, probado_commons = commons(), True
            continue
        if c.get("fuente") == "Unsplash" and clave_unsplash:
            avisar_descarga(c.get("_crudo") or {}, clave_unsplash)
        return {k: v for k, v in c.items() if not k.startswith("_")}
    return None                                         # None: la app muestra el dibujo de la marca
