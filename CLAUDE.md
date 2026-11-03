# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es esto

Tienda web estática de **Conservas Iberia** (empresa ficticia de conservas). No hay dependencias ni repo git: `build.py` usa solo la librería estándar de Python.

## Comandos

```bash
python3 build.py   # lee data/*.csv y regenera docs/index.html
```

No hay tests ni linter configurados. Para probar, abre `docs/index.html` en el navegador.

## Arquitectura

- `data/` es la **entrada**: `conservas_iberia_ventas_2026.csv` (columnas `mes,canal,producto,unidades,ingresos_eur,coste_eur`), `ficha_productos.md` (descripción y formato de cada producto, copia de la ficha de Google Drive) y los PDF de informes mensuales (solo referencia).
- `docs/` es la **salida generada**: `index.html` se sobrescribe en cada build. No lo edites a mano; cambia `build.py`.
- `build.py` hace todo: carga el CSV, calcula precios, y rellena una plantilla HTML (string `TEMPLATE` con CSS y JS inline) sustituyendo `__CARDS__` y `__PRODUCTS_JSON__`.

## Reglas de negocio importantes

- **Precio** = `ingresos_eur / unidades` del canal `Online (web propia)` en el último mes del CSV, con 2 decimales (`Decimal`, `ROUND_HALF_UP`).
- **Categorías** (`pescado`, `verduras`) están fijas en `CATEGORY_BY_PRODUCT`; un producto nuevo del CSV sin categoría hace fallar el build.
- La web **nunca debe mostrar ni incrustar** costes, márgenes, ingresos ni unidades: solo `id`, `name`, `category` y `price_cents` van al JSON.
- La web no carga nada externo (sin CDN ni fuentes) y el carrito vive solo en memoria (se vacía al recargar; `localStorage` solo se usa para recordar el modo claro/oscuro).
- La etiqueta «Más vendido» va en el producto con más unidades del canal Online en el último mes (se calcula en `build.py`).
- Precios en formato español (`6,49 €`); textos de la interfaz en español de España.
- Color corporativo: azul oscuro (`--brand` en el CSS de la plantilla).

## Convenciones

Código, identificadores y comentarios en inglés; documentación y conversación en español (ver `~/.claude/CLAUDE.md`).

## Protección de data/

`data/` es de solo lectura. Un hook `PreToolUse` (`.claude/settings.json` → `.claude/hooks/protect_data.py`) bloquea Write/Edit/NotebookEdit sobre `data/` y los comandos Bash que la modifican (`rm`, `mv`, `>`, `sed -i`, `cp` hacia `data/`, etc.). Leer sí está permitido. No detecta escrituras ocultas dentro de scripts (p. ej. un `python3` que escriba ahí); para eso, si hace falta, `chmod -R a-w data/`.
