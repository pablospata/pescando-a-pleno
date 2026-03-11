# Contexto del Proyecto: Catálogo Pescando a Pleno

## Qué es esto
Estamos armando un catálogo de productos de pesca para revender. El proveedor es **Casa Japón** (casajapon.com, Paraguay).

## Qué ya está hecho

### 1. Catálogo organizado (`catalogo-organizado.json`)
- 3077 productos del proveedor, organizados con: código, nombre en español, categoría, subcategoría, marca, precio USD, specs (tamaño, peso, acción, etc.)
- Categorías: Señuelos, Cañas, Reels Baitcast, Reels Frontales, Combos, Líneas, Anzuelos, Accesorios, Motores, Indumentaria, Terminal, Giradores, Triples, Cables de Acero

### 2. Imágenes descargadas (`imagenes-catalogo/`)
- 8403 archivos de imagen scrapeados de casajapon.com
- 2729 productos con imagen (89% del catálogo)
- 213 productos no encontrados en la web (productos Daiwa nuevos, etc.)
- Nombradas por código: `17010014_1.jpg`, `17010014_2.jpg`, etc.
- Script: `scraper_imagenes.py` (se puede re-correr con `--resume`)

### 3. Selección curada para catálogo impreso
- **`seleccion-catalogo-v2.txt`** — 105 productos, enfoque en rotación/volumen y precios accesibles
- **`seleccion-catalogo-v1.txt`** — 97 productos, versión con más foco en premium
- No hay señuelos rana/frog en el catálogo del proveedor

## Qué falta hacer (PRÓXIMO PASO)

### Armar el catálogo PDF imprimible
Usar la selección V2 (105 productos) + las imágenes descargadas para generar un PDF con:
- **Portada** con branding "Pescando a Pleno"
- **Índice** por categoría
- **Señuelos**: layout grilla (3-4 por página), son muchos y visuales
- **Cañas y Reels**: 1-2 por página, más detalle
- **Resto**: agrupado por categoría
- Cada producto muestra: imagen, nombre, marca, specs, rango de precio, "XX variantes disponibles"
- **No mostrar precio individual fijo** — mostrar "desde USD X" o rango
- **Última página**: contacto
- El listado completo de precios se pasa por Excel aparte para el pedido

### Consideraciones
- El catálogo debe ser IMPRIMIBLE y verse bien visualmente
- Enfoque comercial: lo barato y de alta rotación tiene más protagonismo
- Lo premium se mantiene como vidriera pero con menos espacio
- Distribución aprox: 35% hasta USD 5, 30% USD 5-20, 25% USD 20-100, 10% > USD 100
