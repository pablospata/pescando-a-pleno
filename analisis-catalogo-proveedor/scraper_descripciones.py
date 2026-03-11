"""
Scraper de descripciones de productos desde casajapon.com

Lee las URLs de producto del scraper_log.json (ya obtenidas durante el scraping
de imágenes) y extrae la sección "Descrição Geral" de cada página de detalle.

Solo procesa los productos de la selección v2 del catálogo (105 productos).
Agrupa por URL única para evitar requests redundantes (~40-50 URLs únicas).

Uso:
    python scraper_descripciones.py              # Todas las descripciones
    python scraper_descripciones.py --test 5     # Solo las primeras 5 URLs
    python scraper_descripciones.py --resume     # Retoma desde donde dejó
"""

import json
import re
import time
import argparse
import logging
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ─── Configuración ────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
CATALOGO_PATH = BASE_DIR / "catalogo-organizado.json"
SCRAPER_LOG_PATH = BASE_DIR / "scraper_log.json"
SELECCION_PATH = BASE_DIR / "seleccion-catalogo-v2.txt"
OUTPUT_PATH = BASE_DIR / "descripciones-catalogo.json"

REQUEST_DELAY = 1.5  # segundos entre requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,pt-BR;q=0.8,pt;q=0.7,en;q=0.6",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("scraper_desc")


# ─── Identificar productos de la selección V2 ─────────────────────

def extraer_subcategorias_seleccion() -> list[str]:
    """
    Extrae los nombres de productos/subcategorías de seleccion-catalogo-v2.txt.
    Retorna una lista de strings como 'Animal 100', 'Bay Hunter 70', etc.
    """
    nombres = []
    with open(SELECCION_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Buscar líneas tipo "  1.  Animal 100 — walking bait..."
            # o "  29. Marine Sports SOLARA — ..."
            m = re.match(r'^\s*\d+\.\s+(.+?)\s*—', line)
            if m:
                nombre = m.group(1).strip()
                # Quitar marca si empieza con ella (para cañas/reels)
                for marca in ["Marine Sports ", "Daiwa ", "Duel ", "Megabass ", "OSP ", "Yo-Zuri "]:
                    if nombre.startswith(marca):
                        nombre = nombre[len(marca):]
                        break
                nombres.append(nombre.strip())
    return nombres


def mapear_productos_seleccion(productos: list[dict], nombres_seleccion: list[str]) -> list[dict]:
    """
    Mapea los nombres de la selección v2 a productos del catálogo organizado.
    Retorna una lista con un producto representativo por cada nombre de la selección.
    """
    # Construir índice por subcategoría
    por_sub = {}
    for p in productos:
        sub = p.get("subcategoria", "").upper()
        nombre_es = p.get("nombre_es", "").upper()
        if sub not in por_sub:
            por_sub[sub] = p
        # También indexar por nombre parcial
        for parte in nombre_es.split():
            if len(parte) > 3:
                key = parte.upper()
                if key not in por_sub:
                    por_sub[key] = p

    matched = []
    for nombre in nombres_seleccion:
        found = None
        nombre_upper = nombre.upper()

        # 1. Buscar por subcategoría exacta
        for p in productos:
            sub = (p.get("subcategoria") or "").upper()
            if sub and sub == nombre_upper:
                found = p
                break

        # 2. Buscar por subcategoría contenida
        if not found:
            for p in productos:
                sub = (p.get("subcategoria") or "").upper()
                nom = (p.get("nombre_es") or "").upper()
                if nombre_upper in sub or nombre_upper in nom:
                    found = p
                    break

        # 3. Buscar por keywords del nombre en nombre_es
        if not found:
            keywords = nombre_upper.split()
            for p in productos:
                nom = (p.get("nombre_es") or "").upper()
                if all(kw in nom for kw in keywords):
                    found = p
                    break

        if found:
            matched.append(found)

    return matched


# ─── Scraping de descripciones ─────────────────────────────────────

def extraer_descripcion(session: requests.Session, url: str) -> str | None:
    """
    Visita la página de detalle de un producto en casajapon.com
    y extrae el texto de la sección 'Descrição Geral'.
    """
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.error(f"  Error HTTP: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Estrategia 1: buscar div.description o sección de descripción
    # La descripción suele estar después del tab "Descrição Geral"
    desc_div = soup.select_one("div.description, div.product-description, "
                                "div#descricao, div.tab-content")

    if desc_div:
        text = desc_div.get_text(separator="\n", strip=True)
        if len(text) > 20:
            return limpiar_descripcion(text)

    # Estrategia 2: buscar todo el texto entre "Descrição Geral" y el próximo elemento
    full_text = soup.get_text(separator="\n")
    lines = full_text.split("\n")
    
    capturando = False
    desc_lines = []
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
            
        if "Descrição Geral" in line_clean or "Descrição geral" in line_clean:
            capturando = True
            continue
        
        if capturando:
            # Parar cuando lleguemos a secciones no-descripción
            if any(stop in line_clean for stop in [
                "Fazer login", "ORÇAMENTO", "COMPRAR", "Avise me",
                "login para gerar", "Central de Relacionamento",
                "Casa Japon", "Atendimento"
            ]):
                break
            if len(line_clean) > 5:
                desc_lines.append(line_clean)
    
    if desc_lines:
        return limpiar_descripcion("\n".join(desc_lines))
    
    # Estrategia 3: buscar meta description como fallback
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        content = meta["content"].strip()
        if len(content) > 20:
            return content
    
    return None


def limpiar_descripcion(text: str) -> str:
    """Limpia el texto de la descripción."""
    # Quitar líneas repetidas
    lines = text.split("\n")
    seen = set()
    clean = []
    for line in lines:
        line = line.strip()
        if line and line not in seen:
            seen.add(line)
            clean.append(line)
    
    text = "\n".join(clean)
    
    # Quitar patrones no deseados
    text = re.sub(r'Fazer login.*', '', text)
    text = re.sub(r'Avise me.*', '', text)
    text = re.sub(r'ORÇAMENTO.*', '', text)
    text = re.sub(r'COMPRAR.*', '', text)
    
    return text.strip()


# ─── Main ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scraper de descripciones de casajapon.com")
    parser.add_argument("--test", type=int, help="Procesar solo las primeras N URLs")
    parser.add_argument("--resume", action="store_true", help="Retomar (salta ya procesados)")
    parser.add_argument("--delay", type=float, default=REQUEST_DELAY,
                        help=f"Segundos entre requests (default: {REQUEST_DELAY})")
    args = parser.parse_args()

    # Cargar datos
    log.info("📦 Cargando catálogo y log del scraper...")
    
    with open(CATALOGO_PATH, "r", encoding="utf-8") as f:
        catalogo = json.load(f)
    productos = catalogo["productos"]
    
    with open(SCRAPER_LOG_PATH, "r", encoding="utf-8") as f:
        scraper_log = json.load(f)
    descargados = scraper_log.get("descargados", {})
    
    # Identificar subcategorías/nombres de la selección v2
    nombres_seleccion = extraer_subcategorias_seleccion()
    log.info(f"📋 Selección V2: {len(nombres_seleccion)} productos")
    
    # Mapear a productos del catálogo
    productos_seleccion = mapear_productos_seleccion(productos, nombres_seleccion)
    log.info(f"🔗 Mapeados: {len(productos_seleccion)} productos del catálogo")
    
    # Obtener URLs únicas de producto desde el scraper_log
    urls_por_modelo = {}  # url -> {subcategoria, codigos}
    codigos_seleccion = set(p["codigo"] for p in productos_seleccion)
    
    # También buscar todos los códigos de las mismas subcategorías
    subs_seleccion = set(p.get("subcategoria", "") for p in productos_seleccion if p.get("subcategoria"))
    for p in productos:
        sub = p.get("subcategoria", "")
        if sub in subs_seleccion:
            codigos_seleccion.add(p["codigo"])
    
    for codigo in codigos_seleccion:
        info = descargados.get(codigo)
        if info and info.get("url_producto"):
            url = info["url_producto"]
            if url not in urls_por_modelo:
                # Buscar la subcategoría de este producto
                prod = next((p for p in productos if p["codigo"] == codigo), None)
                sub = prod.get("subcategoria", codigo) if prod else codigo
                urls_por_modelo[url] = {
                    "subcategoria": sub,
                    "codigos": [],
                    "marca": prod.get("marca", "") if prod else "",
                }
            urls_por_modelo[url]["codigos"].append(codigo)
    
    log.info(f"🌐 URLs únicas de producto: {len(urls_por_modelo)}")
    
    # Cargar resultados previos si --resume
    resultados = {}
    if args.resume and OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            resultados = json.load(f)
        log.info(f"📂 Retomando: {len(resultados)} descripciones ya obtenidas")
    
    # Limitar si --test
    urls_list = list(urls_por_modelo.items())
    if args.test:
        urls_list = urls_list[:args.test]
        log.info(f"🧪 Modo test: {len(urls_list)} URLs")
    
    # Scraping
    session = requests.Session()
    session.headers.update(HEADERS)
    
    exitosos = 0
    sin_desc = 0
    errores = 0
    saltados = 0
    total = len(urls_list)
    
    try:
        for i, (url, info) in enumerate(urls_list, 1):
            sub = info["subcategoria"]
            
            # Skip si ya procesado
            if args.resume and sub in resultados:
                saltados += 1
                continue
            
            log.info(f"─── [{i}/{total}] {sub} ({info['marca']}) ───")
            log.info(f"  🌐 {url}")
            
            try:
                descripcion = extraer_descripcion(session, url)
                
                if descripcion:
                    resultados[sub] = {
                        "descripcion_pt": descripcion,
                        "url": url,
                        "marca": info["marca"],
                        "codigos_ejemplo": info["codigos"][:3],
                    }
                    exitosos += 1
                    log.info(f"  ✅ Descripción obtenida ({len(descripcion)} chars)")
                else:
                    sin_desc += 1
                    log.warning(f"  ⚠️ Sin descripción")
                    resultados[sub] = {
                        "descripcion_pt": "",
                        "url": url,
                        "marca": info["marca"],
                        "codigos_ejemplo": info["codigos"][:3],
                    }
            except Exception as e:
                errores += 1
                log.error(f"  ❌ Error: {e}")
            
            # Guardar progreso cada 10
            if i % 10 == 0:
                with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                    json.dump(resultados, f, indent=2, ensure_ascii=False)
                log.info(f"  💾 Progreso guardado ({i}/{total})")
            
            if i < total:
                time.sleep(args.delay)
    
    except KeyboardInterrupt:
        log.info("\n⚠️ Interrumpido")
    finally:
        # Guardar resultados finales
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False)
    
    log.info("═" * 50)
    log.info("📊 RESUMEN")
    log.info("═" * 50)
    log.info(f"  Total URLs:        {total}")
    log.info(f"  ✅ Con descripción: {exitosos}")
    log.info(f"  ⚠️  Sin descripción: {sin_desc}")
    log.info(f"  ❌ Errores:         {errores}")
    if saltados:
        log.info(f"  ⏭️  Saltados:       {saltados}")
    log.info(f"  📁 Salida:          {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
