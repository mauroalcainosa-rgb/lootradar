"""Recolector de precios de LootRadar.

Corre en GitHub Actions cada pocas horas. Consulta las fuentes, escribe
data/deals.json (lo que lee la app) y data/history/<id>.json (historial),
y avisa por Firebase Cloud Messaging cuando un producto baja de precio.

Fuentes de la v1 sin claves: Steam (ofertas en Chile) y Epic (juegos gratis).
Mercado Libre y Eneba se agregan cuando existan las cuentas de afiliado.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HISTORY = DATA / "history"
DEALS_FILE = DATA / "deals.json"
HISTORY_POINTS = 180  # puntos guardados por producto
TIMEOUT = 20
HEADERS = {"User-Agent": "LootRadar/0.1 (+https://github.com/mauroalcainosa-rgb/lootradar)"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_json(url: str, params: dict | None = None) -> dict:
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            print(f"[aviso] {url} intento {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    return {}


# ---------------------------------------------------------------- Steam
def steam_specials() -> list[dict]:
    """Ofertas destacadas de Steam con precios para Chile."""
    data = get_json(
        "https://store.steampowered.com/api/featuredcategories",
        {"cc": "cl", "l": "spanish"},
    )
    items = (data.get("specials") or {}).get("items") or []
    out = []
    for it in items:
        if not it.get("discounted"):
            continue
        app_id = it.get("id")
        out.append({
            "id": f"steam-{app_id}",
            "source": "steam",
            "store": "Steam",
            "cat": "juegos",
            "name": it.get("name", ""),
            "kind": "PC",
            "now": round((it.get("final_price") or 0) / 100),
            "was": round((it.get("original_price") or 0) / 100),
            "currency": it.get("currency", "CLP"),
            "image": it.get("large_capsule_image") or it.get("header_image"),
            "url": f"https://store.steampowered.com/app/{app_id}/",
            "ends": it.get("discount_expiration"),
        })
    return out


# ---------------------------------------------------------------- Epic
def epic_free() -> list[dict]:
    """Juegos gratis de esta semana en Epic Games Store."""
    data = get_json(
        "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions",
        {"locale": "es-ES", "country": "CL", "allowCountries": "CL"},
    )
    elements = (((data.get("data") or {}).get("Catalog") or {}).get("searchStore") or {}).get("elements") or []
    out = []
    for el in elements:
        price = ((el.get("price") or {}).get("totalPrice")) or {}
        promos = ((el.get("promotions") or {}).get("promotionalOffers")) or []
        active = [o for p in promos for o in (p.get("promotionalOffers") or [])]
        if not active or price.get("discountPrice", 1) != 0:
            continue
        slug = el.get("productSlug") or ((el.get("catalogNs") or {}).get("mappings") or [{}])[0].get("pageSlug")
        image = next((k.get("url") for k in el.get("keyImages") or [] if k.get("type") in ("OfferImageWide", "Thumbnail")), None)
        out.append({
            "id": f"epic-{el.get('id')}",
            "source": "epic",
            "store": "Epic Games Store",
            "cat": "juegos",
            "name": el.get("title", ""),
            "kind": "PC · Gratis",
            "now": 0,
            "was": round((price.get("originalPrice") or 0) / 100),
            "currency": price.get("currencyCode", "CLP"),
            "image": image,
            "url": f"https://store.epicgames.com/es-ES/p/{slug}" if slug else "https://store.epicgames.com/es-ES/free-games",
            "free": True,
            "ends": active[0].get("endDate"),
        })
    return out


# ---------------------------------------------------------------- Afiliados
def affiliate_url(item: dict) -> str:
    """Enlace de compra. Cuando se aprueben las cuentas de afiliado (Mercado Libre,
    Eneba, Epic), aquí se arma el enlace con el código que entregue cada programa,
    leído desde los secretos de GitHub. Mientras tanto, enlace directo a la tienda."""
    return item["url"]


# ---------------------------------------------------------------- Historial
def update_history(item: dict, stamp: str) -> list[dict]:
    path = HISTORY / f"{item['id']}.json"
    points = json.loads(path.read_text()) if path.exists() else []
    if not points or points[-1]["p"] != item["now"]:
        points.append({"t": stamp, "p": item["now"]})
    points = points[-HISTORY_POINTS:]
    path.write_text(json.dumps(points, ensure_ascii=False, separators=(",", ":")))
    return points


# ---------------------------------------------------------------- Notificaciones
def send_drop_notifications(drops: list[tuple[dict, int]]) -> None:
    """Un mensaje por producto al tema 'p-<id>'. La app filtra por el límite de cada usuario."""
    sa = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    if not sa or not drops:
        print(f"[info] notificaciones omitidas (credencial: {'sí' if sa else 'no'}, bajas: {len(drops)})")
        return
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request

    info = json.loads(sa)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/firebase.messaging"]
    )
    creds.refresh(Request())
    url = f"https://fcm.googleapis.com/v1/projects/{info['project_id']}/messages:send"
    for item, old in drops:
        topic = "p-" + "".join(c if c.isalnum() or c in "-_" else "_" for c in item["id"])
        body = {"message": {
            "topic": topic,
            "notification": {
                "title": f"Bajó {item['name']}",
                "body": "Ahora gratis" if item["now"] == 0 else f"Ahora ${item['now']:,}".replace(",", ".") + f" (antes ${old:,})".replace(",", "."),
            },
            "data": {"id": item["id"], "now": str(item["now"]), "old": str(old)},
        }}
        r = requests.post(url, json=body, headers={"Authorization": f"Bearer {creds.token}"}, timeout=TIMEOUT)
        print(f"[fcm] {topic}: {r.status_code}")


# ---------------------------------------------------------------- Principal
def main() -> int:
    HISTORY.mkdir(parents=True, exist_ok=True)
    previous = {}
    if DEALS_FILE.exists():
        previous = {d["id"]: d for d in json.loads(DEALS_FILE.read_text()).get("items", [])}

    items = steam_specials() + epic_free()
    if not items:
        print("[error] ninguna fuente respondió; se conserva el archivo anterior", file=sys.stderr)
        return 1

    stamp = now_iso()
    drops = []
    for it in items:
        it["link"] = affiliate_url(it)
        it["hist"] = [p["p"] for p in update_history(it, stamp)][-6:]
        old = previous.get(it["id"], {}).get("now")
        if old is not None and it["now"] < old:
            drops.append((it, old))

    DEALS_FILE.write_text(json.dumps(
        {"updated": stamp, "country": "CL", "items": items},
        ensure_ascii=False, indent=1,
    ))
    print(f"[ok] {len(items)} productos, {len(drops)} bajas de precio")
    send_drop_notifications(drops)
    return 0


if __name__ == "__main__":
    sys.exit(main())
