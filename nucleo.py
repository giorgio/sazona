"""Lógica de sazona. (sin interfaz): recetas, costos, menú de la semana y sobrantes.

La IA propone recetas con sus ingredientes y el precio estimado de cada
presentación; la app calcula el costo de cada receta y por porción, arma la
lista de compras en paquetes enteros y detecta lo que sobra.
"""

from __future__ import annotations

import json
import re
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
    alergenos: list[str] = Field(default_factory=list, description=(
        "Alérgenos comunes que contiene la receta, solo de esta lista: Gluten, Lácteos, Huevo, Maní, "
        "Frutos secos, Soya, Pescado, Mariscos, Ajonjolí. Lista vacía si no tiene ninguno."))


ECONOMICA = 1.00   # USD por porción: desde aquí abajo la receta se marca como "Económica"


def es_economica(por_porcion: float) -> bool:
    return por_porcion <= ECONOMICA


CATEGORIAS = ["Plato fuerte", "Sopas", "Ensaladas", "Desayunos", "Entradas", "Postres"]
DESCRIPCION_CATEGORIA = {
    "Plato fuerte": "plato principal de almuerzo o merienda, con proteína y acompañante",
    "Sopas": "sopas, caldos, cremas o locros",
    "Ensaladas": "ensaladas completas o de acompañante, frescas",
    "Desayunos": "desayunos o meriendas ligeras",
    "Entradas": "entradas, piqueos o bocaditos para compartir",
    "Postres": "postres sanos, con fruta y poco azúcar",
}


DIETAS = {
    "Todas": "",
    "Vegana": "VEGANA: nada de origen animal (sin carne, pescado, mariscos, huevo, lácteos ni miel)",
    "Vegetariana": "VEGETARIANA: sin carne, pollo, pescado ni mariscos; puede llevar lácteos, sin huevo",
    "Ovolactovegetariana": "OVOLACTOVEGETARIANA: sin carne, pollo, pescado ni mariscos; sí huevo y lácteos",
    "Pescetariana": "PESCETARIANA: sin carne roja ni pollo; sí pescado, mariscos, huevo y lácteos",
}


class Catalogo(BaseModel):
    recetas: list[Receta]


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SISTEMA = (
    "Eres el cocinero de sazona., una app de recetas sanas y baratas para hogares de Ecuador. "
    "Conoces cocinas de todo el mundo y las adaptas con ingredientes que se consiguen en mercados y "
    "supermercados ecuatorianos (Tía, Mi Comisariato, Supermaxi, Akí, TuTi, mercados municipales). "
    "Trabajas en USD y tus precios son ESTIMACIONES realistas, nunca exactas. No das dietas médicas "
    "ni diagnósticos. Escribes en ESPAÑOL DE ECUADOR, claro y apetitoso: usa los nombres que se usan aquí "
    "(arroz blanco, refrito, fréjol, choclo, verde, maduro, guineo, tomate riñón, cebolla paiteña o colorada, "
    "culantro, aguacate, zapallo, vainitas, arveja, maní, mote, queso fresco, ají) y nunca los de otros países "
    "(arroz patrio, hogao, frijol, palta, elote, ejote, chícharo, jitomate, cacahuate, betabel). Las cosas que se "
    "cuentan por unidad (huevos, papas, tomates, panes, salchichas…) van siempre en NÚMEROS ENTEROS."
)

PROMPT_RECETAS = """Propón {n} recetas distintas.

PEDIDO
- Cocinas: {cocinas}
- Personas (porciones): {personas}
- Costo máximo por porción: {max_porcion:.2f} USD
- Tiempo máximo: {tiempo} minutos
- Tipo: {tipos}
{categoria}{dieta}- Ciudad: {ciudad}
- No repitas estas recetas: {excluir}
{extra}
REGLAS
1. Recetas reales de esas cocinas, ADAPTADAS con ingredientes que se consiguen en Ecuador.
   Si un ingrediente es difícil de conseguir, cámbialo por uno local y menciónalo en un paso.
2. Saludables: con verduras o legumbres, sin frituras profundas, poco azúcar y porciones razonables.
3. Para cada ingrediente: la presentación en que se vende en Ecuador, su precio estimado completo y
   'fraccion_usada' = qué parte de esa presentación usa la receta (0.5 = la mitad).
   SOLO PRESENTACIONES QUE EXISTEN en tiendas ecuatorianas, con su tamaño en g, kg, ml, litro, libra o
   unidades: p. ej. arroz por libra o funda de 1 kg / 2 kg; fideo funda de 400 g o 500 g; lenteja o fréjol
   por libra o funda de 500 g; leche en funda o cartón de 1 litro; aceite de 1 litro; atún en lata de 170 g;
   huevos por unidad; verduras por unidad o por libra. NUNCA inventes tamaños ('funda de 75 g de arroz')
   ni medias presentaciones ('media caja'): la presentación es lo que se compra entero; lo que no se usa,
   sobra. 'cantidad' es lo que usa la receta en g, ml o unidades.
4. PRECIOS HONESTOS: precio_presentacion_usd es lo que cuesta HOY el paquete completo en un supermercado
   ecuatoriano (2026). NUNCA bajes un precio para que la receta entre en el presupuesto: si no alcanza,
   elige otra receta u otro ingrediente más barato. Referencias reales de 2026 (mercados): libra de pollo
   ~1.40; cubeta de 30 huevos ~4.10; libra de queso de mesa 3.00-4.00; choclo 0.40-0.60 c/u;
   libra de arveja o habas tiernas 1.00-1.50. Los granos secos y legumbres en funda de supermercado
   (fréjol, lenteja, garbanzo) casi siempre cuestan más de 1 USD la funda.
5. Con esos precios reales, el costo por porción debería quedar en {max_porcion:.2f} USD o menos.
   PRIORIZA INGREDIENTES BARATOS de mercado ecuatoriano: arroz, papa, yuca, verde, maduro, choclo, fréjol,
   lenteja, arveja, huevo, pollo, atún, avena, zanahoria, col, tomate y frutas de temporada. Al menos la
   mitad de las recetas debe costar menos de {economica:.2f} USD por porción.
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

# Alérgenos: lo que dice la IA + revisión por palabras en los ingredientes (por si la IA se olvida)
ALERGENOS = {
    "Gluten": r"\b(trigo|harina(?! de (maiz|arroz|yuca|platano|coco|almendra|garbanzo))|pan|panes|fideos?|"
              r"spaghetti|espagueti|tallarin(es)?|macarron(es)?|lasana|pasta(?! de (tomate|aji|mani))|"
              r"cebada|centeno|cuscus|galletas?|seitan|apanado|empanizado|pan rallado)\b",
    "Lácteos": r"\b(leche(?! de (coco|almendras?|soya|soja|avena|arroz))|quesos?|quesillo|yogur|yogurt|"
               r"crema de leche|nata|mantequilla(?! de mani)|requeson|suero de leche)\b",
    "Huevo": r"\b(huevos?|claras?|yemas?|mayonesa)\b",
    "Maní": r"\b(mani|cacahuates?|mantequilla de mani)\b",
    "Frutos secos": r"\b(nuez|nueces|almendras?|avellanas?|pistachos?|anacardos?|maranon|castanas?)\b",
    "Soya": r"\b(soya|soja|tofu|edamame|tempeh)\b",
    "Pescado": r"\b(pescado|atun|sardinas?|tilapia|corvina|salmon|bacalao|albacora|picudo|dorado|merluza|"
               r"trucha|anchoas?)\b",
    "Mariscos": r"\b(camaron(es)?|langostinos?|conchas?|mejillon(es)?|calamar(es)?|pulpo|cangrejos?|almejas?|"
                r"mariscos?|jaiba)\b",
    "Ajonjolí": r"\b(ajonjoli|sesamo|tahini|tahin)\b",
}


def detectar_alergenos(r: Receta) -> list[str]:
    texto = " ".join(_clave(i.nombre) for i in r.ingredientes)
    encontrados = {a for a, patron in ALERGENOS.items() if re.search(patron, texto)}
    por_clave = {_clave(a): a for a in ALERGENOS}
    encontrados |= {por_clave[_clave(x)] for x in (r.alergenos or []) if _clave(x) in por_clave}
    return [a for a in ALERGENOS if a in encontrados]


NO_PERMITIDO = {"Vegana": {"Lácteos", "Huevo", "Pescado", "Mariscos"},
                "Vegetariana": {"Huevo", "Pescado", "Mariscos"},
                "Ovolactovegetariana": {"Pescado", "Mariscos"}}


def cumple_dieta(r: Receta, dieta: str) -> bool:
    """Segunda revisión: descarta recetas que la IA marcó de una dieta pero traen algo prohibido."""
    return not (NO_PERMITIDO.get(dieta, set()) & set(r.alergenos or []))


# Tamaños que de verdad se venden en Ecuador (en g o ml). Si la IA inventa otro, se usa el real más
# pequeño que alcance y el precio se recalcula con el MISMO precio por gramo que dio la IA.
LIBRA = 454
TAMANOS_REALES = [
    (r"\barroz\b", "g", [LIBRA, 1000, 2000, 5000], "funda"),
    (r"\b(fideos?|spaghetti|espagueti|tallarin(es)?|macarron(es)?|pasta corta|lasana)\b", "g", [200, 250, 400, 500, 1000], "funda"),
    (r"\b(lentejas?|frejol(es)?|frijol(es)?|garbanzos?|arveja seca|habas secas|chochos?)\b", "g", [LIBRA, 500, 1000], "funda"),
    (r"\b(azucar|harina|avena|maicena|quinua|morocho|canguil)\b", "g", [250, 400, LIBRA, 500, 1000, 2000], "funda"),
    (r"\b(leche(?! de coco)|yogur|yogurt)\b", "ml", [200, 500, 946, 1000, 2000], "envase"),
    (r"\baceite\b", "ml", [500, 900, 1000, 2000], "botella"),
    (r"\batun\b", "g", [140, 170, 354], "lata"),
    (r"\b(sardinas?)\b", "g", [155, 425], "lata"),
    (r"\b(queso|quesillo)\b", "g", [250, LIBRA, 500, 1000], "unidad"),
    (r"\b(mantequilla|margarina)\b", "g", [100, 250, 500], "barra"),
    (r"\b(pasta de tomate|salsa de tomate)\b", "g", [100, 200, 400], "envase"),
]


def _tamano(texto: str, unidad: str) -> float | None:
    """Lee el tamaño de una presentación ('funda de 500 g', '1 kg', 'libra', '1 litro') en g o ml."""
    t = _clave(texto).replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|kilo|g|gr|gramos|ml|cc|l|lt|litros?|lb|libras?)\b", t)
    if m:
        v, u = float(m.group(1)), m.group(2)
        if u in ("kg", "kilo"):
            v *= 1000
        elif u in ("l", "lt", "litro", "litros"):
            v *= 1000
        elif u in ("lb", "libra", "libras"):
            v *= LIBRA
        return v
    if re.search(r"\b(media libra)\b", t):
        return LIBRA / 2
    if re.search(r"\b(libra)\b", t):
        return LIBRA
    if re.search(r"\b(litro)\b", t):
        return 1000.0
    if re.search(r"\b(kilo)\b", t):
        return 1000.0
    return None


def _bonito(v: float, unidad: str) -> str:
    if unidad == "g":
        if abs(v - LIBRA) < 1:
            return "1 libra"
        return f"{v / 1000:g} kg" if v >= 1000 else f"{v:g} g"
    return f"{v / 1000:g} litro" + ("s" if v > 1000 else "") if v >= 1000 else f"{v:g} ml"


def presentacion_real(i: Ingrediente) -> Ingrediente:
    """Si la presentación no existe (p. ej. 'funda de 75 g de arroz'), la cambia por la real más pequeña
    que alcance, manteniendo el precio por gramo y la cantidad que usa la receta."""
    nombre = _clave(i.nombre)
    for patron, unidad, tamanos, envase in TAMANOS_REALES:
        if not re.search(patron, nombre):
            continue
        actual = _tamano(i.presentacion, unidad)
        if not actual or actual <= 0:
            return i
        texto_raro = re.search(r"\b(media|medio|mitad)\b|1/2", _clave(i.presentacion))
        if any(abs(actual - t) <= t * 0.06 for t in tamanos):
            if texto_raro:                              # 'media caja de 250 g' -> 'funda de 250 g'
                i.presentacion = f"{envase} de {_bonito(actual, unidad)}"
            return i                                    # ya es un tamaño real
        usado = actual * i.fraccion_usada
        real = next((t for t in tamanos if t >= usado), tamanos[-1])
        precio_por = i.precio_presentacion_usd / actual
        i.precio_presentacion_usd = round(precio_por * real, 2)
        i.fraccion_usada = round(usado / real, 3)
        i.presentacion = f"{envase} de {_bonito(real, unidad)}"
        return i
    return i


# Nombres de otros países -> como se dice en Ecuador (por si la IA se equivoca)
ECUADOR = [
    (r"\barroz patrio\b", "arroz blanco"), (r"\bhogao\b", "refrito"), (r"\bfrijol(es)?\b", r"fréjol\1"),
    (r"\bfríjol(es)?\b", r"fréjol\1"), (r"\bpaltas?\b", "aguacate"), (r"\belotes?\b", "choclo"),
    (r"\bejotes?\b", "vainitas"), (r"\bchícharos?\b", "arveja"), (r"\bjitomates?\b", "tomate riñón"),
    (r"\bcacahuates?\b", "maní"), (r"\bcacahuetes?\b", "maní"), (r"\bbetabel\b", "remolacha"),
    (r"\bplátano macho\b", "verde"), (r"\bcalabaza\b", "zapallo"), (r"\bpimentón rojo\b", "pimiento rojo"),
    (r"\bchile\b", "ají"), (r"\bfrutilla\b", "frutilla"), (r"\bpapa criolla\b", "papa chola"),
]


def a_ecuador(texto: str) -> str:
    if not texto:
        return texto
    for patron, cambio in ECUADOR:
        def rep(m, cambio=cambio):
            nuevo = m.expand(cambio) if "\\" in cambio else cambio
            return nuevo[:1].upper() + nuevo[1:] if m.group(0)[:1].isupper() else nuevo
        texto = re.sub(patron, rep, texto, flags=re.IGNORECASE)
    return texto


def unidades_paquete(presentacion: str) -> int | None:
    """Cuántas unidades trae una presentación que se cuenta ('cubeta de 30' -> 30, 'unidad' -> 1)."""
    t = _clave(presentacion or "")
    m = re.search(r"(\d+)\s*(unidades?|u\b)|(cubeta|docena|paquete|malla|atado|funda) de (\d+)\b(?!\s*(g|kg|ml|l|lb))", t)
    if m:
        return int(m.group(1) or m.group(4))
    if re.search(r"\bdocena\b", t):
        return 12
    if re.search(r"\b(unidad|c/u|cada uno)\b", t):
        return 1
    return None


def enteros(i: Ingrediente) -> Ingrediente:
    """Lo que se cuenta por unidad se usa entero: nada de 1.8 huevos."""
    total = unidades_paquete(i.presentacion)
    if total and not i.basico_de_despensa:
        usadas = max(1, round(total * i.fraccion_usada))
        i.fraccion_usada = round(usadas / total, 4)
    return i


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
    r.nombre, r.descripcion = a_ecuador(r.nombre), a_ecuador(r.descripcion)
    r.pasos = [a_ecuador(p) for p in r.pasos]
    for i in r.ingredientes:
        i.nombre, i.cantidad = a_ecuador(i.nombre), a_ecuador(i.cantidad)
    r.ingredientes = [enteros(presentacion_real(i)) for i in r.ingredientes]
    r.alergenos = detectar_alergenos(r)
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
        enteros(i)
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
                   excluir=(), sobrantes=(), cantidad=RECETAS_POR_BUSQUEDA, categoria="", dieta="Todas"):
    """Devuelve (recetas dentro del presupuesto ordenadas por precio, cuántas se descartaron)."""
    prompt = PROMPT_RECETAS.format(
        n=cantidad, economica=ECONOMICA, cocinas=", ".join(cocinas), personas=personas, max_porcion=max_porcion,
        tiempo=tiempo, tipos=", ".join(tipos) or "cualquiera", ciudad=ciudad or "Guayaquil",
        excluir=", ".join(excluir) or "ninguna",
        categoria=(f"- Categoría: {categoria}. TODAS las recetas deben ser de esta categoría "
                   f"({DESCRIPCION_CATEGORIA.get(categoria, categoria)}).\n") if categoria else "",
        dieta=(f"- Dieta OBLIGATORIA, revisa cada ingrediente: {DIETAS[dieta]}.\n") if DIETAS.get(dieta) else "",
        extra=EXTRA_SOBRANTES.format(sobrantes=", ".join(sobrantes)) if sobrantes else "",
    )
    cat, _ = llamar_gemini(cliente, prompt, Catalogo, razonamiento="minimal")
    validas, descartadas = [], 0
    for r in cat.recetas:
        r = ajustar_porciones(limpiar_receta(r), personas)
        if not r.ingredientes or not r.pasos:
            descartadas += 1
            continue
        if not cumple_dieta(r, dieta):
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


def lo_que_usas(i: Ingrediente) -> str:
    """Cantidad que usa la receta, calculada del paquete (sigue bien al cambiar de personas)."""
    for unidad in ("g", "ml"):
        t = _tamano(i.presentacion, unidad)
        if t:
            usado = t * i.fraccion_usada
            if unidad == "g" and re.search(r"\b(ml|cc|litros?|lt)\b", _clave(i.presentacion)):
                unidad = "ml"
            return f"{usado:,.0f} {unidad}" if usado >= 10 else f"{usado:.1f} {unidad}"
    m = re.search(r"(\d+)\s*(unidades?|u\b)|(cubeta|docena|paquete|malla|atado) de (\d+)", _clave(i.presentacion))
    if m:
        total = int(m.group(1) or m.group(4))
        usado = total * i.fraccion_usada
        return f"{usado:g} unidad" if abs(usado - 1) < 1e-9 else f"{round(usado, 1):g} unidades"
    if re.search(r"\b(unidad|c/u)\b", _clave(i.presentacion)):
        usado = i.fraccion_usada
        return f"{round(usado, 1):g} unidad" + ("es" if round(usado, 1) != 1 else "")
    return i.cantidad


def desglose_receta(r: Receta) -> list[dict]:
    """Cada ingrediente con lo que usas, lo que compras (paquetes enteros reales) y cuánto sobra."""
    filas = []
    for i in r.ingredientes:
        paquetes = max(1, math.ceil(round(i.fraccion_usada, 3) - 1e-9))
        sobra = max(0.0, paquetes - i.fraccion_usada)
        filas.append({
            "Ingrediente": i.nombre,
            "Usas": lo_que_usas(i),
            "Compras": f"{paquetes} × {i.presentacion}",
            "Precio del paquete": round(i.precio_presentacion_usd, 2),
            "Total pagado": round(paquetes * i.precio_presentacion_usd, 2),
            "Vale lo que usas": costo_ingrediente(i),
            "Te sobra": "nada" if sobra < 0.05 else f"{round(sobra * 100):.0f} % del paquete",
            "Despensa": "Sí" if i.basico_de_despensa else "",
        })
    return filas


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
