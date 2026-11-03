"""Diseño visual de sazona.: misma familia que canastas., en terracota.

Colores y fuente base están en .streamlit/config.toml; aquí van la cabecera,
los títulos, las tarjetas de receta y el menú. Solo presentación.
"""

import html

import streamlit as st

TERRA = "#B5482A"        # color principal (logo, precios)
BOTON = "#AD5F38"        # terracota arcilla para botones: menos rojo
TERRA_CLARO = "#F7E6DE"
TEXTO = "#2A1F1A"
GRIS = "#7D6F68"
BORDE = "#EADFD8"
FONDO = "#F7F4F1"

# Tonos terrosos que combinan con el terracota, para los botones de país (fondo, texto). Alternan oscuro/claro.
TONOS = [("#5E6B3A", "#FFFFFF"),   # oliva
         ("#E0B04A", TEXTO),       # mostaza
         ("#2F5D62", "#FFFFFF"),   # azul petróleo
         ("#A8BFA0", TEXTO),       # salvia
         ("#3E5A7A", "#FFFFFF"),   # azul tierra
         ("#D9956A", TEXTO)]       # arcilla

# Isotipo de sazona.: la S baja y se convierte en un plato hondo servido.
ISOTIPO = ("M29.6 9.6 C29.6 6.1 26.8 3.6 23.3 3.6 C19.7 3.6 16.9 6.2 16.9 9.5 C16.9 13 19.6 16.6 23.4 16.6 "
           "L41.5 16.6 A17.5 15.5 0 0 1 6.5 16.6 L13.5 16.6 M18.5 37.2 H29.5")


def isotipo_svg(color: str = "#fff", tam: int = 28) -> str:
    return (f'<svg width="{tam}" height="{tam}" viewBox="0 0 48 48" fill="none" stroke="{color}" stroke-width="3.6" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="{ISOTIPO}"/></svg>')


TONOS_CSS = "\n".join(
    f'.st-key-paises [class*="st-key-tono{i}_"] button {{ background:{fondo} !important; border:none !important; '
    f'color:{texto} !important; }} .st-key-paises [class*="st-key-tono{i}_"] button p {{ color:{texto} !important; }}'
    for i, (fondo, texto) in enumerate(TONOS))

CSS = f"""
<style>
.block-container {{ max-width: 1240px; padding-top: 0 !important; padding-bottom: 3rem; }}
header[data-testid="stHeader"] {{ background: transparent; }}

.sz-cabecera {{ display:flex; justify-content:space-between; align-items:center; gap:1rem;
  background:#fff; border-bottom:1px solid {BORDE}; padding:1.3rem 0; margin-bottom:2.2rem;
  box-shadow:0 0 0 100vmax #fff; clip-path:inset(0 -100vmax); }}
.sz-logo {{ display:flex; align-items:center; gap:.85rem; }}
.st-key-logo_wrap {{ position:relative; gap:0 !important; }}
.st-key-logo_btn {{ position:absolute !important; top:0; left:0; width:280px !important; height:100%; z-index:5; }}
.st-key-logo_btn button {{ width:100%; height:100%; opacity:0; cursor:pointer; }}
.sz-logo .icono {{ width:48px; height:48px; border-radius:13px; background:{TERRA}; display:grid; place-items:center; }}
.sz-logo .nombre {{ font-size:1.95rem; font-weight:800; letter-spacing:-.035em; color:{TEXTO}; }}
.sz-logo .punto {{ color:{TERRA}; }}
.sz-lema {{ color:{GRIS}; font-size:.95rem; }}

.sz-ceja {{ font-size:.78rem; letter-spacing:.22em; font-weight:700; color:{GRIS}; text-transform:uppercase; margin:0 0 .5rem; }}
.sz-titulo {{ font-size:clamp(2.1rem, 4.6vw, 3.3rem); font-weight:800; letter-spacing:-.045em; line-height:1.05;
  color:{TEXTO}; margin:0 0 1rem; }}
.sz-sub {{ color:{GRIS}; font-size:1.08rem; line-height:1.7; margin:0 0 1.6rem; }}

.st-key-tarjeta {{ background:#fff; border-radius:22px !important; padding:1.8rem 2rem !important; }}
[data-testid="stWidgetLabel"] p {{ font-weight:600; font-size:1.0rem; color:{TEXTO}; }}
[data-testid="stTextInputRootElement"], .stNumberInput [data-testid="stNumberInputContainer"],
.stMultiSelect [data-baseweb="select"] > div, .stSelectbox [data-baseweb="select"] > div {{ background:#fff !important; }}
[data-testid="stFormSubmitButton"] button, .stButton button[kind="primary"] {{ min-height:3.2rem; }}
[data-testid="stFormSubmitButton"] button p, .stButton button[kind="primary"] p {{ font-size:1.05rem; font-weight:700; }}
.stMultiSelect [data-baseweb="tag"] {{ background:{TERRA_CLARO} !important; color:{TEXTO} !important; }}
.stMultiSelect [data-baseweb="tag"] span {{ color:{TEXTO} !important; }}

/* Tarjetas de receta */
[class*="st-key-rc_"] {{ background:#fff; border-radius:20px !important; padding:.8rem .8rem 1rem !important;
  height:100%; }}
[class*="st-key-rc_"] [data-testid="stImage"] img {{ border-radius:14px; aspect-ratio:4/3; object-fit:cover; width:100%; }}
.sz-foto-vacia {{ border-radius:14px; aspect-ratio:4/3; background:{TERRA_CLARO}; display:grid; place-items:center;
  margin-bottom:.4rem; }}
.sz-chips {{ display:flex; gap:.4rem; flex-wrap:wrap; margin:.3rem 0 .4rem; }}
.sz-chip {{ font-size:.75rem; font-weight:700; color:{TERRA}; background:{TERRA_CLARO}; border-radius:999px;
  padding:.15rem .6rem; }}
[data-testid="stDialog"] button[aria-label="Close"] {{ position:fixed; top:1.4rem; right:1.6rem; z-index:1000;
  width:2.6rem; height:2.6rem; border-radius:999px; background:{BOTON}; color:#fff; opacity:1;
  box-shadow:0 2px 8px rgba(0,0,0,.18); }}
[data-testid="stDialog"] button[aria-label="Close"] svg {{ width:1.4rem; height:1.4rem; color:#fff; fill:#fff; }}
[data-testid="stDialog"] button[aria-label="Close"]:hover {{ filter:brightness(1.1); }}
.sz-alergia {{ display:inline-block; font-size:.78rem; font-weight:700; color:#7A4A00; background:#FCEBC4;
  border:1px solid #E9C46A; border-radius:8px; padding:.15rem .55rem; margin:.1rem 0 .35rem; }}
.sz-chip.barata {{ color:#fff; background:#5E6B3A; }}
.sz-chip.gris {{ color:{GRIS}; background:#F1ECE8; font-weight:600; }}
.sz-nombre {{ font-size:1.2rem; font-weight:800; letter-spacing:-.02em; color:{TEXTO}; line-height:1.2; margin:.1rem 0 .3rem; }}
.sz-desc {{ font-size:.92rem; color:{GRIS}; line-height:1.45; margin:0 0 .7rem; min-height:2.7em; }}
.sz-precio b {{ display:block; font-size:1.75rem; font-weight:800; color:{TERRA}; letter-spacing:-.03em; line-height:1.1; }}
.sz-precios {{ display:flex; gap:.6rem; margin:.2rem 0 .3rem; }}
.sz-precios .sz-precio {{ flex:1; background:{TERRA_CLARO}; border-radius:12px; padding:.5rem .7rem; }}
.sz-precios .sz-precio.total {{ background:{BOTON}; }}
.sz-precios .sz-precio.total b, .sz-precios .sz-precio.total span {{ color:#fff; }}
.sz-precios .sz-precio b {{ font-size:1.45rem; }}
.sz-precio span {{ display:block; font-size:.86rem; color:{GRIS}; margin-top:.1rem; }}
[class*="st-key-rc_"] .stButton {{ margin-top:-.2rem; }}
.sz-nutri {{ font-size:.82rem; color:{GRIS}; margin:.2rem 0 .7rem; }}
.sz-credito {{ font-size:.72rem; color:{GRIS}; margin-top:-.2rem; }}
.sz-credito a {{ color:{GRIS}; }}
[class*="st-key-en_menu_"] button {{ background:{TERRA_CLARO}; border-color:{TERRA_CLARO}; color:{TERRA}; }}

/* Botones en terracota arcilla (no rojo) */
.stButton button[kind="primary"], [data-testid="stFormSubmitButton"] button {{ background:{BOTON} !important;
  border-color:{BOTON} !important; color:#fff !important; }}
.stButton button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] button:hover {{ background:#96502E !important;
  border-color:#96502E !important; }}
.stButton button[kind="secondary"], [data-testid="stDownloadButton"] button, [data-testid="stLinkButton"] a {{
  border-color:{BOTON}; color:{BOTON}; }}
.stButton button[kind="secondary"]:hover, [data-testid="stDownloadButton"] button:hover,
[data-testid="stLinkButton"] a:hover {{ background:{TERRA_CLARO}; border-color:{BOTON}; color:{BOTON}; }}

/* Inicio: receta sugerida y países */
.st-key-sugerida {{ background:#fff; border-radius:22px !important; padding:1.4rem !important; border-color:{BORDE} !important; }}
.st-key-sugerida [data-testid="stImage"] img {{ border-radius:16px; aspect-ratio:4/3; object-fit:cover; width:100%; }}
.sz-ceja-terra {{ color:{TERRA}; }}
.sz-seccion {{ font-size:1.35rem; font-weight:800; letter-spacing:-.02em; color:{TEXTO}; margin:1.2rem 0 .8rem; }}
{TONOS_CSS}
.st-key-paises button:hover {{ filter:brightness(.92); }}
.st-key-paises button {{ aspect-ratio:1 / 1; width:100%; height:auto; min-height:0 !important; border-radius:18px; }}
.st-key-paises button p {{ font-size:1.15rem !important; font-weight:700; text-align:center; }}
.st-key-volver button {{ border:none; background:transparent; padding-left:0; color:{BOTON}; }}

.st-key-menu .stButton button {{ border:none !important; }}
.st-key-menu .st-key-nav_on button {{ color:{TEXTO} !important; background:{TERRA_CLARO} !important; }}
.st-key-menu [class*="st-key-nav_off"] button {{ color:#5E524C !important; }}
[class*="st-key-en_menu_"] .stButton button {{ background:{TERRA_CLARO}; border-color:{TERRA_CLARO}; }}

[data-testid="stHeaderActionElements"] {{ display:none; }}

/* Costos según personas */
.sz-costos {{ display:flex; gap:.8rem; margin:.4rem 0 1rem; }}
.sz-costo {{ flex:1; background:{TERRA_CLARO}; border-radius:14px; padding:.8rem 1rem; }}
.sz-costo small {{ color:{GRIS}; font-size:.82rem; }}
.sz-costo b {{ display:block; color:{TERRA}; font-size:1.7rem; font-weight:800; letter-spacing:-.03em; }}
.sz-costo.total {{ background:{BOTON}; }}
.sz-costo.total small, .sz-costo.total b {{ color:#fff; }}

/* Resumen de la semana */
.sz-resumen {{ display:flex; gap:1rem; flex-wrap:wrap; margin:.4rem 0 1.2rem; }}
.sz-dato {{ background:#fff; border:1px solid {BORDE}; border-radius:16px; padding:1rem 1.2rem; flex:1 1 160px; }}
.sz-dato small {{ color:{GRIS}; font-size:.82rem; }}
.sz-dato b {{ display:block; font-size:1.6rem; font-weight:800; color:{TEXTO}; letter-spacing:-.03em; }}
.sz-dato.destacado b {{ color:{TERRA}; }}

/* Menú lateral */
.sz-menu-ceja {{ font-size:.74rem; letter-spacing:.17em; white-space:nowrap; font-weight:700; color:{GRIS};
  text-transform:uppercase; margin:.6rem 0 1rem .2rem; }}
.st-key-nav_on button, [class*="st-key-nav_off"] button {{ justify-content:flex-start; border:none; padding:1rem 1.2rem;
  min-height:3.4rem; border-radius:14px; }}
.st-key-nav_on button {{ background:{TERRA_CLARO}; color:{TEXTO}; }}
.st-key-nav_on button p, [class*="st-key-nav_off"] button p {{ font-size:1.05rem; }}
.st-key-nav_on button p {{ font-weight:700; }}
[class*="st-key-nav_off"] button {{ background:transparent; color:#5E524C; }}
[class*="st-key-nav_off"] button:hover {{ background:#F3E9E3; color:{TEXTO}; }}
.st-key-nav_on button [data-testid="stIconMaterial"], [class*="st-key-nav_off"] button [data-testid="stIconMaterial"] {{
  font-size:1.35rem; }}
.st-key-nav_on button div, [class*="st-key-nav_off"] button div {{ justify-content:flex-start; }}
[data-baseweb="select"] > div {{ background:#fff !important; }}
.sz-menu-nota b {{ display:block; color:{TEXTO}; margin-bottom:.5rem; font-size:1rem; }}
.sz-menu-nota {{ color:{GRIS}; font-size:.95rem; line-height:1.75; padding:0 .2rem; }}

@media (max-width: 640px) {{
  .st-key-paises [data-testid="stHorizontalBlock"] {{ flex-direction:row !important; flex-wrap:wrap; gap:.6rem; }}
  .st-key-paises [data-testid="stColumn"] {{ flex:1 1 calc(50% - .3rem) !important; min-width:calc(50% - .3rem) !important; }}
  .sz-lema {{ display:none; }}
  .sz-cabecera {{ margin-bottom:1.4rem; }}
  .st-key-tarjeta {{ padding:1.2rem 1rem !important; }}
  .st-key-menu [data-testid="stElementContainer"]:has(hr),
  .st-key-menu [data-testid="stElementContainer"]:has(.sz-menu-nota),
  .st-key-menu [data-testid="stElementContainer"]:has(.sz-menu-ceja),
  .st-key-menu [data-testid="stElementContainer"]:has([data-testid="stCaptionContainer"]) {{ display:none; }}
  .st-key-menu_botones {{ flex-direction:row !important; gap:.5rem; }}
  .st-key-menu_botones > div {{ flex:1 1 0 !important; min-width:0; }}
  .st-key-nav_on button, [class*="st-key-nav_off"] button {{ min-height:2.8rem; padding:.5rem .55rem; gap:.3rem; }}
  .st-key-nav_on button p, [class*="st-key-nav_off"] button p {{ font-size:.86rem; white-space:nowrap; }}
}}
</style>
"""

NOTAS = {
    "inicio": ("Rico no tiene que ser caro.", "Recetas de todo el mundo, con ingredientes de aquí y su precio por porción."),
    "semana": ("Compra una vez, cocina toda la semana.", "Junta tus recetas en una sola lista y aprovecha lo que sobra."),
}


def aplicar_estilos():
    st.markdown(CSS, unsafe_allow_html=True)


def cabecera(ir=None):
    """Logo + lema. El logo es un botón invisible encima que lleva al inicio."""
    with st.container(key="logo_wrap"):
        _cabecera_html()
        if ir:
            st.button("Ir al inicio", key="logo_btn", on_click=ir, args=("inicio",), help="Ir al inicio")


def _cabecera_html():
    st.markdown(
        f"""<div class="sz-cabecera"><div class="sz-logo"><span class="icono">{isotipo_svg('#fff', 30)}</span>
        <span class="nombre">sazona<span class="punto"> .</span></span></div>
        <div class="sz-lema">Rico, sano y barato.</div></div>""",
        unsafe_allow_html=True,
    )


def titulo(ceja: str, texto: str, sub: str = ""):
    h = f'<p class="sz-ceja">{ceja}</p><h1 class="sz-titulo">{texto}</h1>'
    if sub:
        h += f'<p class="sz-sub">{sub}</p>'
    st.markdown(h, unsafe_allow_html=True)


def menu(activo: str, ir, en_semana: int):
    with st.container(key="menu"):
        st.markdown('<p class="sz-menu-ceja">Tu cocina, organizada</p>', unsafe_allow_html=True)
        with st.container(key="menu_botones"):
            with st.container(key="nav_on" if activo == "inicio" else "nav_off_inicio"):
                st.button("Recetas", icon=":material/restaurant_menu:", on_click=ir, args=("inicio",),
                          width="stretch")
            with st.container(key="nav_on" if activo == "semana" else "nav_off_semana"):
                st.button(f"Mi semana ({en_semana})", icon=":material/calendar_month:", on_click=ir,
                          args=("semana",), width="stretch")
        st.divider()
        fuerte, texto = NOTAS.get(activo, NOTAS["inicio"])
        st.markdown(f'<div class="sz-menu-nota"><b>{fuerte}</b>{texto}</div>', unsafe_allow_html=True)
        st.caption("Precios estimados por IA: confírmalos en la tienda. Fotos libres de Wikimedia Commons.")


def foto_vacia():
    st.markdown(f'<div class="sz-foto-vacia">{isotipo_svg(TERRA, 76)}</div>', unsafe_allow_html=True)


def credito_foto(foto: dict):
    lic = foto.get("licencia") or ""
    if lic and foto.get("licencia_url"):
        lic = f' · <a href="{html.escape(foto["licencia_url"])}" target="_blank">{html.escape(lic)}</a>'
    elif lic:
        lic = f" · {html.escape(lic)}"
    st.markdown(
        f'<div class="sz-credito">Foto: <a href="{html.escape(foto["pagina"])}" target="_blank">'
        f'{html.escape(foto["autor"])}</a>{lic} · {html.escape(foto.get("fuente", ""))}</div>',
        unsafe_allow_html=True,
    )


def precios_tarjeta(por_porcion, total, personas) -> str:
    """Precio por porción y de toda la comida, uno al lado del otro."""
    html_p = f'<div class="sz-precio"><b>${por_porcion:.2f}</b><span>por porción</span></div>'
    if total is None:
        return html_p
    return (f'<div class="sz-precios">{html_p}'
            f'<div class="sz-precio total"><b>${total:.2f}</b><span>todos los ingredientes</span></div></div>')


def info_receta(r, por_porcion: float | None = None, total: float | None = None, personas: int | None = None):
    chips = [f'<span class="sz-chip">{html.escape(r.cocina)}</span>',
             f'<span class="sz-chip gris">{r.tiempo_minutos} min</span>']
    if por_porcion is not None and por_porcion <= 1.00:
        chips.insert(0, '<span class="sz-chip barata">💰 Económica</span>')
    chips += [f'<span class="sz-chip gris">{html.escape(e)}</span>' for e in r.etiquetas[:2]]
    st.markdown(
        f'<div class="sz-chips">{"".join(chips)}</div>'
        + (f'<div class="sz-alergia">⚠️ Contiene alérgenos: {html.escape(", ".join(r.alergenos))}</div>'
           if getattr(r, "alergenos", None) else "")
        + f'<div class="sz-nombre">{html.escape(r.nombre)}</div>'
        f'<p class="sz-desc">{html.escape(r.descripcion)}</p>'
        + (precios_tarjeta(por_porcion, total, personas) if por_porcion is not None else "")
        +         f'<div class="sz-nutri">~{r.calorias_por_porcion} kcal · {r.proteina_g_por_porcion} g de proteína por porción</div>',
        unsafe_allow_html=True,
    )


def resumen(datos: list[tuple[str, str, bool]]):
    partes = "".join(f'<div class="sz-dato{" destacado" if d else ""}"><small>{html.escape(t)}</small><b>{v}</b></div>'
                     for t, v, d in datos)
    st.markdown(f'<div class="sz-resumen">{partes}</div>', unsafe_allow_html=True)


def costos(por_porcion: float, total: float, personas: int):
    gente = "1 persona" if personas == 1 else f"{personas} personas"
    st.markdown(
        f'<div class="sz-costos"><div class="sz-costo"><small>Por porción</small><b>${por_porcion:.2f}</b></div>'
        f'<div class="sz-costo total"><small>Todos los ingredientes ({gente})</small><b>${total:.2f}</b></div></div>',
        unsafe_allow_html=True,
    )


def costo_compras(total: float, personas: int):
    gente = "1 persona" if personas == 1 else f"{personas} personas"
    st.markdown(
        f'<div class="sz-costos"><div class="sz-costo total"><small>Costo de los productos para {gente}</small>'
        f'<b>${total:.2f}</b></div></div>',
        unsafe_allow_html=True,
    )
