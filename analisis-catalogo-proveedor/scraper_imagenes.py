"""
Scraper de imágenes de productos desde casajapon.com

Lee los códigos del catálogo organizado (JSON) y descarga las imágenes
de cada producto buscándolo en el sitio del proveedor.

Estrategia de búsqueda (por orden):
  1. Busca por código exacto del producto
  2. Si no encuentra, busca por nombre del modelo (subcategoría)
  3. Agrupa productos por modelo para no hacer búsquedas redundantes

Uso:
    python scraper_imagenes.py                    # Corre todo el catálogo
    python scraper_imagenes.py --test 10          # Prueba con los primeros 10 productos
    python scraper_imagenes.py --codigos 10911010 17010014  # Solo estos códigos
    python scraper_imagenes.py --resume           # Retoma desde donde dejó
    python scraper_imagenes.py --solo-modelos     # Una imagen por modelo (más rápido)
"""

import json
import re
import time
import argparse
import logging
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ─── Configuración ────────────────────────────────────────────────
BASE_URL = "https://www.casajapon.com"
SEARCH_URL = f"{BASE_URL}/produtos/filter"
CATALOGO_PATH = Path(__file__).parent / "catalogo-organizado.json"
IMAGENES_DIR = Path(__file__).parent / "imagenes-catalogo"
LOG_PATH = Path(__file__).parent / "scraper_log.json"

CONFIG = {
    "preferred_size": "800",
    "request_delay": 1.0,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,pt-BR;q=0.8,pt;q=0.7,en;q=0.6",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("scraper")


# ─── Utilidades ───────────────────────────────────────────────────

def cargar_catalogo() -> list[dict]:
    with open(CATALOGO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["productos"]


def cargar_log() -> dict:
    if LOG_PATH.exists():
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "descargados": {},
        "modelos_procesados": {},   # modelo -> {codigos, archivos, url}
        "no_encontrados": [],
        "errores": [],
    }


def guardar_log(log_data: dict):
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)


def extraer_nombre_busqueda(producto: dict) -> str:
    """
    Extrae un nombre de búsqueda limpio del producto.
    Ej: 'A. ISCA ANIMAL 100 014 10cm 14g Sup.' -> 'ISCA ANIMAL'
    """
    nombre = producto.get("nombre_original", "")
    # Quitar prefijo 'A. '
    nombre = re.sub(r'^A\.\s+', '', nombre)
    # Tomar solo las primeras 2-3 palabras significativas (nombre del modelo)
    partes = nombre.split()
    # Buscar hasta encontrar un número o tamaño
    nombre_limpio = []
    for p in partes:
        if re.match(r'^\d', p) or re.match(r'^\d+cm', p):
            break
        nombre_limpio.append(p)
    return " ".join(nombre_limpio[:3]) if nombre_limpio else nombre[:30]


def obtener_clave_modelo(producto: dict) -> str:
    """Genera una clave única para agrupar productos del mismo modelo."""
    marca = producto.get("marca", "")
    sub = producto.get("subcategoria", "")
    # Para productos con subcategoría, usar marca+subcategoría
    if sub:
        return f"{marca}_{sub}".lower().replace(" ", "_")
    # Fallback: usar las primeras palabras del nombre
    return extraer_nombre_busqueda(producto).lower().replace(" ", "_")


# ─── Scraping ─────────────────────────────────────────────────────

def buscar_en_sitio(session: requests.Session, query: str) -> dict | None:
    """
    Busca un query (código o nombre) en casajapon.com.
    Retorna info del primer producto encontrado o None.
    """
    try:
        resp = session.get(SEARCH_URL, params={"q": query}, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.error(f"  Error HTTP buscando '{query}': {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    items = soup.select("div.item")
    if not items:
        return None

    resultado = {"imagenes": [], "url_producto": None, "id_interno": None}

    for item in items:
        # Imágenes
        for img in item.select("img[data-original*='/produtos/'], img[src*='/produtos/']"):
            src = img.get("data-original") or img.get("src", "")
            if src and "/produtos/" in src and src not in resultado["imagenes"]:
                resultado["imagenes"].append(src)

        # Link al producto
        link = item.select_one("a[href*='/produto/']")
        if link and not resultado["url_producto"]:
            resultado["url_producto"] = urljoin(BASE_URL, link["href"])

    # Fallback: buscar imágenes en toda la página
    if not resultado["imagenes"]:
        for img in soup.select("img[src*='/produtos/'], img[data-original*='/produtos/']"):
            src = img.get("data-original") or img.get("src", "")
            if src and "/produtos/" in src and src not in resultado["imagenes"]:
                resultado["imagenes"].append(src)

    # Extraer ID interno
    for img_url in resultado["imagenes"]:
        parts = img_url.split("/img/")
        if len(parts) > 1:
            id_str = parts[1].split("/")[0]
            if id_str.isdigit():
                resultado["id_interno"] = id_str
                break

    return resultado if resultado["imagenes"] or resultado["url_producto"] else None


def obtener_imagenes_detalle(session: requests.Session, url: str) -> list[str]:
    """Extrae imágenes de alta resolución de la página de detalle."""
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.error(f"  Error obteniendo detalle: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    imagenes = []
    sz = CONFIG["preferred_size"]

    for img in soup.select("img[src*='/produtos/'], img[data-original*='/produtos/']"):
        src = img.get("data-original") or img.get("src", "")
        if src and "/produtos/" in src:
            src_hi = src.replace("/400/", f"/{sz}/").replace("/300/", f"/{sz}/")
            if src_hi not in imagenes:
                imagenes.append(src_hi)

    for a in soup.select("a[href$='.jpg'], a[href$='.png'], a[href$='.jpeg']"):
        href = a.get("href", "")
        if "/produtos/" in href and href not in imagenes:
            imagenes.append(href)

    return imagenes


def descargar_imagen(session: requests.Session, url: str, filepath: Path) -> bool:
    """Descarga una imagen a disco."""
    try:
        resp = session.get(url, timeout=30, stream=True)
        resp.raise_for_status()
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return True
    except requests.RequestException as e:
        log.error(f"  Error descargando: {e}")
        return False


def buscar_y_descargar(session: requests.Session, codigo: str, queries: list[str],
                       log_data: dict, max_imagenes: int = 5) -> bool:
    """
    Intenta buscar el producto con múltiples queries (código, nombre, etc.)
    y descarga las imágenes encontradas. Limita a max_imagenes por producto.
    """
    resultado = None

    for query in queries:
        log.info(f"  🔍 Buscando: '{query}'")
        resultado = buscar_en_sitio(session, query)
        if resultado:
            log.info(f"  ✅ Encontrado con: '{query}'")
            break
        time.sleep(CONFIG["request_delay"] * 0.5)

    if not resultado:
        log.warning(f"  ❌ No encontrado con ningún query")
        if codigo not in log_data["no_encontrados"]:
            log_data["no_encontrados"].append(codigo)
        return False

    # Obtener imágenes de detalle si hay URL de producto
    imagenes = []
    if resultado.get("url_producto"):
        log.info(f"  📸 Obteniendo imágenes de detalle...")
        time.sleep(CONFIG["request_delay"] * 0.5)
        imagenes = obtener_imagenes_detalle(session, resultado["url_producto"])

    if not imagenes:
        imagenes = resultado.get("imagenes", [])

    if not imagenes:
        log.warning(f"  ⚠️ Sin imágenes disponibles")
        return False

    # Limitar cantidad de imágenes
    imagenes = imagenes[:max_imagenes]

    # Descargar
    descargadas = []
    for i, img_url in enumerate(imagenes):
        if not img_url.startswith("http"):
            img_url = urljoin(BASE_URL, img_url)

        ext = Path(img_url.split("?")[0]).suffix or ".jpg"
        filename = f"{codigo}{ext}" if len(imagenes) == 1 else f"{codigo}_{i+1}{ext}"
        filepath = IMAGENES_DIR / filename

        if filepath.exists():
            log.info(f"  ✅ Ya existe: {filename}")
            descargadas.append(filename)
            continue

        if descargar_imagen(session, img_url, filepath):
            log.info(f"  ✅ Descargada: {filename}")
            descargadas.append(filename)

    if descargadas:
        log_data["descargados"][codigo] = {
            "archivos": descargadas,
            "id_interno": resultado.get("id_interno"),
            "url_producto": resultado.get("url_producto"),
        }
        return True

    return False


# ─── Main ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scraper de imágenes de casajapon.com")
    parser.add_argument("--test", type=int, help="Procesar solo los primeros N productos")
    parser.add_argument("--codigos", nargs="+", help="Procesar solo estos códigos")
    parser.add_argument("--resume", action="store_true", help="Retomar (salta ya procesados)")
    parser.add_argument("--delay", type=float, default=CONFIG["request_delay"],
                        help="Segundos entre requests (default: 1.0)")
    parser.add_argument("--size", choices=["300", "400", "800"], default=CONFIG["preferred_size"],
                        help="Tamaño de imagen (default: 800)")
    parser.add_argument("--max-img", type=int, default=5,
                        help="Máximo de imágenes por producto (default: 5)")
    parser.add_argument("--solo-modelos", action="store_true",
                        help="Solo una imagen por modelo/subcategoría (más rápido)")
    args = parser.parse_args()

    CONFIG["request_delay"] = args.delay
    CONFIG["preferred_size"] = args.size

    IMAGENES_DIR.mkdir(parents=True, exist_ok=True)

    productos = cargar_catalogo()
    log_data = cargar_log()
    # Asegurar que las claves nuevas existan en logs viejos
    log_data.setdefault("modelos_procesados", {})

    log.info(f"📦 Catálogo: {len(productos)} productos")
    log.info(f"📁 Destino: {IMAGENES_DIR}")
    log.info(f"⏱️  Delay: {CONFIG['request_delay']}s | Tamaño: {CONFIG['preferred_size']}px | Max img: {args.max_img}")

    # Filtrar
    if args.codigos:
        codigos_set = set(args.codigos)
        productos = [p for p in productos if p["codigo"] in codigos_set]
        log.info(f"🔍 {len(productos)} productos por código")

    if args.test:
        productos = productos[:args.test]
        log.info(f"🧪 Modo test: {len(productos)} productos")

    session = requests.Session()
    session.headers.update(HEADERS)

    total = len(productos)
    exitosos = 0
    no_encontrados = 0
    errores = 0
    saltados = 0
    modelos_ya_buscados = set(log_data["modelos_procesados"].keys())

    try:
        for i, prod in enumerate(productos, 1):
            codigo = prod["codigo"]

            # Skip already processed
            if args.resume and codigo in log_data["descargados"]:
                saltados += 1
                continue

            clave_modelo = obtener_clave_modelo(prod)

            # Modo solo-modelos: saltar si ya procesamos este modelo
            if args.solo_modelos and clave_modelo in modelos_ya_buscados:
                # Copiar la referencia del modelo ya existente
                modelo_info = log_data["modelos_procesados"].get(clave_modelo, {})
                if modelo_info.get("archivos"):
                    log_data["descargados"][codigo] = {
                        "archivos": modelo_info["archivos"],
                        "modelo_ref": clave_modelo,
                    }
                    exitosos += 1
                saltados += 1
                continue

            log.info(f"─── [{i}/{total}] {prod.get('nombre_es', codigo)} ───")

            try:
                # Queries a intentar (orden de prioridad)
                queries = [codigo]  # 1. Código exacto

                # 2. Nombre para búsqueda (modelo)
                nombre_busqueda = extraer_nombre_busqueda(prod)
                if nombre_busqueda and nombre_busqueda != codigo:
                    queries.append(nombre_busqueda)

                exito = buscar_y_descargar(session, codigo, queries, log_data, args.max_img)

                if exito:
                    exitosos += 1
                    # Registrar modelo como ya buscado
                    info = log_data["descargados"].get(codigo, {})
                    log_data["modelos_procesados"][clave_modelo] = {
                        "archivos": info.get("archivos", []),
                        "url_producto": info.get("url_producto"),
                        "codigo_ref": codigo,
                    }
                    modelos_ya_buscados.add(clave_modelo)
                else:
                    no_encontrados += 1

            except Exception as e:
                log.error(f"  ❌ Error inesperado: {e}")
                errores += 1
                log_data["errores"].append({"codigo": codigo, "error": str(e)})

            if i % 10 == 0:
                guardar_log(log_data)
                log.info(f"  💾 Progreso guardado ({i}/{total})")

            if i < total:
                time.sleep(CONFIG["request_delay"])

    except KeyboardInterrupt:
        log.info("\n⚠️ Interrumpido")
    finally:
        guardar_log(log_data)

    log.info("═" * 50)
    log.info("📊 RESUMEN")
    log.info("═" * 50)
    log.info(f"  Total:             {total}")
    log.info(f"  ✅ Con imagen:     {exitosos}")
    log.info(f"  ❌ No encontrados: {no_encontrados}")
    log.info(f"  ⚠️  Errores:       {errores}")
    if saltados:
        log.info(f"  ⏭️  Saltados:      {saltados}")
    log.info(f"  📁 Imágenes:       {IMAGENES_DIR}")
    log.info(f"  📋 Log:            {LOG_PATH}")


if __name__ == "__main__":
    main()
