"""sazón.: recetas sanas y baratas de todo el mundo, con su precio por porción.

Hermana de canastas. Páginas:
  - Inicio: la receta sugerida del día (con foto) y un botón por país.
  - País: las recetas de esa cocina, de 3 en 3 con "Mostrar más".
  - Receta: eliges para cuántas personas y la app calcula el costo por porción y el total.
  - Mi semana: las recetas elegidas, una sola lista de compras en paquetes enteros,
    ideas para lo que sobra y enlace a canastas. para comparar tiendas.

Ejecutar en local:  streamlit run app.py
Claves en .streamlit/secrets.toml o en los Secrets de Streamlit Cloud: GEMINI_API_KEY y PEXELS_API_KEY.
"""

import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

import diseno as d
import fotos
import nucleo as n

ICONO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icono.png")
st.set_page_config(page_title="sazón.", page_icon=ICONO if os.path.exists(ICONO) else "🍲", layout="wide")

ESPERA_ENTRE_CONSULTAS = 6
POR_PAGINA = 3            # recetas que se muestran de una vez
BASE_PERSONAS = 4         # la IA calcula para 4; la app escala a lo que elija la persona
MAX_PORCION = 2.5
TIEMPO_MAX = 60
INICIALES = {"pagina": "inicio", "pais": None, "extra": {}, "visibles": {}, "menu": [], "ideas_sobra": [],
             "personas": 2}
for _k, _v in INICIALES.items():
    st.session_state.setdefault(_k, _v)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def ir(pagina, pais=None):
    st.session_state["pagina"] = pagina
    if pais:
        st.session_state["pais"] = pais


def secreto(nombre):
    try:
        return st.secrets.get(nombre)
    except Exception:  # noqa: BLE001
        return None


def cliente_gemini():
    clave = secreto("GEMINI_API_KEY")
    if not clave:
        raise n.ErrorIA("Falta la clave de la IA (GEMINI_API_KEY) en los Secrets de la app.")
    from google import genai

    return genai.Client(api_key=clave)


def hoy() -> str:
    return datetime.now(ZoneInfo("America/Guayaquil")).date().isoformat()


def esperar_turno():
    falta = ESPERA_ENTRE_CONSULTAS - (time.time() - st.session_state.get("ultima_consulta", 0))
    if falta > 0:
        time.sleep(falta)
    st.session_state["ultima_consulta"] = time.time()


@st.cache_data(ttl=86400, show_spinner=False, max_entries=60)
def recetas_del_dia(cocina: str, dia: str):
    """Recetas de una cocina. Se guardan un día y se comparten entre visitantes (ahorra cuota)."""
    recetas, _ = n.buscar_recetas(cliente_gemini(), [cocina], BASE_PERSONAS, MAX_PORCION, TIEMPO_MAX,
                                  cantidad=POR_PAGINA)
    return recetas


def cocina_sugerida(dia: str) -> str:
    cocinas = list(n.PAISES.values())
    return cocinas[datetime.fromisoformat(dia).toordinal() % len(cocinas)]


@st.cache_data(ttl=7 * 86400, show_spinner=False)
def foto(consulta: str):
    return fotos.buscar_foto(consulta, secreto("PEXELS_API_KEY"))


def en_menu(r) -> bool:
    return any(m.nombre == r.nombre for m in st.session_state["menu"])


def alternar_menu(r):
    if en_menu(r):
        st.session_state["menu"] = [m for m in st.session_state["menu"] if m.nombre != r.nombre]
    else:
        st.session_state["menu"] = st.session_state["menu"] + [r]


def alto(filas):
    return 36 + 35 * max(len(filas), 1)


def mostrar_foto(r):
    f = foto(r.busqueda_foto)
    if f:
        st.image(f["url"], width="stretch")
        d.credito_foto(f)
    else:
        d.foto_vacia()


# ---------------------------------------------------------------------------
# Detalle de receta: personas -> costo por porción y total
# ---------------------------------------------------------------------------

@st.dialog("Receta", width="large")
def ver_receta(r):
    c1, c2 = st.columns([1, 1.2], gap="large")
    with c1:
        mostrar_foto(r)
    with c2:
        d.info_receta(r)
        personas = st.number_input("¿Para cuántas personas?", min_value=1, max_value=20,
                                   value=st.session_state["personas"], key=f"pers_{r.nombre}")
        st.session_state["personas"] = personas
        rp = n.ajustar_porciones(r, personas)
        d.costos(n.costo_porcion(rp), n.costo_receta(rp), personas)
        ya = en_menu(r)
        st.button("Quitar de mi semana" if ya else f"Agregar a mi semana (para {personas})",
                  icon=":material/remove:" if ya else ":material/add:", on_click=alternar_menu, args=(rp,),
                  type="secondary" if ya else "primary", width="stretch")
    st.subheader(f"Ingredientes para {personas}")
    filas = n.tabla_ingredientes(rp)
    st.dataframe(filas, hide_index=True, width="stretch", height=alto(filas),
                 column_config={"Costo en la receta": st.column_config.NumberColumn(format="$%.2f")})
    st.caption("“Costo en la receta” es solo la parte que usas del paquete. Precios estimados.")
    st.subheader("Preparación")
    for i, p in enumerate(r.pasos, 1):
        st.markdown(f"{i}. {p}")
    st.caption(f"Dificultad: {r.dificultad}")
    st.info("💚 " + r.por_que_es_saludable)


def tarjeta(r, clave: str):
    with st.container(border=True, key=f"rc_{clave}"):
        mostrar_foto(r)
        d.info_receta(r, n.costo_porcion(r))
        if st.button("Ver receta", key=f"ver_{clave}", icon=":material/menu_book:", type="primary", width="stretch"):
            ver_receta(r)
        with st.container(key=f"en_menu_{clave}" if en_menu(r) else f"fuera_{clave}"):
            st.button("En mi semana" if en_menu(r) else "A mi semana",
                      icon=":material/check:" if en_menu(r) else ":material/add:",
                      key=f"menu_{clave}", on_click=alternar_menu,
                      args=(n.ajustar_porciones(r, st.session_state["personas"]),), width="stretch")


def cuadricula(recetas, prefijo: str):
    for fila in range(0, len(recetas), 3):
        cols = st.columns(3, gap="medium")
        for j, r in enumerate(recetas[fila:fila + 3]):
            with cols[j]:
                tarjeta(r, f"{prefijo}_{fila + j}")


# ---------------------------------------------------------------------------
# Página: inicio (receta sugerida + países)
# ---------------------------------------------------------------------------

def pagina_inicio():
    d.titulo("Cocina rico, gasta poco", "¿Qué cocinamos hoy?",
             "Recetas de todo el mundo con ingredientes de aquí, cada una con su precio por porción.")
    hueco_sugerida = st.container()

    st.markdown('<p class="sz-seccion">Elige un país</p>', unsafe_allow_html=True)
    with st.container(key="paises"):
        paises = list(n.PAISES)
        for fila in range(0, len(paises), 4):
            cols = st.columns(4, gap="small")
            for j, pais in enumerate(paises[fila:fila + 4]):
                i = fila + j
                with cols[j].container(key=f"tono{i % len(d.TONOS)}_{i}"):
                    st.button(pais, key=f"pais_{pais}", width="stretch", on_click=ir, args=("pais", pais))

    with hueco_sugerida:
        dia = hoy()
        try:
            with st.spinner("Preparando la receta del día…"):
                r = recetas_del_dia(cocina_sugerida(dia), dia)[0]
        except n.ErrorIA as e:
            st.warning(f"No pudimos traer la receta del día. {e}")
            return
        with st.container(border=True, key="sugerida"):
            st.markdown('<p class="sz-ceja sz-ceja-terra">Receta sugerida de hoy</p>', unsafe_allow_html=True)
            c1, c2 = st.columns([1.1, 1], gap="large", vertical_alignment="center")
            with c1:
                mostrar_foto(r)
            with c2:
                d.info_receta(r, n.costo_porcion(r))
                if st.button("Ver receta", key="ver_sugerida", icon=":material/menu_book:", type="primary",
                             width="stretch"):
                    ver_receta(r)
        st.write("")


# ---------------------------------------------------------------------------
# Página: recetas de un país
# ---------------------------------------------------------------------------

def pagina_pais():
    s = st.session_state
    pais = s["pais"] or "Ecuador"
    cocina = n.PAISES[pais]
    st.button("Todos los países", icon=":material/arrow_back:", on_click=ir, args=("inicio",), key="volver")
    d.titulo(f"Cocina de {pais}" if pais not in ("Mediterráneo", "Medio Oriente") else f"Cocina del {pais}",
             f"{pais}.", "Ordenadas de la más barata a la más cara. Abre una para calcularla para tu familia.")
    try:
        with st.spinner(f"Buscando recetas de {pais}… unos segundos"):
            recetas = recetas_del_dia(cocina, hoy()) + s["extra"].get(cocina, [])
    except n.ErrorIA as e:
        st.error(str(e))
        return

    visibles = s["visibles"].get(cocina, POR_PAGINA)
    cuadricula(recetas[:visibles], f"p{cocina[:3]}")
    st.write("")
    if st.button("Mostrar más", icon=":material/expand_more:", key="mas", width="stretch"):
        if visibles >= len(recetas):  # ya se vieron todas: pedir nuevas a la IA
            esperar_turno()
            with st.spinner("Buscando más recetas…"):
                try:
                    nuevas, _ = n.buscar_recetas(cliente_gemini(), [cocina], BASE_PERSONAS, MAX_PORCION,
                                                 TIEMPO_MAX, excluir=[r.nombre for r in recetas],
                                                 cantidad=POR_PAGINA)
                except n.ErrorIA as e:
                    st.error(str(e))
                    return
            s["extra"][cocina] = s["extra"].get(cocina, []) + nuevas
        s["visibles"][cocina] = visibles + POR_PAGINA
        st.rerun()


# ---------------------------------------------------------------------------
# Página: mi semana
# ---------------------------------------------------------------------------

def pagina_semana():
    menu = st.session_state["menu"]
    d.titulo("Tu plan de la semana", "Mi semana.",
             "Las recetas que elegiste, en una sola lista de compras.")
    if not menu:
        with st.container(border=True, key="tarjeta"):
            st.markdown("Todavía no agregas recetas. Elige un país y pulsa **A mi semana** en las que te gusten.")
            st.button("Ver recetas", icon=":material/restaurant_menu:", on_click=ir, args=("inicio",),
                      type="primary")
        return

    lista = n.lista_de_compras(menu)
    porciones = sum(r.porciones for r in menu)
    d.resumen([
        ("Recetas", str(len(menu)), False),
        ("Compras de la semana", f"${lista['total']:.2f}", True),
        ("Lo que cocinas", f"${n.costo_menu(menu):.2f}", False),
        ("Promedio por porción", f"${n.costo_menu(menu) / max(porciones, 1):.2f}", False),
    ])
    st.caption("“Compras” es lo que pagas en la tienda (paquetes enteros). “Lo que cocinas” es solo lo que usan "
               "las recetas: la diferencia es lo que te sobra para otras comidas.")

    with st.container(border=True, key="tarjeta"):
        st.subheader("Tus recetas")
        for i, r in enumerate(menu):
            c1, c2, c3 = st.columns([4, 1.6, 1], vertical_alignment="center")
            c1.markdown(f"**{r.nombre}** · {r.cocina} · para {r.porciones}")
            c2.markdown(f"**${n.costo_porcion(r):.2f}** por porción  \n${n.costo_receta(r):.2f} en total")
            if c3.button("Quitar", key=f"quitar_{i}", icon=":material/close:", width="stretch"):
                alternar_menu(r)
                st.rerun()

        st.subheader("Lista de compras")
        st.dataframe(lista["comprar"], hide_index=True, width="stretch", height=alto(lista["comprar"]),
                     column_config={"Precio": st.column_config.NumberColumn(format="$%.2f"),
                                    "Para": st.column_config.TextColumn(width="medium")})
        if lista["despensa"]:
            st.caption("Revisa si ya tienes en casa: " + ", ".join(f["Ingrediente"] for f in lista["despensa"]))
        b1, b2 = st.columns(2, gap="medium")
        b1.download_button("Descargar lista", n.texto_lista(menu, lista).encode("utf-8"), "lista_sazon.txt",
                           "text/plain", icon=":material/download:", width="stretch")
        b2.link_button("Ver dónde comprar más barato en canastas.", n.enlace_canastas(lista),
                       icon=":material/shopping_basket:", width="stretch")

    seccion_sobrantes(lista)


def seccion_sobrantes(lista):
    st.write("")
    with st.container(border=True, key="tarjeta_sobra"):
        st.subheader("♻️ Lo que te sobra")
        if not lista["sobrantes"]:
            st.markdown("¡Bien! Con estas recetas casi no te sobra nada.")
            return
        for s in lista["sobrantes"]:
            st.markdown(f"- **{s['nombre']}**: te queda cerca del **{s['sobra']:.0%}** de {s['presentacion']}")
        if st.button("Darme ideas para aprovecharlo", icon=":material/lightbulb:", type="primary"):
            s_ = st.session_state
            esperar_turno()
            cocinas = sorted({r.cocina for r in s_["menu"] if r.cocina in n.COCINAS}) or n.COCINAS[:4]
            with st.spinner("Buscando recetas con lo que te sobra…"):
                try:
                    s_["ideas_sobra"], _ = n.buscar_recetas(
                        cliente_gemini(), cocinas, s_["personas"], MAX_PORCION, TIEMPO_MAX,
                        excluir=[r.nombre for r in s_["menu"]], sobrantes=[x["nombre"] for x in lista["sobrantes"]])
                except n.ErrorIA as e:
                    st.error(str(e))
    if st.session_state["ideas_sobra"]:
        st.write("")
        st.markdown("**Ideas para aprovechar lo que sobra**")
        cuadricula(st.session_state["ideas_sobra"], "sob")


# ---------------------------------------------------------------------------
# Página principal
# ---------------------------------------------------------------------------

d.aplicar_estilos()
d.cabecera()
pagina = st.session_state["pagina"]
col_menu, col_pagina = st.columns([1, 3], gap="large")
with col_menu:
    d.menu("semana" if pagina == "semana" else "inicio", ir, len(st.session_state["menu"]))
with col_pagina:
    {"inicio": pagina_inicio, "pais": pagina_pais, "semana": pagina_semana}.get(pagina, pagina_inicio)()

st.divider()
st.caption("sazón. · hermana de canastas. · IA: Google Gemini · Fotos: [Wikimedia Commons](https://commons.wikimedia.org) · "
           "Precios y valores nutricionales aproximados.")
