"""Selecciona productos para el catálogo impreso - V3: por LÍNEA de producto."""
import json
import re
import sys
from collections import defaultdict, Counter

sys.stdout.reconfigure(encoding="utf-8")

with open("catalogo-organizado.json", "r", encoding="utf-8") as f:
    productos = json.load(f)["productos"]


def extraer_linea(producto):
    """Extrae la línea/familia del producto."""
    nombre = producto.get("nombre_es", producto.get("nombre_original", ""))
    marca = producto.get("marca", "")
    cat = producto.get("categoria", "")
    sub = producto.get("subcategoria", "")

    # Para Cañas y Reels: extraer la SERIE del nombre (Laguna, Venza, Titan, etc.)
    # porque subcategoria es demasiado genérica (Casting/Spinning, Marine Sports)
    if cat in ("Cañas", "Reels Baitcast", "Reels Frontales"):
        n = nombre
        for prefix in ["Caña ", "Reel ", "Telescópica "]:
            if n.startswith(prefix):
                n = n[len(prefix):]
                break
        parts = n.split()
        # Tomar primera palabra como serie (LAGUNA, VENZA, TITAN, etc.)
        if parts:
            serie = parts[0]
            # Si es muy corto, combinar con segunda palabra
            if len(serie) <= 2 and len(parts) > 1:
                serie = f"{parts[0]} {parts[1]}"
            # Limpiar sufijos numéricos modelo (LAGUNA → LAGUNA, no LAGUNA II)
            return serie
        return n[:20]

    # Para el resto: usar subcategoría si existe
    if sub:
        return sub

    # Fallback: primeras palabras del nombre
    n = nombre
    for prefix in ["Señuelo ", "Línea ", "Anzuelo ", "Acc. ",
                    "Combo ", "Motor ", "Remera ", "Girador ", "Cable de Acero ",
                    "Bajo de Línea ", "Triple "]:
        if n.startswith(prefix):
            n = n[len(prefix):]
            break

    parts = n.split()
    if not parts:
        return nombre[:20]

    linea = parts[0]
    if len(linea) <= 2 and len(parts) > 1:
        linea = f"{parts[0]} {parts[1]}"
    return linea


# ─── Agrupar y seleccionar ────────────────────────────────

seleccion = []
por_cat_linea = defaultdict(lambda: defaultdict(list))

for p in productos:
    cat = p.get("categoria", "?")
    linea = extraer_linea(p)
    por_cat_linea[cat][linea].append(p)

marcas_premium = {"Megabass", "Daiwa", "Yo-Zuri", "OSP", "Duel"}

for cat, lineas in por_cat_linea.items():
    for linea, items in lineas.items():
        # Elegir 1 representante por línea
        # Prioridad: marca premium > precio medio-alto
        premium = [i for i in items if i.get("marca") in marcas_premium]
        pool = premium if premium else items

        pool_sorted = sorted(pool, key=lambda x: x.get("precio_usd", 0), reverse=True)
        idx = min(len(pool_sorted) // 3, len(pool_sorted) - 1)
        elegido = pool_sorted[idx]

        seleccion.append({
            "categoria": cat,
            "linea": linea,
            "producto": elegido,
            "variantes_total": len(items),
            "rango_precio": (
                min(i.get("precio_usd", 0) for i in items),
                max(i.get("precio_usd", 0) for i in items),
            ),
        })

# Ordenar
orden_cats = [
    "Señuelos Artificiales", "Cañas", "Reels Baitcast", "Reels Frontales",
    "Combos", "Líneas", "Anzuelos", "Accesorios", "Motores", "Indumentaria",
    "Terminal", "Giradores", "Triples", "Cables de Acero", "Repuestos", "Repuestos Cañas",
]
orden_map = {c: i for i, c in enumerate(orden_cats)}
seleccion.sort(key=lambda x: (
    orden_map.get(x["categoria"], 99),
    x["linea"],
))

# ─── Generar TXT ──────────────────────────────────────────

por_cat = defaultdict(list)
for item in seleccion:
    por_cat[item["categoria"]].append(item)

lines = []
lines.append("=" * 70)
lines.append("SELECCIÓN DE PRODUCTOS PARA CATÁLOGO IMPRESO")
lines.append("Pescando a Pleno - Catálogo 2026")
lines.append("=" * 70)
lines.append("")
lines.append(f"Total de líneas seleccionadas: {len(seleccion)}")
lines.append(f"De un catálogo total de: {len(productos)} productos")
lines.append("")
lines.append("Criterio: Un producto representativo por cada LÍNEA")
lines.append("(cada fila = una familia de productos)")
lines.append("Entre paréntesis: cantidad de variantes disponibles")
lines.append("")

for cat in orden_cats:
    if cat not in por_cat:
        continue
    items = por_cat[cat]
    lines.append("-" * 70)
    lines.append(f"  {cat.upper()} ({len(items)} líneas)")
    lines.append("-" * 70)

    for item in items:
        p = item["producto"]
        nombre = p.get("nombre_es", p.get("nombre_original", "?"))
        marca = p.get("marca", "") or "—"
        precio = p.get("precio_usd", 0)
        codigo = p.get("codigo", "?")
        linea = item["linea"]
        variantes = item["variantes_total"]
        rmin, rmax = item["rango_precio"]

        specs = []
        if p.get("tamaño_cm"):
            specs.append(f"{p['tamaño_cm']}cm")
        if p.get("peso_g"):
            specs.append(f"{p['peso_g']}g")
        if p.get("tipo_accion"):
            specs.append(p["tipo_accion"])
        specs_str = f" ({', '.join(specs)})" if specs else ""

        precio_rango = f"USD {rmin:.2f}-{rmax:.2f}" if rmin != rmax else f"USD {precio:.2f}"

        lines.append(f"  ● {linea} — {marca}{specs_str}")
        lines.append(f"    Ejemplo: {nombre}")
        lines.append(f"    Código ref: {codigo} | {precio_rango} | {variantes} variantes")
        lines.append("")

lines.append("=" * 70)
lines.append("RESUMEN")
lines.append("=" * 70)
total = 0
for cat in orden_cats:
    if cat in por_cat:
        n = len(por_cat[cat])
        total += n
        lines.append(f"  {cat}: {n} líneas")
lines.append(f"  ─────────────────────────────")
lines.append(f"  TOTAL: {total} líneas de producto")

lines.append("")
lines.append("POR MARCA")
lines.append("-" * 40)
marcas_count = Counter(item["producto"].get("marca", "") for item in seleccion)
for m, n in marcas_count.most_common():
    lines.append(f"  {m or 'Sin marca'}: {n}")

text = "\n".join(lines)
with open("seleccion-catalogo.txt", "w", encoding="utf-8") as f:
    f.write(text)

print(text)
