"""Cosecha: genera el recetario base (recetario.json) pidiéndole tandas de recetas a la IA UNA sola vez.

Uso (con la clave de Gemini en el ambiente):
    set GEMINI_API_KEY=tu-clave          (Windows)
    export GEMINI_API_KEY=tu-clave       (Mac/Linux)
    python cosecha.py                    # ~10 recetas por cada país y categoría (unas 700)
    python cosecha.py --por-combo 15     # más recetas por combinación
    python cosecha.py --solo Ecuador     # solo una cocina (la que se ve en los botones)

Es reanudable: si recetario.json ya existe, NO repite recetas; puedes pararlo y seguir después.
Cuando termina, recetario.json se sube al repo de sazona. y al de larefri. (el mismo archivo).
"""

from __future__ import annotations

import argparse
import json
import os
import time

import nucleo as n

PERSONAS_BASE = 4          # las recetas se guardan para 4; cada app las escala a lo que elija el usuario
MAX_PORCION = 2.5
TIEMPO_MAX = 60


def main():
    ap = argparse.ArgumentParser(description="Genera el recetario base de sazona./larefri.")
    ap.add_argument("--por-combo", type=int, default=10, help="recetas por cada combinación país × categoría")
    ap.add_argument("--solo", default="", help="solo esta cocina, tal como sale en los botones (p. ej. Ecuador)")
    ap.add_argument("--salida", default="recetario.json", help="archivo del recetario (se actualiza solo)")
    args = ap.parse_args()

    clave = os.environ.get("GEMINI_API_KEY")
    if not clave:
        raise SystemExit("Falta la clave: define GEMINI_API_KEY en el ambiente y vuelve a correr.")
    from google import genai
    cliente = genai.Client(api_key=clave)

    datos = {"version": 1, "recetas": []}
    if os.path.exists(args.salida):
        with open(args.salida, encoding="utf-8") as f:
            datos = json.load(f)
    vistos = {e["receta"]["nombre"] for e in datos.get("recetas", [])}
    print(f"Recetario actual: {len(vistos)} recetas. Cosechando...", flush=True)

    paises = {args.solo: n.PAISES[args.solo]} if args.solo else n.PAISES
    for pais, cocina in paises.items():
        for categoria in n.CATEGORIAS:
            faltan = args.por_combo - sum(1 for e in datos["recetas"]
                                          if e.get("categoria") == categoria
                                          and n._clave(e["receta"].get("cocina", "")) == n._clave(cocina))
            intentos = 0
            while faltan > 0 and intentos < 3:
                intentos += 1
                excluir = [e["receta"]["nombre"] for e in datos["recetas"]
                           if n._clave(e["receta"].get("cocina", "")) == n._clave(cocina)]
                try:
                    recetas, _ = n.buscar_recetas(cliente, [cocina], PERSONAS_BASE, MAX_PORCION, TIEMPO_MAX,
                                                  cantidad=faltan + 3, categoria=categoria, excluir=excluir)
                except n.ErrorIA as e:
                    print(f"[cosecha] {pais}/{categoria}: {e}", flush=True)
                    break
                nuevas = 0
                for r in recetas:
                    if r.nombre in vistos:
                        continue
                    vistos.add(r.nombre)
                    datos["recetas"].append({"categoria": categoria, "receta": r.model_dump()})
                    nuevas += 1
                faltan -= nuevas
                with open(args.salida, "w", encoding="utf-8") as f:
                    json.dump(datos, f, ensure_ascii=False, indent=1)
                print(f"[cosecha] {pais}/{categoria}: +{nuevas} (total {len(datos['recetas'])})", flush=True)
                if not nuevas:
                    break                                   # la IA no dio nada nuevo: no insistir
                time.sleep(2)                               # cuidar la cuota de la IA
    print(f"LISTO: {len(datos['recetas'])} recetas en {args.salida}. "
          "Súbelo al repo de sazona. y al de larefri. (el mismo archivo).", flush=True)


if __name__ == "__main__":
    main()
