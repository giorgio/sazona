"""Lógica de sazón. (sin interfaz): recetas, costos, menú de la semana y sobrantes.

La IA propone recetas con sus ingredientes y el precio estimado de cada
presentación; la app calcula el costo de cada receta y por porción, arma la
lista de compras en paquetes enteros y detecta lo que sobra.
"""

from __future__ import annotations

import json
import math
import time
import unicodedata
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

MODELO_PRINCIPAL = "gemini-3.8-flash"
MODELO_RESPALDO = "gemini-3.5-flash-lite"

COCINAS = ["Ecuatoriana", "Italiana", "China", "Mexicana", "Peruana", "Mediterránea",
           "India", "Japonesa", "Tailandesa", "Árabe", "Colombiana", "Española"]
# Botones del inicio: lo que ve la persona -> la cocina que se pide a la IA
PAISES = {"Ecuador": "Ecuatoriana", "Italia": "Italiana", "China": "China", "México": "Mexicana",
          "Perú": "Peruana", "Colombia": "Colombiana", "España": "Española", "Mediterráneo": "Mediterránea",
          "India": "India", "Japón": "Japonesa", "Tailandia": "Tailandesa", "Medio Oriente": "Árabe"}
TIPOS = ["Alta en proteína", "Vegetariana", "Vegana", "Para niños", "Baja en grasa", "Sin gluten"]
ICONOS = ["pasta", "arroz", "sopa", "ensalada", "pollo", "carne", "pescado", "huevo", "menestra", "otro"]
RECETAS_POR_BUSQUEDA = 6
SOBRANTE_MINIMO = 0.25  # desde un cuarto de paquete vale la pena aprovecharlo


# ---------------------------------------------------------------------------
# Esquemas (Gemini responde JSON con esta forma)
# ---------------------------------------------------------------------------

class Ingrediente(BaseModel):
    nombre: str = Field(description="Ingrediente genérico, p. ej. 'Fideo spaghetti', 'Pechuga de pollo'")
    cantidad: str = Field(description="Lo que usa la receta, p. ej. '250 g', '2 unidades'")
    presentacion: str = Field(description="Cómo se compra en Ecuador, p. ej. 'funda de 500 g', 'cubeta de 30'")
    precio_presentacion_usd: float = Field(description="Precio estimado en USD de esa presentación completa")
    fraccion_usada: float = Field(description="Parte de la presentación que usa la receta, de 0 a 1")
    basico_de_despensa: bool = Field(description="True para sal, pimienta, aceite, ajo en polvo y similares")


class Receta(BaseModel):
    nombre: str
    cocina: str = Field(description="Una de las cocinas pedidas")
    descripcion: str = Field(description="Una frase apetitosa de máximo 15 palabras")
    porciones: int
    tiempo_minutos: int
    dificultad: str = Field(description="Fácil o Media")
    etiquetas: list[str] = Field(description="De los tipos pedidos u otros cortos: 'Alta en proteína', 'Rápida'...")
    ingredientes: list[Ingrediente]
    pasos: list[str]
    calorias_por_porcion: int
    proteina_g_por_porcion: int
    por_que_es_saludable: str
    busqueda_foto: str = Field(description="Búsqueda en INGLÉS para encontrar una foto del plato, 3 a 6 palabras")
    icono: str = Field(description="Uno de: " + ", ".join(ICONOS))


class Catalogo(BaseModel):
    recetas: list[Receta]


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SISTEMA = (
    "Eres el cocinero de sazón., una app de recetas sanas y baratas para hogares de Ecuador. "
    "Conoces cocinas de todo el mundo y las adaptas con ingredientes que se consiguen en mercados y "
    "supermercados ecuatorianos (Tía, Mi Comisariato, Supermaxi, Akí, TuTi, mercados municipales). "
    "Trabajas en USD y tus precios son ESTIMACIONES realistas, nunca exactas. No das dietas médicas "
    "ni diagnósticos. Escribes en español neutro, claro y apetitoso."
)

PROMPT_RECETAS = """Propón {n} recetas distintas.

PEDIDO
- Cocinas: {cocinas}
- Personas (porciones): {personas}
- Costo máximo por porción: {max_porcion:.2f} USD
- Tiempo máximo: {tiempo} minutos
- Tipo: {tipos}
- Ciudad: {ciudad}
- No repitas estas recetas: {excluir}
{extra}
REGLAS
1. Recetas reales de esas cocinas, ADAPTADAS con ingredientes que se consiguen en Ecuador.
   Si un ingrediente es difícil de conseguir, cámbialo por uno local y menciónalo en un paso.
2. Saludables: con verduras o legumbres, sin frituras profundas, poco azúcar y porciones razonables.
3. Para cada ingrediente: la presentación en que se vende en Ecuador, su precio estimado completo y
   'fraccion_usada' = qué parte de esa presentación usa la receta (0.5 = la mitad).
4. PRECIOS HONESTOS: precio_presentacion_usd es lo que cuesta HOY el paquete completo en un supermercado
   ecuatoriano (2026). NUNCA bajes un precio para que la receta entre en el presupuesto: si no alcanza,
   elige otra receta u otro ingrediente más barato. Referencias reales de 2026 (mercados): libra de pollo
   ~1.40; cubeta de 30 huevos ~4.10; libra de queso de mesa 3.00-4.00; choclo 0.40-0.60 c/u;
   libra de arveja o habas tiernas 1.00-1.50. Los granos secos y legumbres en funda de supermercado
   (fréjol, lenteja, garbanzo) casi siempre cuestan más de 1 USD la funda.
5. Con esos precios reales, el costo por porción debería quedar en {max_porcion:.2f} USD o menos.
6. Marca sal, pimienta, aceite y condimentos secos como basico_de_despensa.
7. Pasos cortos (máximo 8), pensados para alguien que cocina poco.
8. Calorías y proteína son aproximadas por porción."""

EXTRA_SOBRANTES = """- PRIORIDAD: usa estos ingredientes que le sobraron al usuario esta semana: {sobrantes}.
  Cada receta debe usar al menos uno de ellos."""


# ---------------------------------------------------------------------------
# Validaciones
# ---------------------------------------------------------------------------

@dataclass
class Validacion:
    errores: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errores


def validar_busqueda(cocinas: list[str], personas: int, max_porcion: float, tiempo: int) -> Validacion:
    v = Validacion()
    if not cocinas:
        v.errores.append("Elige al menos un tipo de cocina.")
    if not personas or personas < 1:
        v.errores.append("Indica al menos 1 persona.")
    if max_porcion is None or max_porcion < 0.3:
        v.errores.append("Con menos de 0,30 USD por porción no se puede armar una receta completa.")
    if not tiempo or tiempo < 10:
        v.errores.append("Elige al menos 10 minutos de cocina.")
    return v


# ---------------------------------------------------------------------------
# Costos (los calcula la app, no la IA)
# ---------------------------------------------------------------------------

def limpiar_receta(r: Receta) -> Receta:
    """Corrige datos imposibles que a veces devuelve la IA."""
    r.porciones = max(1, int(r.porciones or 1))
    r.tiempo_minutos = max(1, int(r.tiempo_minutos or 1))
    buenos = []
    for i in r.ingredientes:
        if i.precio_presentacion_usd is None or i.precio_presentacion_usd < 0:
            continue
        i.fraccion_usada = min(1.0, max(0.0, float(i.fraccion_usada or 0)))
        buenos.append(i)
    r.ingredientes = buenos
    if r.icono not in ICONOS:
        r.icono = "otro"
    return r


def costo_ingrediente(i: Ingrediente) -> float:
    return round(i.precio_presentacion_usd * i.fraccion_usada, 2)


def costo_receta(r: Receta) -> float:
    return round(sum(costo_ingrediente(i) for i in r.ingredientes), 2)


def costo_porcion(r: Receta) -> float:
    return round(costo_receta(r) / max(r.porciones, 1), 2)


def ajustar_porciones(r: Receta, personas: int) -> Receta:
    """Escala la receta a otro número de personas (la fracción usada crece o baja)."""
    if personas == r.porciones or personas < 1:
        return r
    f = personas / r.porciones
    nueva = r.model_copy(deep=True)
    for i in nueva.ingredientes:
        i.fraccion_usada = round(i.fraccion_usada * f, 3)
    nueva.porciones = personas
    return nueva


def tabla_ingredientes(r: Receta) -> list[dict]:
    return [{
        "Ingrediente": i.nombre,
        "Cantidad": i.cantidad,
        "Se compra": i.presentacion,
        "Precio del paquete": round(i.precio_presentacion_usd, 2),
        "Usas": f"{min(i.fraccion_usada, 1):.0%}" if i.fraccion_usada < 1 else "todo",
        "Costo en la receta": costo_ingrediente(i),
        "Despensa": "Sí" if i.basico_de_despensa else "",
    } for i in r.ingredientes]


# ---------------------------------------------------------------------------
# Llamada a Gemini (igual que en canastas.)
# ---------------------------------------------------------------------------

class ErrorIA(Exception):
    """Error con un mensaje ya listo para mostrar al usuario."""


def _codigo(e: Exception) -> int | None:
    return getattr(e, "code", None) or getattr(e, "status_code", None)


def llamar_gemini(cliente, prompt: str, esquema, modelos=(MODELO_PRINCIPAL, MODELO_RESPALDO), reintentos: int = 1,
                  razonamiento: str = "low"):
    from google.genai import types

    ultimo_error: Exception | None = None
    usar_nivel = True
    for modelo in modelos:
        for intento in range(reintentos + 1):
            try:
                resp = cliente.models.generate_content(
                    model=modelo,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SISTEMA,
                        response_mime_type="application/json",
                        response_schema=esquema,
                        temperature=0.7,
                        max_output_tokens=12000,
                        thinking_config=types.ThinkingConfig(thinking_level=razonamiento) if usar_nivel else None,
                    ),
                )
                obj = resp.parsed
                if obj is None and getattr(resp, "text", None):
                    obj = esquema.model_validate(json.loads(resp.text))
                if obj is None:
                    raise ValueError("respuesta vacía")
                return obj, modelo
            except Exception as e:  # noqa: BLE001
                ultimo_error = e
                codigo = _codigo(e)
                if codigo in (401, 403):
                    raise ErrorIA("La clave de la IA no es válida. Revisa el secreto GEMINI_API_KEY.") from e
                if codigo == 400 and usar_nivel and "think" in str(e).lower():
                    usar_nivel = False
                    continue
                if codigo in (404, 429):
                    break
                if intento < reintentos:
                    time.sleep(2)
                    continue
                break
    codigo = _codigo(ultimo_error) if ultimo_error else None
    if codigo == 429:
        raise ErrorIA("Se alcanzó el límite gratuito de consultas a la IA. Espera un minuto y vuelve a intentar.")
    if codigo and codigo >= 500:
        raise ErrorIA("El servicio de IA está saturado. Intenta de nuevo en unos minutos.")
    raise ErrorIA("La IA no devolvió recetas válidas. Intenta de nuevo.")


def buscar_recetas(cliente, cocinas, personas, max_porcion, tiempo, tipos=(), ciudad="Guayaquil",
                   excluir=(), sobrantes=(), cantidad=RECETAS_POR_BUSQUEDA):
    """Devuelve (recetas dentro del presupuesto ordenadas por precio, cuántas se descartaron)."""
    prompt = PROMPT_RECETAS.format(
        n=cantidad, cocinas=", ".join(cocinas), personas=personas, max_porcion=max_porcion,
        tiempo=tiempo, tipos=", ".join(tipos) or "cualquiera", ciudad=ciudad or "Guayaquil",
        excluir=", ".join(excluir) or "ninguna",
        extra=EXTRA_SOBRANTES.format(sobrantes=", ".join(sobrantes)) if sobrantes else "",
    )
    cat, _ = llamar_gemini(cliente, prompt, Catalogo, razonamiento="minimal")
    validas, descartadas = [], 0
    for r in cat.recetas:
        r = ajustar_porciones(limpiar_receta(r), personas)
        if not r.ingredientes or not r.pasos:
            descartadas += 1
            continue
        if costo_porcion(r) > max_porcion * 1.1:  # 10 % de tolerancia por redondeo
            descartadas += 1
            continue
        validas.append(r)
    if not validas:
        raise ErrorIA("No encontré recetas dentro de ese precio. Sube un poco el precio máximo o cambia de cocina.")
    return sorted(validas, key=costo_porcion), descartadas


# ---------------------------------------------------------------------------
# Menú de la semana: lista de compras en paquetes enteros y sobrantes
# ---------------------------------------------------------------------------

def _clave(texto: str) -> str:
    t = unicodedata.normalize("NFD", texto.lower().strip())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def lista_de_compras(recetas: list[Receta]) -> dict:
    """Junta los ingredientes de varias recetas. Se compran paquetes enteros."""
    grupos: dict[tuple, dict] = {}
    for r in recetas:
        for i in r.ingredientes:
            k = (_clave(i.nombre), _clave(i.presentacion))
            g = grupos.setdefault(k, {"nombre": i.nombre, "presentacion": i.presentacion,
                                      "precio": i.precio_presentacion_usd, "uso": 0.0,
                                      "despensa": i.basico_de_despensa, "recetas": []})
            g["uso"] += i.fraccion_usada
            g["precio"] = max(g["precio"], i.precio_presentacion_usd)
            if r.nombre not in g["recetas"]:
                g["recetas"].append(r.nombre)
    comprar, despensa, sobrantes = [], [], []
    for g in grupos.values():
        paquetes = max(1, math.ceil(round(g["uso"], 3) - 1e-9))
        sobra = round(paquetes - g["uso"], 2)
        fila = {"Ingrediente": g["nombre"], "Comprar": f"{paquetes} × {g['presentacion']}",
                "Precio": round(paquetes * g["precio"], 2), "Para": ", ".join(g["recetas"]),
                "Sobra": f"{sobra:.0%} de un paquete" if sobra >= 0.05 else ""}
        (despensa if g["despensa"] else comprar).append(fila)
        if not g["despensa"] and sobra >= SOBRANTE_MINIMO:
            sobrantes.append({"nombre": g["nombre"], "presentacion": g["presentacion"], "sobra": sobra})
    comprar.sort(key=lambda f: f["Ingrediente"])
    return {
        "comprar": comprar,
        "despensa": despensa,
        "sobrantes": sorted(sobrantes, key=lambda s: -s["sobra"]),
        "total": round(sum(f["Precio"] for f in comprar), 2),
        "despensa_total": round(sum(f["Precio"] for f in despensa), 2),
    }


def compras_receta(r: Receta) -> dict:
    """Lo que hay que comprar para una receta: cada producto en paquetes enteros, con su precio."""
    comprar, despensa = [], []
    for i in r.ingredientes:
        paquetes = max(1, math.ceil(round(i.fraccion_usada, 3) - 1e-9))
        fila = {"Producto": i.nombre, "Para la receta": i.cantidad,
                "Compras": f"{paquetes} × {i.presentacion}",
                "Precio": round(paquetes * i.precio_presentacion_usd, 2)}
        (despensa if i.basico_de_despensa else comprar).append(fila)
    return {"comprar": comprar, "despensa": despensa,
            "total": round(sum(f["Precio"] for f in comprar), 2)}


def costo_menu(recetas: list[Receta]) -> float:
    """Lo que de verdad se gasta en la semana (solo lo usado, no paquetes enteros)."""
    return round(sum(costo_receta(r) for r in recetas), 2)


def texto_lista(recetas: list[Receta], lista: dict) -> str:
    lineas = ["SAZÓN. - Lista de compras de la semana", "Precios estimados: confírmalos en la tienda.", "",
              "Recetas: " + ", ".join(r.nombre for r in recetas), ""]
    lineas += [f"[ ] {f['Comprar']} de {f['Ingrediente']}  ~{f['Precio']:.2f} USD" for f in lista["comprar"]]
    lineas += ["", f"Total estimado: {lista['total']:.2f} USD"]
    if lista["despensa"]:
        lineas += ["", "Revisa si tienes en casa: " + ", ".join(f["Ingrediente"] for f in lista["despensa"])]
    return "\n".join(lineas)


def enlace_canastas(lista: dict, base: str = "https://canastas.streamlit.app") -> str:
    """Abre canastas. con estos productos ya cargados para comparar tiendas."""
    from urllib.parse import quote

    productos = [f["Ingrediente"] for f in lista["comprar"]][:15]
    return f"{base}/?productos=" + quote("|".join(productos))
