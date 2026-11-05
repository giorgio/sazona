"""Pruebas de sazón. sin internet ni cuota (se simula a Gemini). Ejecutar: python tests/test_nucleo.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import nucleo as n


class Resp:
    def __init__(s, obj): s.parsed, s.text = obj, None


class Err(Exception):
    def __init__(s, code): s.code = code


class Fake:
    def __init__(s, seq):
        s.models = s
        s.seq = list(seq)

    def generate_content(s, model, contents, config):
        s.ultimo_prompt = contents
        x = s.seq.pop(0)
        if isinstance(x, Exception):
            raise x
        return Resp(x)


def ing(nombre, pres, precio, frac, despensa=False):
    return n.Ingrediente(nombre=nombre, cantidad="x", presentacion=pres, precio_presentacion_usd=precio,
                         fraccion_usada=frac, basico_de_despensa=despensa)


def receta(nombre, ings, porciones=2, icono="pasta"):
    return n.Receta(nombre=nombre, cocina="Italiana", descripcion="d", porciones=porciones, tiempo_minutos=30,
                    dificultad="Fácil", etiquetas=[], ingredientes=ings, pasos=["a"], calorias_por_porcion=400,
                    proteina_g_por_porcion=20, por_que_es_saludable="x", busqueda_foto="pasta", icono=icono)


# validaciones
assert not n.validar_busqueda([], 2, 1.5, 30).ok
assert not n.validar_busqueda(["China"], 2, 0.1, 30).ok
assert n.validar_busqueda(["China"], 2, 1.5, 30).ok

# costos: la app suma, no la IA
pasta = receta("Pasta pomodoro", [ing("Fideo spaghetti", "funda 500 g", 1.20, 0.5), ing("Tomate", "libra", 0.80, 1.0),
                                   ing("Aceite", "botella 1 l", 3.0, 0.02, True)])
assert n.costo_receta(pasta) == 1.46 and n.costo_porcion(pasta) == 0.73

# limpieza de datos imposibles
mala = receta("Rara", [ing("A", "u", -1, 0.5), ing("B", "u", 2, 1.7)], porciones=0, icono="nave")
mala = n.limpiar_receta(mala)
assert len(mala.ingredientes) == 1 and mala.ingredientes[0].fraccion_usada == 1.0 and mala.porciones == 1
assert mala.icono == "otro"

# escalar porciones
x4 = n.ajustar_porciones(pasta, 4)
assert x4.porciones == 4 and x4.ingredientes[0].fraccion_usada == 1.0 and pasta.porciones == 2
assert n.costo_porcion(x4) == n.costo_porcion(pasta) or abs(n.costo_porcion(x4) - n.costo_porcion(pasta)) < 0.02

# búsqueda: filtra las que se pasan del precio y ordena de la más barata a la más cara
cara = receta("Lomo", [ing("Lomo", "kg", 12, 1.0)])
barata = receta("Lentejas", [ing("Lenteja", "funda 500 g", 1.0, 0.5)])
cat = n.Catalogo(recetas=[pasta, cara, barata])
recs, descartadas = n.buscar_recetas(Fake([cat]), ["Italiana"], 2, 1.0, 30)
assert [r.nombre for r in recs] == ["Lentejas", "Pasta pomodoro"] and descartadas == 1

# sin recetas válidas -> error claro
try:
    n.buscar_recetas(Fake([n.Catalogo(recetas=[cara])]), ["Italiana"], 2, 1.0, 30)
    raise SystemExit("debió fallar")
except n.ErrorIA as e:
    assert "precio" in str(e)

# sobrantes pasan al prompt
f = Fake([n.Catalogo(recetas=[barata])])
n.buscar_recetas(f, ["China"], 2, 1.5, 30, sobrantes=["Fideo spaghetti"])
assert "Fideo spaghetti" in f.ultimo_prompt and "PRIORIDAD" in f.ultimo_prompt

# 429 en ambos modelos
try:
    n.buscar_recetas(Fake([Err(429), Err(429)]), ["China"], 2, 1.5, 30)
    raise SystemExit("debió fallar")
except n.ErrorIA as e:
    assert "límite" in str(e)

# menú de la semana: paquetes enteros y sobrantes
otra_pasta = receta("Lo mein", [ing("fideo spaghetti", "Funda 500 g", 1.20, 0.25), ing("Zanahoria", "libra", 0.5, 0.5)])
lista = n.lista_de_compras([pasta, otra_pasta])
fideo = [f for f in lista["comprar"] if f["Ingrediente"].lower().startswith("fideo")]
assert len(fideo) == 1 and fideo[0]["Comprar"].startswith("1 ×") and fideo[0]["Precio"] == 1.2
assert [s["nombre"] for s in lista["sobrantes"]] == ["Zanahoria", "Fideo spaghetti"], lista["sobrantes"]
assert lista["despensa"][0]["Ingrediente"] == "Aceite"
assert lista["total"] == round(1.2 + 0.8 + 0.5, 2)
assert n.costo_menu([pasta, otra_pasta]) == round(1.46 + 0.3 + 0.25, 2)
assert "productos=" in n.enlace_canastas(lista) and "Tomate" in n.enlace_canastas(lista)
assert "Total estimado" in n.texto_lista([pasta], n.lista_de_compras([pasta]))
print("TODAS LAS PRUEBAS DE SAZÓN OK")
