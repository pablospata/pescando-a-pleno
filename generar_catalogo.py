#!/usr/bin/env python3
"""
Genera catalogo-nuevo3.html con el diseño de catalogo-marzo.html
usando datos de copy-catalogo-v3.txt e imágenes de imagenes-catalogo/
"""
import re
import os
import glob

BASE = r"c:\Users\Juan\Documents\pescando-a-pleno"
COPY_FILE = os.path.join(BASE, "analisis-catalogo-proveedor", "copy-catalogo-v3.txt")
IMG_DIR = os.path.join(BASE, "analisis-catalogo-proveedor", "imagenes-catalogo")
OUTPUT = os.path.join(BASE, "catalogo-nuevo3.html")
LOGO = "logo-letras-claras-sin-fondo-cuadrado-pescando-a-pleno.png"

# ─── Find image for a product code ───
def find_image(code):
    """Find the _1 image for a given product code, return relative path or None."""
    for ext in ['jpg', 'jpeg', 'png', 'webp']:
        path = os.path.join(IMG_DIR, f"{code}_1.{ext}")
        if os.path.exists(path):
            return f"analisis-catalogo-proveedor/imagenes-catalogo/{code}_1.{ext}"
    return None

# ─── Parse copy-catalogo-v3.txt ───
def parse_copy():
    with open(COPY_FILE, encoding='utf-8') as f:
        text = f.read()
    
    # Extract the intro text (between the header and first category)
    intro_match = re.search(r'ESTIMADO COMERCIANTE:\s*\n(.*?)(?=\n\n)', text, re.DOTALL)
    intro_text = intro_match.group(1).strip() if intro_match else ""
    
    # Extract señuelos section - use flexible pattern
    # Find from "EL ARTE" to next major section or end
    senueulos_match = re.search(
        r'(EL ARTE DEL ENGA.O.*?)(?=\nEL ALMA DEL EQUIPO|\nCA.AS DE PESCA|\nTODA LA POTENCIA|$)', 
        text, re.DOTALL
    )
    if not senueulos_match:
        print("ERROR: No se encontró la sección de señuelos")
        # Debug: print first 500 chars after line 10
        lines = text.split('\n')
        for i, l in enumerate(lines[10:25], 10):
            print(f"  L{i}: {l[:80]}")
        return None, None, []
    
    senueulos_text = senueulos_match.group(1)
    print(f"Sección señuelos: {len(senueulos_text)} chars")
    
    # Get the category intro - text between the header line and first ■
    cat_intro_match = re.search(
        r'EL ARTE DEL ENGA.O.*?\n[─\-=]+\n(.*?)(?=\n\n)', 
        senueulos_text, re.DOTALL
    )
    cat_intro = cat_intro_match.group(1).strip() if cat_intro_match else ""
    
    # Parse product families (■ blocks)
    families = []
    family_blocks = re.split(r'\n■ ', senueulos_text)
    
    for block in family_blocks[1:]:  # skip first (before first ■)
        lines = block.strip().split('\n')
        family_name = lines[0].strip()
        
        # Get family description (line after family name, before first numbered product)
        desc_lines = []
        products = []
        i = 1
        
        # Collect description text until we hit a numbered product line
        while i < len(lines):
            line = lines[i].strip()
            # Check if this is a numbered product line like "1. Animal 100 (Cod: 17010014)"
            if re.match(r'^\d+\.\s+', line):
                break
            if line and not line.startswith('─'):
                desc_lines.append(line)
            i += 1
        
        family_desc = ' '.join(desc_lines).strip()
        
        # Now parse products
        while i < len(lines):
            line = lines[i].strip()
            prod_match = re.match(r'^(\d+)\.\s+(.*?)\s*\(Cod:\s*(\d+)\)', line)
            if prod_match:
                num = prod_match.group(1)
                name = prod_match.group(2)
                code = prod_match.group(3)
                
                # Get specs line (starts with >)
                specs = ""
                price = ""
                brand = ""
                
                for j in range(i+1, min(i+5, len(lines))):
                    sline = lines[j].strip()
                    if sline.startswith('>'):
                        specs = sline[1:].strip()
                        # Extract brand
                        brand_match = re.match(r'^(.*?)\s*\|', specs)
                        if brand_match:
                            brand = brand_match.group(1).strip()
                            specs = specs[specs.index('|')+1:].strip()
                    if 'PRECIO MAYORISTA' in sline:
                        price_match = re.search(r'PRECIO MAYORISTA:\s*\$?([\d.,]+)', sline)
                        if price_match:
                            price = price_match.group(1)
                
                img_path = find_image(code)
                
                products.append({
                    'num': num,
                    'name': name,
                    'code': code,
                    'brand': brand,
                    'specs': specs,
                    'price': price,
                    'image': img_path,
                })
            i += 1
        
        if products:
            families.append({
                'name': family_name,
                'description': family_desc,
                'products': products,
            })
    
    return intro_text, cat_intro, families


# ─── Generate HTML ───
def generate_html():
    intro_text, cat_intro, families = parse_copy()
    
    if not families:
        print("ERROR: No se encontraron familias de productos")
        return
    
    print(f"Encontradas {len(families)} familias de señuelos")
    total_products = sum(len(f['products']) for f in families)
    print(f"Total productos señuelos: {total_products}")
    
    # Count images found
    imgs_found = sum(1 for f in families for p in f['products'] if p['image'])
    print(f"Imágenes encontradas: {imgs_found}/{total_products}")
    
    # ─── Build pages ───
    # 3 products per page
    pages_html = []
    page_num = 2  # portada is page 1
    
    # ── PAGE 2: ÍNDICE ──
    pages_html.append(f'''
    <!-- ═══════════════════════════════════════════════ -->
    <!-- PÁGINA {page_num} — ÍNDICE                     -->
    <!-- ═══════════════════════════════════════════════ -->
    <div class="pagina">
        <div class="wood-strip"></div>
        <div class="pagina-header">
            <img src="{LOGO}" alt="Logo" class="logo-mini">
            <span class="categoria-titulo">ÍNDICE</span>
        </div>

        <div class="indice-content">
            <div class="indice-intro">
                <h2>Catálogo Mayorista 2026</h2>
                <p>{intro_text}</p>
            </div>

            <div class="indice-categorias">
                <div class="indice-item">
                    <span class="indice-num">01</span>
                    <span class="indice-nombre">Señuelos Artificiales</span>
                    <span class="indice-desc">{len(families)} familias · {total_products} productos</span>
                </div>
                <div class="indice-item">
                    <span class="indice-num">02</span>
                    <span class="indice-nombre">Cañas</span>
                    <span class="indice-desc">Próximamente</span>
                </div>
                <div class="indice-item">
                    <span class="indice-num">03</span>
                    <span class="indice-nombre">Reels Baitcast</span>
                    <span class="indice-desc">Próximamente</span>
                </div>
                <div class="indice-item">
                    <span class="indice-num">04</span>
                    <span class="indice-nombre">Reels Frontales</span>
                    <span class="indice-desc">Próximamente</span>
                </div>
                <div class="indice-item">
                    <span class="indice-num">05</span>
                    <span class="indice-nombre">Líneas y Líders</span>
                    <span class="indice-desc">Próximamente</span>
                </div>
                <div class="indice-item">
                    <span class="indice-num">06</span>
                    <span class="indice-nombre">Anzuelos y Terminal</span>
                    <span class="indice-desc">Próximamente</span>
                </div>
                <div class="indice-item">
                    <span class="indice-num">07</span>
                    <span class="indice-nombre">Accesorios</span>
                    <span class="indice-desc">Próximamente</span>
                </div>
            </div>
        </div>

        <div class="wood-strip-bottom"></div>
        <div class="pagina-footer">
            <span class="contacto">+54 9 11 2249-0329 · Juan Pablo Freccero · Pescando a Pleno</span>
            <span class="pagina-num">{page_num:02d}</span>
        </div>
    </div>''')
    page_num += 1
    
    # ── SEÑUELOS CATEGORY INTRO PAGE ──
    pages_html.append(f'''
    <!-- ═══════════════════════════════════════════════ -->
    <!-- PÁGINA {page_num} — SEÑUELOS INTRO              -->
    <!-- ═══════════════════════════════════════════════ -->
    <div class="pagina-estrella">
        <div class="estrella-hero">
            <img src="fishing-lifestyle.png" alt="Pesca con señuelos">
            <div class="hero-overlay">
                <span class="hero-badge">★ Sección 01</span>
                <h2 class="hero-title">SEÑUELOS ARTIFICIALES</h2>
                <p class="hero-sub">El Arte del Engaño · Alta Performance</p>
            </div>
        </div>

        <div class="estrella-content">
            <div class="estrella-descripcion">
                <h3>El Arte del Engaño</h3>
                <div class="texto">
                    <p>{cat_intro}</p>
                </div>
            </div>

            <div class="estrella-specs-grid">
                <div class="estrella-spec-item">
                    <span class="spec-valor">{total_products}</span>
                    <span class="spec-nombre">Productos</span>
                </div>
                <div class="estrella-spec-item">
                    <span class="spec-valor">{len(families)}</span>
                    <span class="spec-nombre">Familias</span>
                </div>
                <div class="estrella-spec-item">
                    <span class="spec-valor">4</span>
                    <span class="spec-nombre">Marcas</span>
                </div>
                <div class="estrella-spec-item">
                    <span class="spec-valor">$4.1k</span>
                    <span class="spec-nombre">Desde</span>
                </div>
            </div>

            <div class="estrella-precio-row">
                <div class="estrella-precio-left">
                    <span class="precio-big">PRECIOS MAYORISTAS</span>
                </div>
                <span class="consultar">¡Consultá por volumen!</span>
            </div>
        </div>

        <div class="pagina-footer">
            <span class="contacto">+54 9 11 2249-0329 · Juan Pablo Freccero · Pescando a Pleno</span>
            <span class="pagina-num">{page_num:02d}</span>
        </div>
    </div>''')
    page_num += 1
    
    # ── PRODUCT PAGES: 3 products per page ──
    # Group all products from all families into a flat list, but keep family info
    all_items = []
    for family in families:
        for pi, prod in enumerate(family['products']):
            all_items.append({
                **prod,
                'family_name': family['name'],
                'family_desc': family['description'] if pi == 0 else None,  # only show desc on first product of family
                'is_first_in_family': pi == 0,
            })
    
    # Chunk into pages of 3
    for chunk_start in range(0, len(all_items), 3):
        chunk = all_items[chunk_start:chunk_start+3]
        
        # Determine the subcategory title for this page header
        brands_on_page = set()
        families_on_page = set()
        for item in chunk:
            if item['brand']:
                brands_on_page.add(item['brand'])
            families_on_page.add(item['family_name'])
        
        header_title = "SEÑUELOS · " + " · ".join(sorted(families_on_page))
        if len(header_title) > 50:
            header_title = "SEÑUELOS ARTIFICIALES"
        
        # Build product cards
        products_html = ""
        for item in chunk:
            # Family description banner (if first product of a new family)
            family_banner = ""
            if item['is_first_in_family'] and item['family_desc']:
                short_desc = item['family_desc'][:150] + ('...' if len(item['family_desc']) > 150 else '')
                family_banner = f'''
                <!-- Family intro -->
                <div class="familia-banner">
                    <strong>{item['family_name']}</strong>
                    <span>{short_desc}</span>
                </div>'''
            
            # Image
            if item['image']:
                img_tag = f'<img src="{item["image"]}" alt="{item["name"]}">'
            else:
                img_tag = f'<div class="no-image">Sin imagen</div>'
            
            # Specs badges
            specs_parts = [s.strip() for s in item['specs'].split(',') if s.strip()]
            specs_html = ''.join(f'<span class="spec">{s}</span>' for s in specs_parts[:5])
            
            # Price formatting
            price_display = f"${item['price']}" if item['price'] else "Consultar"
            
            products_html += f'''
            {family_banner}
            <!-- Producto {item['num']} — {item['name']} -->
            <div class="producto">
                <div class="diagonal-accent"></div>
                <div class="producto-foto">
                    <span class="id-tag">#{item['num']}</span>
                    {img_tag}
                </div>
                <div class="producto-detalle">
                    <span class="codigo">CÓD. {item['code']}</span>
                    <h3>{item['name']}</h3>
                    <p class="descripcion marca-label">{item['brand']}</p>
                    <div class="specs">
                        {specs_html}
                    </div>
                    <div class="precio-zona">
                        <span class="precio">{price_display}</span>
                        <span class="precio-label">Precio mayorista</span>
                    </div>
                </div>
            </div>'''
        
        pages_html.append(f'''
    <!-- ═══════════════════════════════════════════════ -->
    <!-- PÁGINA {page_num}                               -->
    <!-- ═══════════════════════════════════════════════ -->
    <div class="pagina">
        <div class="wood-strip"></div>
        <div class="pagina-header">
            <img src="{LOGO}" alt="Logo" class="logo-mini">
            <span class="categoria-titulo">{header_title}</span>
        </div>

        <div class="productos-area">
            {products_html}
        </div>

        <div class="wood-strip-bottom"></div>
        <div class="pagina-footer">
            <span class="contacto">+54 9 11 2249-0329 · Juan Pablo Freccero · Pescando a Pleno</span>
            <span class="pagina-num">{page_num:02d}</span>
        </div>
    </div>''')
        page_num += 1
    
    # ─── FULL HTML ───
    html = f'''<!DOCTYPE html>
<html lang="es">

<head>
    <meta charset="UTF-8">
    <title>Catálogo Mayorista — Pescando a Pleno</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700;800;900&family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Oswald:wght@300;400;600;700;800;900&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Anton&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;700&display=swap" rel="stylesheet">

    <style>
        /* ══════════════════════════════════════════════ */
        /* RESET & BASE                                  */
        /* ══════════════════════════════════════════════ */
        *,
        *::before,
        *::after {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        :root {{
            --azul: #1A3A5C;
            --azul-claro: #2a5a8c;
            --teal: #6BADA0;
            --arena: #CBB68E;
            --arena-claro: #e8dcc8;
            --negro: #1C1C1C;
            --crema: #F5F0EB;
            --blanco: #FFFFFF;
            --madera: #d4c4a8;
            --madera-oscuro: #8b7355;
        }}

        body {{
            font-family: 'Roboto', sans-serif;
            color: var(--negro);
            background: #000;
        }}

        /* ══════════════════════════════════════════════ */
        /* PRINT / PAGE SETUP                            */
        /* ══════════════════════════════════════════════ */
        @page {{
            size: A4;
            margin: 0;
        }}

        /* ══════════════════════════════════════════════ */
        /* CARÁTULA                                      */
        /* ══════════════════════════════════════════════ */
        .portada {{
            width: 210mm;
            height: 297mm;
            position: relative;
            overflow: hidden;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #c4b6a2;
            text-align: center;
            background-image: url('bg-pesca2.jpg');
            background-size: cover;
            background-position: right;
            page-break-after: always;
        }}

        .background-overlay {{
            position: absolute;
            top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(to bottom, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0.70) 100%);
            z-index: 1;
        }}

        .contenido {{
            position: relative;
            z-index: 2;
            width: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}

        .logo-container {{ margin-bottom: 25px; }}

        .logo {{
            width: 450px;
            filter: drop-shadow(0px 4px 10px rgba(0,0,0,0.5));
        }}

        .textos {{
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        .separador {{
            width: 60px; height: 3px;
            background-color: var(--arena);
            margin: 0 auto 20px;
        }}

        .titulo-catalogo {{
            font-family: 'Bebas Neue', sans-serif;
            font-size: 5rem; font-weight: 400;
            letter-spacing: 2px;
            text-shadow: 1px 1px 6px rgba(0,0,0,0.6);
        }}

        .subtitulo-catalogo {{
            font-family: 'Bebas Neue', sans-serif;
            font-size: 4.5rem; font-weight: 400;
            letter-spacing: 2px;
            margin-bottom: 60px;
            text-shadow: 1px 1px 6px rgba(0,0,0,0.6);
        }}

        .slogan {{
            font-family: 'Bebas Neue', sans-serif;
            font-size: 2rem; font-weight: 700;
            letter-spacing: 4px;
            border-top: 1px solid rgba(255,255,255,0.3);
            border-bottom: 1px solid rgba(255,255,255,0.3);
            padding: 15px 0;
            display: inline-block;
            text-shadow: 1px 1px 4px rgba(0,0,0,0.5);
            line-height: 1.8;
        }}

        /* ══════════════════════════════════════════════ */
        /* PÁGINAS DE PRODUCTO                            */
        /* ══════════════════════════════════════════════ */
        .pagina {{
            width: 210mm; height: 297mm;
            position: relative; overflow: hidden;
            background: var(--crema);
            page-break-after: always;
            display: flex; flex-direction: column;
        }}

        .pagina:last-child {{ page-break-after: auto; }}

        /* ── Wood strip top ── */
        .wood-strip {{
            width: 100%; height: 18px;
            background: url('wood-texture.png') center/cover;
            flex-shrink: 0;
            position: relative;
        }}
        .wood-strip::after {{
            content: '';
            position: absolute; bottom: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, var(--arena), transparent);
        }}

        /* ── Page header ── */
        .pagina-header {{
            background: var(--azul);
            padding: 12px 35px;
            display: flex; align-items: center; justify-content: space-between;
            flex-shrink: 0;
            position: relative;
        }}
        .pagina-header::after {{
            content: '';
            position: absolute; bottom: -8px; left: 0; right: 0;
            height: 8px;
            background: linear-gradient(to bottom, rgba(26,58,92,0.15), transparent);
        }}
        .pagina-header .logo-mini {{
            height: 32px;
            filter: brightness(10);
        }}
        .pagina-header .categoria-titulo {{
            font-family: 'Bebas Neue', sans-serif;
            font-size: 1.4rem; letter-spacing: 4px;
            color: var(--arena);
        }}

        /* ── Product grid area (3 per page) ── */
        .productos-area {{
            flex: 1;
            display: flex; flex-direction: column;
            gap: 10px;
            padding: 10px 28px 14px;
        }}

        /* ── Family banner ── */
        .familia-banner {{
            background: linear-gradient(135deg, rgba(26,58,92,0.06) 0%, rgba(107,173,160,0.06) 100%);
            border-left: 3px solid var(--teal);
            padding: 6px 14px;
            border-radius: 0 6px 6px 0;
            margin-bottom: -4px;
        }}
        .familia-banner strong {{
            font-family: 'Montserrat', sans-serif;
            font-size: 0.7rem; font-weight: 800;
            color: var(--azul);
            text-transform: uppercase;
            letter-spacing: 1px;
            display: block;
        }}
        .familia-banner span {{
            font-family: 'Roboto', sans-serif;
            font-size: 0.6rem; font-weight: 300;
            color: #666;
            line-height: 1.4;
            display: block;
            margin-top: 2px;
        }}

        /* ── Product card — magazine style ── */
        .producto {{
            flex: 1;
            display: flex;
            background: var(--blanco);
            border-radius: 6px;
            overflow: hidden;
            position: relative;
            box-shadow: 0 2px 15px rgba(0,0,0,0.06);
        }}
        .producto::before {{
            content: '';
            position: absolute; top: 0; left: 0;
            width: 5px; height: 100%;
            background: linear-gradient(to bottom, var(--teal), var(--azul));
            border-radius: 6px 0 0 6px;
        }}

        /* Image zone */
        .producto-foto {{
            width: 195px; min-width: 195px;
            display: flex; align-items: center; justify-content: center;
            padding: 12px;
            position: relative;
            background: linear-gradient(135deg, #fafafa 0%, #f0ede8 100%);
        }}
        .producto-foto img {{
            max-width: 100%; max-height: 100%;
            object-fit: contain;
            filter: drop-shadow(2px 4px 6px rgba(0,0,0,0.1));
        }}
        .producto-foto .id-tag {{
            position: absolute; top: 8px; right: 8px;
            background: var(--azul); color: white;
            font-family: 'Montserrat', sans-serif;
            font-weight: 700; font-size: 0.55rem;
            padding: 2px 7px; border-radius: 3px;
            letter-spacing: 1px; opacity: 0.85;
        }}
        .producto-foto .no-image {{
            font-family: 'Caveat', cursive;
            font-size: 0.85rem; color: #ccc;
        }}

        /* Info zone */
        .producto-detalle {{
            flex: 1;
            padding: 14px 18px 14px 16px;
            display: flex; flex-direction: column; justify-content: center;
            position: relative;
        }}
        .producto-detalle .codigo {{
            font-family: 'Roboto', sans-serif;
            font-size: 0.6rem; font-weight: 500;
            color: #aaa; letter-spacing: 1.5px;
            text-transform: uppercase; margin-bottom: 2px;
        }}
        .producto-detalle h3 {{
            font-family: 'Montserrat', sans-serif;
            font-weight: 800; font-size: 0.95rem;
            color: var(--azul); text-transform: uppercase;
            line-height: 1.25; margin-bottom: 4px;
        }}
        .producto-detalle .descripcion {{
            font-family: 'Roboto', sans-serif;
            font-weight: 300; font-size: 0.72rem;
            line-height: 1.5; color: #555; margin-bottom: 6px;
        }}
        .producto-detalle .marca-label {{
            color: var(--teal); font-weight: 500;
            font-size: 0.65rem;
        }}
        .producto-detalle .specs {{
            display: flex; gap: 6px; flex-wrap: wrap;
            margin-bottom: 8px;
        }}
        .producto-detalle .spec {{
            font-family: 'Roboto', sans-serif;
            font-size: 0.58rem; font-weight: 500;
            color: var(--azul);
            background: rgba(26,58,92,0.07);
            border: 1px solid rgba(26,58,92,0.12);
            padding: 2px 8px; border-radius: 3px;
            letter-spacing: 0.3px;
        }}
        .producto-detalle .precio-zona {{
            display: flex; align-items: center; gap: 10px;
        }}
        .producto-detalle .precio {{
            font-family: 'Montserrat', sans-serif;
            font-weight: 800; font-size: 1.2rem;
            color: var(--negro);
        }}
        .producto-detalle .precio-label {{
            font-family: 'Caveat', cursive;
            font-size: 0.8rem; color: var(--teal);
            font-weight: 700;
        }}

        /* ── Diagonal accent on card ── */
        .producto .diagonal-accent {{
            position: absolute; top: 0; right: 0;
            width: 0; height: 0;
            border-style: solid;
            border-width: 0 45px 45px 0;
            border-color: transparent var(--arena) transparent transparent;
            opacity: 0.2;
        }}

        /* ══════════════════════════════════════════════ */
        /* PÁGINA ESTRELLA                                */
        /* ══════════════════════════════════════════════ */
        .pagina-estrella {{
            width: 210mm; height: 297mm;
            position: relative; overflow: hidden;
            background: var(--crema);
            page-break-after: always;
            display: flex; flex-direction: column;
        }}

        .estrella-hero {{
            position: relative; height: 200px;
            overflow: hidden; flex-shrink: 0;
        }}
        .estrella-hero img {{
            width: 100%; height: 100%;
            object-fit: cover;
            filter: brightness(0.7) saturate(1.1);
        }}
        .estrella-hero .hero-overlay {{
            position: absolute; inset: 0;
            background: linear-gradient(to bottom, rgba(26,58,92,0.4) 0%, rgba(26,58,92,0.85) 100%);
            display: flex; flex-direction: column;
            justify-content: flex-end;
            padding: 25px 35px;
        }}
        .estrella-hero .hero-badge {{
            font-family: 'Caveat', cursive;
            font-size: 1.1rem; color: var(--arena);
            margin-bottom: 4px;
        }}
        .estrella-hero .hero-title {{
            font-family: 'Bebas Neue', sans-serif;
            font-size: 2.8rem; color: white;
            letter-spacing: 3px; line-height: 1;
        }}
        .estrella-hero .hero-sub {{
            font-family: 'Roboto', sans-serif;
            font-size: 0.85rem; font-weight: 300;
            color: rgba(255,255,255,0.8);
            margin-top: 6px; letter-spacing: 1px;
        }}

        .estrella-content {{
            flex: 1;
            display: flex; flex-direction: column;
            padding: 25px 35px;
        }}
        .estrella-descripcion {{
            flex: 1;
            display: flex; flex-direction: column;
            gap: 16px;
        }}
        .estrella-descripcion h3 {{
            font-family: 'Playfair Display', serif;
            font-size: 1.3rem; color: var(--azul);
        }}
        .estrella-descripcion .texto {{
            font-family: 'Roboto', sans-serif;
            font-weight: 300; font-size: 0.82rem;
            line-height: 1.7; color: #444;
            columns: 2; column-gap: 25px;
        }}

        .estrella-specs-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px; margin-top: 20px;
        }}
        .estrella-spec-item {{
            background: var(--blanco);
            border-radius: 6px; padding: 10px 12px;
            text-align: center;
            border: 1px solid rgba(26,58,92,0.08);
        }}
        .estrella-spec-item .spec-valor {{
            font-family: 'Montserrat', sans-serif;
            font-weight: 800; font-size: 1.1rem;
            color: var(--azul); display: block;
        }}
        .estrella-spec-item .spec-nombre {{
            font-family: 'Roboto', sans-serif;
            font-size: 0.6rem; color: #888;
            text-transform: uppercase; letter-spacing: 1px;
            margin-top: 2px;
        }}

        .estrella-precio-row {{
            display: flex; align-items: center; justify-content: space-between;
            background: var(--azul);
            border-radius: 8px; padding: 14px 22px;
            margin-top: auto;
        }}
        .estrella-precio-left {{
            display: flex; align-items: baseline; gap: 8px;
        }}
        .estrella-precio-row .precio-big {{
            font-family: 'Montserrat', sans-serif;
            font-weight: 900; font-size: 1.3rem;
            color: white; letter-spacing: 2px;
        }}
        .estrella-precio-row .consultar {{
            font-family: 'Caveat', cursive;
            font-size: 1.1rem; color: var(--arena);
        }}

        /* ══════════════════════════════════════════════ */
        /* ÍNDICE                                         */
        /* ══════════════════════════════════════════════ */
        .indice-content {{
            flex: 1;
            padding: 30px 35px;
            display: flex; flex-direction: column;
        }}
        .indice-intro {{
            margin-bottom: 30px;
        }}
        .indice-intro h2 {{
            font-family: 'Playfair Display', serif;
            font-size: 1.5rem; color: var(--azul);
            margin-bottom: 12px;
        }}
        .indice-intro p {{
            font-family: 'Roboto', sans-serif;
            font-size: 0.82rem; font-weight: 300;
            line-height: 1.7; color: #555;
        }}
        .indice-categorias {{
            display: flex; flex-direction: column;
            gap: 12px;
        }}
        .indice-item {{
            display: flex; align-items: center;
            gap: 16px;
            background: var(--blanco);
            padding: 14px 20px;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            border-left: 4px solid var(--teal);
        }}
        .indice-item .indice-num {{
            font-family: 'Bebas Neue', sans-serif;
            font-size: 1.8rem; color: var(--arena);
            min-width: 40px;
        }}
        .indice-item .indice-nombre {{
            font-family: 'Montserrat', sans-serif;
            font-weight: 700; font-size: 0.9rem;
            color: var(--azul); text-transform: uppercase;
            flex: 1;
        }}
        .indice-item .indice-desc {{
            font-family: 'Caveat', cursive;
            font-size: 0.9rem; color: var(--madera-oscuro);
        }}

        /* ══════════════════════════════════════════════ */
        /* FOOTER                                         */
        /* ══════════════════════════════════════════════ */
        .pagina-footer {{
            background: var(--azul);
            padding: 8px 35px;
            display: flex; align-items: center; justify-content: space-between;
            flex-shrink: 0;
        }}
        .pagina-footer .contacto {{
            font-family: 'Roboto', sans-serif;
            font-size: 0.65rem;
            color: rgba(255,255,255,0.6);
            letter-spacing: 0.5px;
        }}
        .pagina-footer .pagina-num {{
            font-family: 'Bebas Neue', sans-serif;
            font-size: 0.95rem; color: var(--arena);
            letter-spacing: 2px;
        }}

        .wood-strip-bottom {{
            width: 100%; height: 12px;
            background: url('wood-texture.png') center/cover;
            flex-shrink: 0;
        }}

        /* ══════════════════════════════════════════════ */
        /* PRINT                                          */
        /* ══════════════════════════════════════════════ */
        @media print {{
            body {{ background: white; }}
            .portada, .pagina, .pagina-estrella {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
                box-shadow: none; margin: 0;
            }}
        }}

        /* ══════════════════════════════════════════════ */
        /* SCREEN PREVIEW                                 */
        /* ══════════════════════════════════════════════ */
        @media screen {{
            body {{
                display: flex; flex-direction: column;
                align-items: center;
                gap: 12mm; padding: 12mm;
                background: #444;
            }}
            .portada, .pagina, .pagina-estrella {{
                box-shadow: 0 10px 50px rgba(0,0,0,0.5);
            }}
        }}
    </style>
</head>

<body>

    <!-- ═══════════════════════════════════════════════ -->
    <!-- CARÁTULA                                       -->
    <!-- ═══════════════════════════════════════════════ -->
    <div class="portada">
        <div class="background-overlay"></div>
        <div class="contenido">
            <div class="logo-container">
                <img src="{LOGO}" alt="Pescando a Pleno" class="logo">
            </div>
            <div class="textos">
                <div class="separador"></div>
                <h2 class="titulo-catalogo">CATÁLOGO DE PRODUCTOS</h2>
                <h3 class="subtitulo-catalogo">MARZO 2026</h3>
                <p class="slogan">JUAN PABLO FRECCERO<br>+54 9 11 2249-0329</p>
            </div>
        </div>
    </div>

    {"".join(pages_html)}

</body>

</html>'''
    
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\nOK! Generado: {OUTPUT}")
    print(f"   Total páginas: {page_num - 1}")


if __name__ == '__main__':
    generate_html()
