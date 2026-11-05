"""Pruebas de la memoria de recetas (memoria.py) con el recetario semilla recetario.json.
Corre:  python test_memoria.py"""

import os
import tempfile

import memoria
import nucleo as n

TODAS = memoria.todas()
assert len(TODAS) == 10, f"el recetario semilla tiene 10 recetas, salieron {len(TODAS)}"

# --- filtros de buscar() ---
assert len(memoria.buscar()) == 10
assert len(memoria.buscar(cocina="Ecuatoriana")) == 4, "4 ecuatorianas en la semilla"
assert len(memoria.buscar(categoria="Sopas")) == 2, "2 sopas en la semilla"
veganas = memoria.buscar(dieta="Vegana")
assert len(veganas) == 3, f"3 veganas (lentejas, pomodoro, aguacate), salieron {len(veganas)}"
assert all("Huevo" not in (r.alergenos or []) and "Lácteos" not in (r.alergenos or []) for r in veganas)
rapidas = memoria.buscar(tiempo=15)
assert all(r.tiempo_minutos <= 30 for r in rapidas), "tiempo=15 tolera hasta 30 min"
assert len(memoria.buscar(max_porcion=0.50)) == 4, "4 recetas de $0.55 o menos por porción"
excl = memoria.buscar(cocina="Ecuatoriana", excluir=["Locro de papa"])
assert len(excl) == 3 and all(r.nombre != "Locro de papa" for r in excl), "excluir quita la receta"
baratas = memoria.buscar()
assert [n.costo_porcion(r) for r in baratas] == sorted(n.costo_porcion(r) for r in baratas), "orden por precio"

# --- muestra_diaria: misma selección todo el día, misma lista de platos otro día ---
a1 = memoria.muestra_diaria("2026-11-05", 4, cocina="Ecuatoriana")
a2 = memoria.muestra_diaria("2026-11-05", 4, cocina="Ecuatoriana")
b = memoria.muestra_diaria("2026-11-06", 4, cocina="Ecuatoriana")
assert [r.nombre for r in a1] == [r.nombre for r in a2], "mismo día, mismo orden"
assert len(a1) == 4, "pide 4, da 4"
assert {r.nombre for r in a1} == {r.nombre for r in b}, "otro día, mismos platos disponibles (son 4 en total)"
assert all(r.cocina == "Ecuatoriana" for r in a1), "la muestra respeta la cocina"

# --- aprender: guarda recetas nuevas sin repetir (en un archivo temporal) ---
with tempfile.TemporaryDirectory() as tmp:
    memoria.ARCHIVO_NUEVAS = os.path.join(tmp, "nuevas.json")
    memoria._cache.clear()
    r, cat = TODAS[0]
    nueva = r.model_copy(deep=True)
    nueva.nombre = "Plato aprendido de prueba"
    memoria.aprender([nueva], "Entradas")
    memoria.aprender([nueva], "Entradas")          # dos veces: no duplica
    assert any(x.nombre == "Plato aprendido de prueba" for x, _ in memoria.todas()), "aprende la receta nueva"
    assert len(memoria.todas()) == 11, "sin duplicados al aprender dos veces la misma"
    memoria.aprender([])                           # lista vacía: no hace nada
    assert len(memoria.todas()) == 11
memoria._cache.clear()

print("TODAS LAS PRUEBAS DE MEMORIA OK")
