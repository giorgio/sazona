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


def _texto_plano(valor: str) -> str:
    sin_etiquetas = re.sub(r"<[^>]+>", "", valor or "")
    return " ".join(html.unescape(sin_etiquetas).split())[:60]


def foto_commons(consulta: str) -> dict | None:
    try:
        r = requests.get(
            COMMONS_API,
            params={"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
                    "gsrlimit": 6, "gsrsearch": f"{consulta} filetype:bitmap", "prop": "imageinfo",
                    "iiprop": "url|extmetadata", "iiurlwidth": 900,
                    "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl"},
            headers={"User-Agent": USER_AGENT},
            timeout=8,
        )
        r.raise_for_status()
        paginas = (r.json().get("query") or {}).get("pages") or {}
    except (requests.RequestException, ValueError):
        return None
    for p in sorted(paginas.values(), key=lambda x: x.get("index", 99)):
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
                         headers={"Authorization": clave}, timeout=8)
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
    if f is None and len(consulta.split()) > 2:  # segunda oportunidad con una búsqueda más corta
        f = foto_commons(" ".join(consulta.split()[:2]))
    return f
