"""Scrape Chennai gold/silver/platinum rates from goodreturns.in."""

import asyncio
import re
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup

BASE = "https://www.goodreturns.in"
PAGES = {
    "gold": f"{BASE}/gold-rates/chennai.html",
    "silver": f"{BASE}/silver-rates/chennai.html",
    "platinum": f"{BASE}/platinum-rate-in-chennai.html",
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}
IST = ZoneInfo("Asia/Kolkata")

def _num(text: str) -> float | None:
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", text.replace("\xa0", " ").replace("- ", "-"))
    return float(m.group(0).replace(",", "")) if m else None


def _change(card) -> float | None:
    pill = card.select_one(".gr-change-pill")
    if not pill:
        return None
    val = _num(pill.get_text(" ", strip=True))
    if val is None:
        return None
    val = abs(val)
    return -val if "gr-change-down" in pill.get("class", []) else val


def parse_gold(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    rates = {}
    for k in ("24K", "22K", "18K"):
        span = soup.find(id=f"{k}-price")
        if not span:
            raise ValueError(f"{k} price not found")
        card = span.find_parent(class_="gr-price-card")
        rates[k] = {"price": _num(span.get_text()), "change": _change(card) if card else None}

    history = []
    for table in soup.find_all("table"):
        head = [th.get_text(strip=True) for th in table.find_all("th")]
        if head[:3] == ["Date", "24K", "22K"]:
            for tr in table.find_all("tr")[1:]:
                tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
                if len(tds) >= 3:
                    try:
                        d = datetime.strptime(tds[0], "%b %d, %Y").date().isoformat()
                    except ValueError:
                        continue
                    p24 = _num(tds[1].split("(")[0])
                    p22 = _num(tds[2].split("(")[0])
                    history.append({"date": d, "24K": p24, "22K": p22})
            break
    history.sort(key=lambda r: r["date"])
    return {"rates": rates, "history": history}


def parse_single(html: str, metal: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    span = soup.find(id=f"{metal}-1g-price")
    if not span:
        raise ValueError(f"{metal} price not found")
    card = span.find_parent(class_="gr-price-card")
    return {"price": _num(span.get_text()), "change": _change(card) if card else None}


async def scrape() -> dict:
    async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as c:
        gold_r, silver_r, plat_r = await asyncio.gather(
            *(c.get(u) for u in PAGES.values()), return_exceptions=True
        )
    if isinstance(gold_r, Exception) or gold_r.status_code != 200:
        raise RuntimeError(f"gold page failed: {gold_r!r}")
    out = parse_gold(gold_r.text)
    for name, resp in (("silver", silver_r), ("platinum", plat_r)):
        try:
            if isinstance(resp, Exception) or resp.status_code != 200:
                raise RuntimeError(repr(resp))
            out[name] = parse_single(resp.text, name)
        except Exception:
            out[name] = None
    now = datetime.now(IST)
    hist = out.get("history") or []
    out["date"] = hist[-1]["date"] if hist else now.date().isoformat()
    out["fetchedAt"] = now.isoformat(timespec="seconds")
    out["source"] = PAGES["gold"]
    return out


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "static/rates.json")
    data = asyncio.run(scrape())
    out.write_text(json.dumps(data, indent=1))
    print(f"wrote {out}: 24K {data['rates']['24K']['price']} 22K {data['rates']['22K']['price']} "
          f"18K {data['rates']['18K']['price']}")
