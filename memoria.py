"""Memoria de recetas: un recetario guardado en disco que la app consulta ANTES de llamar a la IA.

- recetario.json: el recetario base. Se genera una vez con cosecha.py y va en el repo.
- recetario_nuevas.json: lo que la IA va creando mientras la app anda (se aprende solo, mejor
  esfuerzo: si el servidor se reinicia o el disco es de solo lectura, simplemente se pierde).

sazona. y larefri. usan este mismo archivo sin cambios; solo necesitan nucleo.py.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import threading

import nucleo as n

_CARPETA = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_BASE = os.path.join(_CARPETA, "recetario.json")
ARCHIVO_NUEVAS = os.path.join(_CARPETA, "recetario_nuevas.json")

_cache: dict[str, tuple[float, list]] = {}     # ruta -> (fecha de modificación, [(Receta, categoria)])
_lock = threading.Lock()


def _leer(ruta: str) -> list:
    """Lee un recetario del disco (con caché: solo relee si el archivo cambió)."""
    try:
        mtime = os.path.getmtime(ruta)
    except OSError:
        return []
    if ruta in _cache and _cache[ruta][0] == mtime:
        return _cache[ruta][1]
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, ValueError):
        return []
    out = []
    for e in datos.get("recetas", []):
        try:
            out.append((n.Receta.model_validate(e["receta"]), e.get("categoria", "")))
        except Exception:  # noqa: BLE001   (una receta mala no tumba las demás)
            continue
    _cache[ruta] = (mtime, out)
    return out


def todas() -> list:
    """Base + aprendidas, sin nombres repetidos (si se repite, gana la del recetario base)."""
    vistos, out = set(), []
    for ruta in (ARCHIVO_BASE, ARCHIVO_NUEVAS):
        for r, cat in _leer(ruta):
            if r.nombre in vistos:
                continue
            vistos.add(r.nombre)
            out.append((r, cat))
    return out


def buscar(cocina: str = "", categoria: str = "", dieta: str = "Todas", max_porcion: float | None = None,
           tiempo: int | None = None, excluir=(), cantidad: int | None = None) -> list:
    """Recetas guardadas que cumplen los filtros, ordenadas de más barata a más cara por porción."""
    ex = {n._clave(x) for x in excluir}
    out = []
    for r, cat in todas():
        if cocina and n._clave(r.cocina) != n._clave(cocina):
            continue
        if categoria and cat != categoria:
            continue
        if n._clave(r.nombre) in ex:
            continue
        if tiempo is not None and r.tiempo_minutos > tiempo + 15:
            continue
        if not n.cumple_dieta(r, dieta):
            continue
        if max_porcion is not None and n.costo_porcion(r) > max_porcion * 1.1:
            continue
        out.append(r)
    out.sort(key=n.costo_porcion)
    return out[:cantidad] if cantidad else out


def muestra_diaria(dia: str, cantidad: int, **filtros) -> list:
    """Una selección barajada del recetario: igual durante todo el día, distinta al día siguiente."""
    clave = "|".join([dia, filtros.get("cocina", ""), filtros.get("categoria", ""), filtros.get("dieta", "")])
    semilla = int(hashlib.sha256(clave.encode("utf-8")).hexdigest(), 16)
    out = buscar(**filtros)
    random.Random(semilla).shuffle(out)
    return out[:cantidad]


def aprender(recetas, categoria: str = "") -> None:
    """Guarda recetas nuevas que creó la IA (mejor esfuerzo: si no se puede escribir, no pasa nada)."""
    if not recetas:
        return
    vistos = {r.nombre for r, _ in todas()}
    nuevas = []
    for r in recetas:
        if r.nombre in vistos:
            continue
        vistos.add(r.nombre)
        d = r.model_dump()
        for i in d.get("ingredientes", []):
            i.pop("de_tu_casa", None)            # eso depende de cada usuario: no se guarda
        nuevas.append({"categoria": categoria, "receta": d})
    if not nuevas:
        return
    with _lock:
        try:
            datos = {"version": 1, "recetas": []}
            if os.path.exists(ARCHIVO_NUEVAS):
                try:
                    with open(ARCHIVO_NUEVAS, encoding="utf-8") as f:
                        datos = json.load(f)
                except ValueError:
                    datos = {"version": 1, "recetas": []}
            ya = {e["receta"]["nombre"] for e in datos.get("recetas", [])}
            datos.setdefault("recetas", [])
            datos["recetas"] += [e for e in nuevas if e["receta"]["nombre"] not in ya]
            with open(ARCHIVO_NUEVAS, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False)
            _cache.pop(ARCHIVO_NUEVAS, None)
            print(f"[memoria] aprendí {len(nuevas)} receta(s) nueva(s)", flush=True)
        except OSError as e:
            print(f"[memoria] no pude guardar: {e}", flush=True)
