"""Build the static Conservas Iberia web shop from the sales CSV."""

import csv
import json
from decimal import ROUND_HALF_UP
from decimal import Decimal
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_CSV = ROOT / "data" / "conservas_iberia_ventas_2026.csv"
DATA_FICHA = ROOT / "data" / "ficha_productos.md"
OUTPUT = ROOT / "docs" / "index.html"

PRICE_CHANNEL = "Online (web propia)"

CATEGORY_BY_PRODUCT = {
    "Bonito del Norte en aceite de oliva": "pescado",
    "Sardinillas en aceite de oliva": "pescado",
    "Mejillones en escabeche": "pescado",
    "Ventresca de bonito": "pescado",
    "Pimientos del piquillo": "verduras",
    "Alcachofas en aceite": "verduras",
}
CATEGORY_LABELS = {"pescado": "Pescado y marisco", "verduras": "Verduras"}


def format_eur(cents: int) -> str:
    """Format cents as Spanish euros, e.g. 649 -> '6,49 €'."""
    euros, rest = divmod(cents, 100)
    integer = f"{euros:,}".replace(",", ".")
    return f"{integer},{rest:02d} €"


def load_ficha() -> dict[str, dict[str, str]]:
    """Parse the product sheet: '## name', description line, 'Formato: ...' line."""
    sheet: dict[str, dict[str, str]] = {}
    current: str | None = None
    for raw in DATA_FICHA.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("## "):
            current = line[3:].strip()
            sheet[current] = {"description": "", "format": ""}
        elif current and line.startswith("Formato:"):
            sheet[current]["format"] = line.removeprefix("Formato:").strip()
        elif current and line:
            sheet[current]["description"] = line
    return sheet


def load_products() -> list[dict[str, object]]:
    with DATA_CSV.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    last_month = max(row["mes"] for row in rows)
    names = list(dict.fromkeys(row["producto"] for row in rows))

    units_by_name = {
        r["producto"]: int(r["unidades"])
        for r in rows
        if r["canal"] == PRICE_CHANNEL and r["mes"] == last_month
    }
    best_units = max(units_by_name.values())
    ficha = load_ficha()

    products: list[dict[str, object]] = []
    for name in names:
        match = [
            r
            for r in rows
            if r["producto"] == name
            and r["canal"] == PRICE_CHANNEL
            and r["mes"] == last_month
        ]
        if len(match) != 1:
            msg = f"Expected one {PRICE_CHANNEL} row for {name!r} in {last_month}"
            raise SystemExit(msg)
        if not ficha.get(name, {}).get("description") or not ficha[name]["format"]:
            msg = f"Missing description or format in {DATA_FICHA.name} for {name!r}"
            raise SystemExit(msg)
        if name not in CATEGORY_BY_PRODUCT:
            msg = f"No category defined for product {name!r}"
            raise SystemExit(msg)
        price = (
            Decimal(match[0]["ingresos_eur"]) / Decimal(match[0]["unidades"])
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        products.append(
            {
                "id": len(products),
                "name": name,
                "category": CATEGORY_BY_PRODUCT[name],
                "price_cents": int(price * 100),
                "best": units_by_name[name] == best_units,
                "description": ficha[name]["description"],
                "format": ficha[name]["format"],
            }
        )
    return products


TEMPLATE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Conservas Iberia · Tienda online</title>
<script>
(function () {
  var theme;
  try { theme = localStorage.getItem("theme"); } catch (e) { theme = null; }
  if (theme !== "dark" && theme !== "light") {
    theme = window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  document.documentElement.dataset.theme = theme;
})();
</script>
<style>
/* Light theme (default) and dark theme share the same variable names */
:root{--bg:#faf6ee;--fg:#1f2a30;--muted:#566670;--card:#fff;--line:#e4dccb;--brand:#0b4f6c;--ctl:#0b4f6c;--ctl-on:#fff;--accent:#b0432c;--badge-bg:#f2c94c;--badge-fg:#3b2f00;color-scheme:light}
:root[data-theme=dark]{--bg:#0f171c;--fg:#e8eef1;--muted:#a3b3bc;--card:#18232a;--line:#2b3a43;--brand:#0b4f6c;--ctl:#8cc7e3;--ctl-on:#0d2a38;--accent:#b0432c;--badge-bg:#f2c94c;--badge-fg:#3b2f00;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--fg);line-height:1.4}
header{background:var(--brand);color:#fff;padding:.75rem 1rem;display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:.5rem 1rem}
header h1{margin:0;font-size:1.25rem}
.tools{display:flex;align-items:center;gap:.75rem;margin-left:auto}
header a{color:#fff;font-weight:600;display:inline-flex;align-items:center;min-height:44px}
header button{background:transparent;color:#fff;border-color:#fff}
main{max-width:1100px;margin:0 auto;padding:1rem;display:grid;gap:1.5rem}
@media(min-width:800px){main{grid-template-columns:1fr 320px;align-items:start}aside{position:sticky;top:1rem}}
:focus-visible{outline:3px solid #f2c94c;outline-offset:2px}
main :focus-visible{outline-color:var(--ctl)}
.filters{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:1rem}
button{font:inherit;cursor:pointer;border-radius:.5rem;border:1px solid var(--ctl);background:var(--card);color:var(--ctl);padding:.5rem .9rem;min-height:44px}
button[aria-pressed=true]{background:var(--ctl);color:var(--ctl-on)}
header button[aria-pressed=true]{background:transparent;color:#fff}
.grid{display:grid;gap:1rem;grid-template-columns:repeat(auto-fill,minmax(210px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:.75rem;padding:1rem;display:flex;flex-direction:column;gap:.4rem}
.card h3{margin:0;font-size:1.05rem}
.cat{color:var(--muted);font-size:.85rem}
.badge{align-self:flex-start;background:var(--badge-bg);color:var(--badge-fg);font-size:.8rem;font-weight:700;border-radius:999px;padding:.1rem .6rem}
.desc{margin:0;font-size:.92rem}
.format{color:var(--muted);font-size:.85rem}
.price{font-size:1.3rem;font-weight:700;margin-top:auto}
.add{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
.cart{background:var(--card);border:1px solid var(--line);border-radius:.75rem;padding:1rem}
.cart h2{margin:0 0 .75rem;font-size:1.15rem}
.line{display:grid;grid-template-columns:1fr auto;gap:.25rem .5rem;padding:.6rem 0;border-bottom:1px solid var(--line)}
.qty{display:flex;align-items:center;gap:.4rem}
.qty button{min-width:44px;padding:.3rem}
.total{display:flex;justify-content:space-between;font-size:1.2rem;font-weight:700;margin-top:.8rem}
.empty{color:var(--muted)}
.back{display:inline-flex;align-items:center;min-height:44px;margin-top:.5rem;color:var(--ctl)}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
[hidden]{display:none!important}
</style>
</head>
<body>
<header>
<h1>Conservas Iberia</h1>
<div class="tools">
<a href="#carrito">Carrito (<span id="count" aria-live="polite">0</span>)</a>
<button type="button" id="theme-toggle">Modo oscuro</button>
</div>
</header>
<main>
<section id="productos">
<h2>Nuestros productos</h2>
<div class="filters" role="group" aria-label="Filtrar por categoría">
<button type="button" data-filter="todos" aria-pressed="true">Todos</button>
<button type="button" data-filter="pescado" aria-pressed="false">Pescado y marisco</button>
<button type="button" data-filter="verduras" aria-pressed="false">Verduras</button>
</div>
<p class="sr" id="result" aria-live="polite"></p>
<div class="grid" id="grid">
__CARDS__
</div>
</section>
<aside id="carrito" class="cart">
<h2>Tu carrito</h2>
<p class="empty" id="empty">Tu carrito está vacío.</p>
<div id="lines" aria-live="polite"></div>
<div class="total"><span>Total</span><span id="total" aria-live="polite">0,00&nbsp;€</span></div>
<a class="back" href="#productos">Volver a los productos</a>
</aside>
</main>
<script>
const PRODUCTS = __PRODUCTS_JSON__;
const eur = new Intl.NumberFormat("es-ES", {style: "currency", currency: "EUR", useGrouping: "always"});
const fmt = (cents) => eur.format(cents / 100);
const cart = new Map();
let focusKey = null;

function render() {
  const lines = document.getElementById("lines");
  lines.textContent = "";
  let total = 0, count = 0;
  for (const [id, qty] of cart) {
    const p = PRODUCTS[id];
    total += p.price_cents * qty;
    count += qty;
    const row = document.createElement("div");
    row.className = "line";
    const name = document.createElement("strong");
    name.textContent = p.name;
    const sub = document.createElement("span");
    sub.textContent = fmt(p.price_cents * qty);
    const ctrl = document.createElement("div");
    ctrl.className = "qty";
    for (const [label, delta, aria] of [["−", -1, "Quitar una unidad"], ["+", 1, "Añadir una unidad"]]) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = label;
      b.setAttribute("aria-label", aria + " de " + p.name);
      b.dataset.qtyId = id;
      b.dataset.delta = delta;
      b.addEventListener("click", () => change(id, delta, true));
      ctrl.appendChild(b);
      if (delta === -1) {
        const q = document.createElement("span");
        q.textContent = qty;
        q.setAttribute("aria-label", "Cantidad: " + qty);
        ctrl.appendChild(q);
      }
    }
    row.append(name, sub, ctrl);
    lines.appendChild(row);
  }
  document.getElementById("total").textContent = fmt(total);
  document.getElementById("count").textContent = count;
  document.getElementById("empty").hidden = cart.size > 0;
  if (focusKey) {
    const target = document.querySelector(
      '[data-qty-id="' + focusKey.id + '"][data-delta="' + focusKey.delta + '"]'
    ) || document.querySelector('.add[data-id="' + focusKey.id + '"]');
    if (target) target.focus();
    focusKey = null;
  }
}

function change(id, delta, restoreFocus) {
  if (restoreFocus) focusKey = {id, delta};
  const qty = (cart.get(id) || 0) + delta;
  if (qty <= 0) cart.delete(id); else cart.set(id, qty);
  render();
}

document.querySelectorAll(".add").forEach((b) =>
  b.addEventListener("click", () => change(Number(b.dataset.id), 1, false)));

document.querySelectorAll("[data-filter]").forEach((b) =>
  b.addEventListener("click", () => {
    const f = b.dataset.filter;
    document.querySelectorAll("[data-filter]").forEach((x) =>
      x.setAttribute("aria-pressed", String(x === b)));
    let shown = 0;
    document.querySelectorAll(".card").forEach((c) => {
      c.hidden = f !== "todos" && c.dataset.category !== f;
      if (!c.hidden) shown += 1;
    });
    document.getElementById("result").textContent =
      shown + (shown === 1 ? " producto mostrado" : " productos mostrados");
  }));

const themeBtn = document.getElementById("theme-toggle");
function syncThemeButton() {
  const dark = document.documentElement.dataset.theme === "dark";
  themeBtn.textContent = dark ? "Modo claro" : "Modo oscuro";
}
themeBtn.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("theme", next); } catch (e) { /* storage unavailable */ }
  syncThemeButton();
});
syncThemeButton();
render();
</script>
</body>
</html>
"""


def render_card(product: dict[str, object]) -> str:
    category = str(product["category"])
    badge = '<span class="badge">Más vendido</span>' if product["best"] else ""
    return (
        f'<article class="card" data-category="{category}">'
        f"{badge}"
        f'<span class="cat">{escape(CATEGORY_LABELS[category])}</span>'
        f'<h3>{escape(str(product["name"]))}</h3>'
        f'<p class="desc">{escape(str(product["description"]))}</p>'
        f'<span class="format">{escape(str(product["format"]).capitalize())}</span>'
        f'<span class="price">{format_eur(int(product["price_cents"]))}</span>'  # type: ignore[call-overload]
        f'<button type="button" class="add" data-id="{product["id"]}">Añadir</button>'
        "</article>"
    )


def main() -> None:
    products = load_products()
    page = TEMPLATE.replace("__CARDS__", "\n".join(render_card(p) for p in products))
    keys = ("id", "name", "category", "price_cents")
    public = [{k: p[k] for k in keys} for p in products]
    page = page.replace("__PRODUCTS_JSON__", json.dumps(public, ensure_ascii=False))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(page, encoding="utf-8")
    print(f"Written {OUTPUT} with {len(products)} products:")
    for p in products:
        print(f"  {p['name']}: {format_eur(int(p['price_cents']))}")  # type: ignore[call-overload]


if __name__ == "__main__":
    main()
