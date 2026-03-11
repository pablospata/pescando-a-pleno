"""
Generador de copy para catálogo impreso — Pescando a Pleno

Lee la selección V2, el catálogo organizado y las descripciones scrapeadas,
calcula los precios mayoristas en ARS y genera un .txt con el copy completo.

Fórmula de precio:
    precio_mayorista_ars = precio_usd × TIPO_CAMBIO × (1 + COSTO_ENVIO) × (1 + MARGEN)

Uso:
    python generar_copy_catalogo.py
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

# ─── Configuración ────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
CATALOGO_PATH = BASE_DIR / "catalogo-organizado.json"
DESCRIPCIONES_PATH = BASE_DIR / "descripciones-catalogo.json"
SELECCION_PATH = BASE_DIR / "seleccion-catalogo-v2.txt"
OUTPUT_PATH = BASE_DIR / "copy-catalogo-preview.txt"

# Parámetros de precio
TIPO_CAMBIO = 1488        # USD → ARS
COSTO_ENVIO = 0.18        # 18%
MARGEN = 0.50             # 50%
FACTOR_TOTAL = TIPO_CAMBIO * (1 + COSTO_ENVIO) * (1 + MARGEN)  # = 2634.24


# ─── Traducciones PT → ES ─────────────────────────────────────────

TRADUCCIONES = {
    # Términos de pesca
    "isca": "señuelo",
    "iscas": "señuelos",
    "vara": "caña",
    "varas": "cañas",
    "molinete": "reel frontal",
    "molinetes": "reels frontales",
    "carretilha": "reel baitcast",
    "carretilhas": "reels baitcast",
    "anzol": "anzuelo",
    "anzóis": "anzuelos",
    "linha": "línea",
    "linhas": "líneas",
    "garatéia": "triple",
    "garatéias": "triples",
    "garateia": "triple",
    "garateias": "triples",
    "pesca esportiva": "pesca deportiva",
    "pesca profissional": "pesca profesional",
    "água doce": "agua dulce",
    "água salgada": "agua salada",
    "água salobra": "agua salobre",
    "arremesso": "lanzamiento",
    "arremessos": "lanzamientos",
    "recolhimento": "recogida",
    "fisgada": "clavada",
    "fisgadas": "clavadas",
    "freio": "freno",
    "rolamento": "rulemán",
    "rolamentos": "rulemanes",
    "lastro": "lastre",
    "lastros": "lastres",
    "pitão": "ojal",
    "barbela": "paleta",
    "nado": "natación",
    "peixe": "pez",
    "peixes": "peces",
    "pescador": "pescador",
    "pescadores": "pescadores",
    "predador": "predador",
    "predadores": "predadores",
    "superfície": "superficie",
    "meia água": "media agua",
    "fundo": "fondo",
    "afundante": "hundimiento",
    "flutuante": "flotante",
    "mergulho": "inmersión",
    "combate": "pelea",
    "combates": "peleas",
    "briga": "pelea",
    "brigas": "peleas",
    "resistência": "resistencia",
    "durabilidade": "durabilidad",
    "desempenho": "rendimiento",
    "equilíbrio": "equilibrio",
    "equipamento": "equipo",
    "equipamentos": "equipos",
    "arame contínuo": "alambre continuo",
    "aço inox": "acero inoxidable",
    "plástico ABS": "plástico ABS",

    # Términos generales
    "desenvolvido": "desarrollado",
    "desenvolvida": "desarrollada",
    "projetado": "diseñado",
    "projetada": "diseñada",
    "fabricado": "fabricado",
    "fabricada": "fabricada",
    "equipado": "equipado",
    "equipada": "equipada",
    "construído": "construido",
    "construída": "construida",
    "oferece": "ofrece",
    "oferecendo": "ofreciendo",
    "permite": "permite",
    "permitindo": "permitiendo",
    "proporciona": "proporciona",
    "proporcionando": "proporcionando",
    "garante": "garantiza",
    "garantindo": "garantizando",
    "apresenta": "presenta",
    "disponível": "disponible",
    "ideal": "ideal",
    "excelente": "excelente",
    "versatilidade": "versatilidad",
    "versátil": "versátil",
    "precisão": "precisión",
    "potência": "potencia",
    "suave": "suave",
    "leve": "liviano",
    "leves": "livianos",
    "robusto": "robusto",
    "robusta": "robusta",
    "silenciosa": "silenciosa",
    "conforto": "confort",
    "escolha": "elección",
    "perfeita": "perfecta",
    "perfeito": "perfecto",
    "melhor": "mejor",
    "melhores": "mejores",
    "maior": "mayor",
    "maiores": "mayores",
    "menor": "menor",
    "menores": "menores",
    "alta": "alta",
    "alto": "alto",
    "grandes": "grandes",
    "grande": "grande",
    "pequeno": "pequeño",
    "pequena": "pequeña",
    "diferentes": "diferentes",
    "diversas": "diversas",
    "diversos": "diversos",
    "custo-benefício": "relación costo-beneficio",
    "tamanhos": "tamaños",
    "tamanho": "tamaño",
    "comprimento": "largo",
    "peso": "peso",
    "ação": "acción",
    "velocidade": "velocidad",
    "som": "sonido",
    "sons": "sonidos",
    "cor": "color",
    "cores": "colores",
    "acabamento": "acabado",
    "reforçado": "reforzado",
    "reforçada": "reforzada",
    "agilidade": "agilidad",
    "estabilidade": "estabilidad",
    "confiabilidade": "confiabilidad",
    "confiável": "confiable",
    "funcional": "funcional",
    "eficiente": "eficiente",
    "eficiência": "eficiencia",
    "ataque": "ataque",
    "ataques": "ataques",
    "instinto": "instinto",
    "instintivo": "instintivo",
    "movimento": "movimiento",
    "movimentos": "movimientos",
    "trabalho": "trabajo",
    "trabalhada": "trabajada",
    "lançamento": "lanzamiento",
    "lançamentos": "lanzamientos",
    "longos": "largos",
    "longo": "largo",
    "precisos": "precisos",
    "preciso": "preciso",
    "ventos": "vientos",
    "vento": "viento",
    "fortes": "fuertes",
    "forte": "fuerte",
    "condições": "condiciones",
    "condição": "condición",
    "modalidades": "modalidades",
    "assinada": "firmado",
    "assinado": "firmado",
    "projeto": "proyecto",
    "campo": "campo",
    "jornadas": "jornadas",
    "jornada": "jornada",
    "resultados": "resultados",
    "resultado": "resultado",
    "reais": "reales",
    "real": "real",
    "definitiva": "definitiva",
    "definitivo": "definitivo",
    "completa": "completa",
    "completo": "completo",
    "profissional": "profesional",
    "profissionais": "profesionales",
    "também": "también",
    "através": "a través",
    "além": "además",
    "ou": "o",
    "e": "y",
    "para": "para",
    "com": "con",
    "sem": "sin",
    "mais": "más",
    "muito": "muy",
    "desde": "desde",
    "até": "hasta",
    "entre": "entre",
    "sobre": "sobre",
    "sob": "bajo",
    "cada": "cada",
    "todo": "todo",
    "toda": "toda",
    "todos": "todos",
    "todas": "todas",
    "mesmo": "incluso",
    "qualquer": "cualquier",
}


def traducir_descripcion(texto_pt: str) -> str:
    """Traduce un texto del portugués al español argentino (aproximado)."""
    if not texto_pt:
        return ""

    texto = texto_pt

    # Limpiar: quitar la tabla de modelos al final
    # Buscar "MODELOS" y cortar ahí
    idx = texto.find("MODELOS")
    if idx > 0:
        texto = texto[:idx].strip()

    # Limpiar patrones de especificación técnica al final
    for pattern in [
        r'\nModelo\n.*$',
        r'\nCód / Cód Barras.*$',
        r'\nQuantidade.*$',
    ]:
        texto = re.sub(pattern, '', texto, flags=re.DOTALL)

    # Reemplazar palabras/frases — orden de mayor a menor longitud
    sorted_keys = sorted(TRADUCCIONES.keys(), key=len, reverse=True)
    for pt_word in sorted_keys:
        es_word = TRADUCCIONES[pt_word]
        # Solo reemplazar palabras completas (word boundary)
        pattern = re.compile(r'\b' + re.escape(pt_word) + r'\b', re.IGNORECASE)
        # Preservar capitalización del original
        def repl(match):
            original = match.group(0)
            if original[0].isupper():
                return es_word.capitalize()
            return es_word
        texto = pattern.sub(repl, texto)

    # Limpiar líneas vacías múltiples
    texto = re.sub(r'\n{3,}', '\n\n', texto)

    return texto.strip()


def precio_ars(precio_usd: float) -> int:
    """Calcula el precio mayorista en ARS, redondeado."""
    return round(precio_usd * FACTOR_TOTAL)


def formatear_precio_ars(monto: int) -> str:
    """Formatea un monto ARS con separador de miles."""
    return f"${monto:,.0f}".replace(",", ".")


# ─── Mapeo de selección V2 a productos del catálogo ────────────────

def parsear_seleccion_v2() -> list[dict]:
    """
    Parsea seleccion-catalogo-v2.txt y retorna una lista de items.  
    Cada item: { 'numero', 'nombre', 'descripcion_corta', 'seccion', 'subseccion' }
    """
    items = []
    seccion_actual = ""
    subseccion_actual = ""

    with open(SELECCION_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()

            # Detectar sección principal (entre líneas de guiones)
            sec_match = re.match(r'\s{2}(\S.+?)\s*\((\d+)\s*productos?\)', line)
            if sec_match:
                seccion_actual = sec_match.group(1).strip()
                continue

            # Detectar subsección (GAMA ENTRADA, MARINE SPORTS, etc.)
            if re.match(r'^[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ /\-]+\s*—', line):
                subseccion_actual = line.split("—")[0].strip()
                continue
            if re.match(r'^[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ ]+\(', line):
                subseccion_actual = line.split("(")[0].strip()
                continue

            # Detectar producto numerado
            m = re.match(r'\s*(\d+)\.\s+(.+?)\s*—\s*(.+?)(?:\s*\([\$\d].*\))?\s*$', line)
            if m:
                items.append({
                    "numero": int(m.group(1)),
                    "nombre": m.group(2).strip(),
                    "descripcion_corta": m.group(3).strip(),
                    "seccion": seccion_actual,
                    "subseccion": subseccion_actual,
                })
                continue

            # Producto sin guión ni descripción (combos, etc.)
            m2 = re.match(r'\s*(\d+)\.\s+(.+?)(?:\s*\([\$\d].*\))?\s*$', line)
            if m2 and not re.match(r'\s*\d+\.\s*$', line):
                nombre = m2.group(2).strip()
                if len(nombre) > 5 and not nombre.startswith("="):
                    items.append({
                        "numero": int(m2.group(1)),
                        "nombre": nombre,
                        "descripcion_corta": "",
                        "seccion": seccion_actual,
                        "subseccion": subseccion_actual,
                    })

    return items


def buscar_producto_catalogo(nombre_seleccion: str, productos: list[dict], seccion: str) -> list[dict]:
    """
    Busca productos del catálogo que coincidan con un nombre de la selección V2.
    Retorna todos los productos que coinciden (variantes).
    """
    # Extraer keywords del nombre
    nombre_clean = nombre_seleccion.upper()
    # Quitar marcas del nombre para buscar
    for marca in ["MARINE SPORTS ", "DAIWA ", "DUEL ", "MEGABASS ", "OSP ", "YO-ZURI "]:
        nombre_clean = nombre_clean.replace(marca, "")
    nombre_clean = nombre_clean.strip()

    keywords = [kw for kw in nombre_clean.split() if len(kw) > 1]
    if not keywords:
        return []

    # Mapeo de secciones del TXT a categorías del JSON
    seccion_to_cat = {
        "SEÑUELOS ARTIFICIALES": "Señuelos Artificiales",
        "CAÑAS": "Cañas",
        "REELS BAITCAST": "Reels Baitcast",
        "REELS FRONTALES": "Reels Frontales",
        "COMBOS": "Combos",
        "LÍNEAS": "Líneas",
        "ANZUELOS": "Anzuelos",
        "ACCESORIOS": "Accesorios",
        "MOTORES ELÉCTRICOS": "Motores",
        "INDUMENTARIA": "Indumentaria",
        "TERMINAL / GIRADORES / TRIPLES": ["Terminal", "Giradores", "Triples", "Cables de Acero"],
    }

    cat_filtro = seccion_to_cat.get(seccion, seccion)
    if isinstance(cat_filtro, str):
        cat_filtro = [cat_filtro]

    # Buscar por subcategoría/nombre
    matches = []
    for p in productos:
        if p.get("categoria") not in cat_filtro:
            continue

        nombre_prod = (p.get("nombre_es") or p.get("nombre_original") or "").upper()
        sub = (p.get("subcategoria") or "").upper()

        # Intentar match por keywords principales
        if all(kw in nombre_prod or kw in sub for kw in keywords[:2]):
            matches.append(p)

    # Si no encontramos, intentar con solo la primera keyword
    if not matches and keywords:
        for p in productos:
            if p.get("categoria") not in cat_filtro:
                continue
            nombre_prod = (p.get("nombre_es") or "").upper()
            sub = (p.get("subcategoria") or "").upper()
            if keywords[0] in nombre_prod or keywords[0] in sub:
                matches.append(p)

    return matches


def buscar_descripcion(subcategoria: str, marca: str, descripciones: dict) -> str:
    """Busca la descripción traducida para una subcategoría."""
    if not descripciones:
        return ""

    # 1. Buscar por subcategoría exacta
    if subcategoria in descripciones:
        desc = descripciones[subcategoria].get("descripcion_pt", "")
        if desc:
            return traducir_descripcion(desc)

    # 2. Buscar case-insensitive
    sub_upper = subcategoria.upper()
    for key, val in descripciones.items():
        if key.upper() == sub_upper:
            desc = val.get("descripcion_pt", "")
            if desc:
                return traducir_descripcion(desc)

    # 3. Buscar parcial
    for key, val in descripciones.items():
        if sub_upper in key.upper() or key.upper() in sub_upper:
            desc = val.get("descripcion_pt", "")
            if desc:
                return traducir_descripcion(desc)

    return ""


# ─── Generar Copy ──────────────────────────────────────────────────

def main():
    print("📦 Cargando datos...")

    # Cargar catálogo
    with open(CATALOGO_PATH, "r", encoding="utf-8") as f:
        catalogo = json.load(f)
    productos = catalogo["productos"]
    print(f"  Catálogo: {len(productos)} productos")

    # Cargar descripciones
    descripciones = {}
    if DESCRIPCIONES_PATH.exists():
        with open(DESCRIPCIONES_PATH, "r", encoding="utf-8") as f:
            descripciones = json.load(f)
        print(f"  Descripciones: {len(descripciones)} entradas")
    else:
        print("  ⚠️ No se encontró descripciones-catalogo.json, se generará sin descripciones")

    # Parsear selección V2
    items_v2 = parsear_seleccion_v2()
    print(f"  Selección V2: {len(items_v2)} productos")

    # Generar copy
    lines = []
    lines.append("=" * 70)
    lines.append("CATÁLOGO MAYORISTA — PESCANDO A PLENO")
    lines.append("Precios mayoristas en ARS (Pesos Argentinos)")
    lines.append(f"Tipo de cambio: USD 1 = ARS {TIPO_CAMBIO:,}".replace(",", "."))
    lines.append(f"Incluye envío (+{int(COSTO_ENVIO*100)}%) y margen ({int(MARGEN*100)}%)")
    lines.append(f"Factor total: USD × {FACTOR_TOTAL:,.2f} = ARS".replace(",", "."))
    lines.append("=" * 70)
    lines.append("")

    # Agrupar por sección
    por_seccion = defaultdict(list)
    for item in items_v2:
        por_seccion[item["seccion"]].append(item)

    total_encontrados = 0
    total_con_desc = 0

    for seccion, items in por_seccion.items():
        lines.append("")
        lines.append("─" * 70)
        lines.append(f"  {seccion} ({len(items)} productos)")
        lines.append("─" * 70)
        lines.append("")

        for item in items:
            nombre = item["nombre"]
            desc_corta = item["descripcion_corta"]
            numero = item["numero"]

            # Buscar en catálogo
            matches = buscar_producto_catalogo(nombre, productos, seccion)

            if matches:
                total_encontrados += 1
                # Calcular rango de precios ARS
                precios_usd = [p.get("precio_usd", 0) for p in matches if p.get("precio_usd")]
                precio_min = min(precios_usd) if precios_usd else 0
                precio_max = max(precios_usd) if precios_usd else 0

                precio_min_ars = precio_ars(precio_min)
                precio_max_ars = precio_ars(precio_max)

                # Tomar el producto representativo (el primero)
                rep = matches[0]
                marca = rep.get("marca", "")
                subcategoria = rep.get("subcategoria", "")

                # Specs
                specs = []
                if rep.get("tamaño_cm"):
                    specs.append(f"{rep['tamaño_cm']}cm")
                if rep.get("peso_g"):
                    specs.append(f"{rep['peso_g']}g")
                if rep.get("tipo_accion"):
                    specs.append(rep["tipo_accion"])
                specs_str = f" | {', '.join(specs)}" if specs else ""

                # Precio formateado
                if precio_min_ars == precio_max_ars or abs(precio_min - precio_max) < 0.01:
                    precio_str = f"Precio mayorista: {formatear_precio_ars(precio_min_ars)}"
                else:
                    precio_str = f"Precio mayorista: {formatear_precio_ars(precio_min_ars)} — {formatear_precio_ars(precio_max_ars)}"

                # Descripción
                descripcion = buscar_descripcion(subcategoria, marca, descripciones)
                if descripcion:
                    total_con_desc += 1
                    # Limitar a 3-4 líneas
                    desc_lines = descripcion.split("\n")
                    # Tomar los primeros párrafos significativos
                    desc_final = []
                    chars = 0
                    for dl in desc_lines:
                        dl = dl.strip()
                        if not dl or chars > 400:
                            break
                        desc_final.append(dl)
                        chars += len(dl)
                    descripcion = " ".join(desc_final)
                    if len(descripcion) > 500:
                        descripcion = descripcion[:497] + "..."

                lines.append(f"  {numero}. {nombre}")
                lines.append(f"     Marca: {marca}{specs_str}")
                if desc_corta:
                    lines.append(f"     {desc_corta}")
                lines.append(f"     {precio_str}")
                lines.append(f"     Variantes disponibles: {len(matches)}")
                if descripcion:
                    lines.append(f"     ──")
                    lines.append(f"     {descripcion}")
                lines.append("")

            else:
                # No encontrado en el catálogo
                lines.append(f"  {numero}. {nombre}")
                if desc_corta:
                    lines.append(f"     {desc_corta}")
                lines.append(f"     [⚠️ No encontrado en catálogo organizado]")
                lines.append("")

    # Resumen final
    lines.append("")
    lines.append("=" * 70)
    lines.append("RESUMEN")
    lines.append("=" * 70)
    lines.append(f"  Productos en selección V2: {len(items_v2)}")
    lines.append(f"  Encontrados en catálogo:   {total_encontrados}")
    lines.append(f"  Con descripción:           {total_con_desc}")
    lines.append(f"  Sin encontrar:             {len(items_v2) - total_encontrados}")
    lines.append("")
    lines.append(f"  Tipo de cambio:  USD 1 = ARS {TIPO_CAMBIO:,}".replace(",", "."))
    lines.append(f"  Costo envío:     +{int(COSTO_ENVIO*100)}%")
    lines.append(f"  Margen:          +{int(MARGEN*100)}%")
    lines.append(f"  Factor total:    × {FACTOR_TOTAL:,.2f}".replace(",", "."))
    lines.append("")

    # Escribir
    text = "\n".join(lines)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"\n✅ Copy generado: {OUTPUT_PATH}")
    print(f"   {len(items_v2)} productos | {total_encontrados} encontrados | {total_con_desc} con descripción")


if __name__ == "__main__":
    main()
