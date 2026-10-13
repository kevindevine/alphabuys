"""Alpha Buys price checker.

Visits five Irish shops, finds every Nike Alphafly, and records price + in-stock
sizes (UK). Writes data/latest.json and appends to data/history.jsonl.
Run:  python3 check.py
"""
import json, re, subprocess, html, datetime, pathlib, sys
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
BROWSER_HEADERS = [
    "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language: en-IE,en;q=0.9",
    'sec-ch-ua: "Chromium";v="130", "Google Chrome";v="130"',
    "sec-ch-ua-mobile: ?0",
    'sec-ch-ua-platform: "macOS"',
    "Sec-Fetch-Dest: document", "Sec-Fetch-Mode: navigate",
    "Sec-Fetch-Site: none", "Sec-Fetch-User: ?1", "Upgrade-Insecure-Requests: 1",
]


def get(url, headers=(), browser=False):
    cmd = ["curl", "-s", "-L", "--max-time", "30", "-A", UA]
    if browser:  # Sports Direct only answers requests that look fully like Chrome
        cmd += ["--http2", "--compressed"] + [x for h in BROWSER_HEADERS for x in ("-H", h)]
    for h in headers:
        cmd += ["-H", h]
    r = subprocess.run(cmd + [url], capture_output=True, text=True)
    if r.returncode or not r.stdout:
        raise RuntimeError(f"fetch failed ({r.returncode}): {url}")
    return r.stdout


def model_of(name):
    m = re.search(r"alphafly\s*(?:next%?\s*)?(\d)", name, re.I)
    return f"Alphafly {m.group(1)}" if m else "Alphafly"


def gender_of(text):
    t = text.lower()
    return "women" if re.search(r"women|womens|\bw\b", t) else "men"


def size_num(s):
    s = str(s).strip().replace(",", ".")
    m = re.match(r"(\d+(?:\.\d)?)", s)
    return m.group(1).rstrip("0").rstrip(".") if m and "." in m.group(1) else (m.group(1) if m else s)


def offer(shop, name, colour, price, was, sizes, url, image=None, gender=None):
    return {
        "shop": shop, "model": model_of(name), "name": name.strip(), "colour": colour or "",
        "gender": gender or gender_of(name), "price": round(float(price), 2),
        "was": round(float(was), 2) if was and float(was) > float(price) else None,
        "sizes": sorted({size_num(s) for s in sizes}, key=lambda x: float(x) if re.match(r"^[\d.]+$", x) else 99),
        "url": url, "image": image,
    }


# ---------------------------------------------------------------- Nike
def nike():
    h = get("https://www.nike.com/ie/w?q=alphafly")
    data = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S).group(1))
    prods = {}
    def walk(o):
        if isinstance(o, dict):
            if "copy" in o and "pdpUrl" in o and "alphafly" in o["copy"]["title"].lower():
                prods[o["productCode"]] = o
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(data)

    def one(p):
        code = p["productCode"]
        page = get(p["pdpUrl"]["url"])
        i = page.find('"sizes":[', page.find('"selectedProduct":'))
        gtin_to_uk = {}
        if i > 0:
            for s in json.JSONDecoder().raw_decode(page, i + 8)[0]:
                for g in s.get("gtins", []):
                    gtin_to_uk[g["gtin"]] = s["localizedLabel"]
        stock = json.loads(get(
            f"https://api.nike.com/deliver/available_gtins/v3?filter=styleColor({code})&filter=merchGroup(XP)",
            ["nike-api-caller-id: com.nike.commerce.nikedotcom.web"]))
        sizes = [gtin_to_uk[o["gtin"]] for o in stock.get("objects", []) if o["available"] and o["gtin"] in gtin_to_uk]
        return offer("Nike", p["copy"]["title"], p["displayColors"]["colorDescription"],
                     p["prices"]["currentPrice"], p["prices"]["initialPrice"], sizes,
                     p["pdpUrl"]["url"], p["colorwayImages"]["squarishURL"], gender_of(p["copy"]["subTitle"]))
    with ThreadPoolExecutor(6) as ex:
        return list(ex.map(one, prods.values()))


# ---------------------------------------------------------------- Elverys (Shopify)
def elverys():
    d = json.loads(get("https://www.elverys.ie/search/suggest.json?q=alphafly&resources%5Btype%5D=product&resources%5Blimit%5D=10"))
    out = []
    for p in d["resources"]["results"]["products"]:
        if "alphafly" not in p["title"].lower():
            continue
        handle = p["url"].split("?")[0]
        j = json.loads(get(f"https://www.elverys.ie{handle}.js"))
        sizes = [v["title"] for v in j["variants"] if v["available"]]
        colour = handle.split("-")[-2] if handle[-1].isdigit() else ""
        out.append(offer("Elverys", j["title"], colour, j["price"] / 100,
                         (j["compare_at_price"] or 0) / 100, sizes,
                         f"https://www.elverys.ie{handle}", "https:" + j["featured_image"] if j.get("featured_image") else None))
    return out


# ---------------------------------------------------------------- Lifestyle Sports
def lifestyle():
    h = get("https://www.lifestylesports.com/ie/search?q=alphafly")
    out = []
    for t in re.findall(r'class="product-tile.*?END: \.product-tile', h, re.S):
        name = re.sub(r"<[^>]+>|\s+", " ", re.search(r'product-name-label">(.*?)</h2>', t, re.S).group(1)).strip()
        if "alphafly" not in name.lower():
            continue
        prices = [float(x) for x in re.findall(r"(?:€|&#8364;)\s*([\d.]+)", t)]
        sizes = re.search(r"Sizes in stock: ([^<]*)", t)
        img = re.search(r'<img[^>]*src="([^"]+)"', t)
        out.append(offer("Lifestyle Sports", name, "", prices[0], max(prices),
                         sizes.group(1).split(", ") if sizes else [],
                         re.search(r'href="([^"?]+)', t).group(1), img and html.unescape(img.group(1))))
    return out


# ---------------------------------------------------------------- Top4Running
def top4running():
    d = json.loads(get("https://live.luigisbox.com/search?tracker_id=214346-251725&q=alphafly&f[]=type:item&size=40"))
    paths = [h["url"] for h in d["results"]["hits"]]

    def one(path):
        page = get("https://top4running.ie" + path)
        for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
            try:
                x = json.loads(b)
            except ValueError:
                continue
            for g in (x if isinstance(x, list) else [x]):
                if g.get("@type") != "ProductGroup":
                    continue
                variants = g["hasVariant"]
                prices = [float(v["offers"]["price"]) for v in variants]
                sizes, in_stock_prices = [], []
                for v in variants:
                    if v["offers"]["availability"].endswith("InStock"):
                        m = re.search(r"eu-(\d+(?:-5)?)-uk", v["offers"]["url"])
                        if m:
                            sizes.append(m.group(1).replace("-5", ".5"))
                            in_stock_prices.append(float(v["offers"]["price"]))
                price = min(in_stock_prices or prices)
                was = re.search(r'class="[^"]*(?:price-old|old-price|crossed)[^"]*"[^>]*>\s*€?\s*([\d.,]+)', page)
                return offer("Top4Running", g["name"].replace("Running shoes ", ""), g.get("color", ""),
                             price, was and was.group(1).replace(",", ""), sizes,
                             "https://top4running.ie" + path, (g.get("image") or [None])[0],
                             "women" if "women" in path else "men")
    with ThreadPoolExecutor(6) as ex:
        got = [o for o in ex.map(one, paths) if o]
    if paths and not got:
        raise RuntimeError("product pages blocked (bot check)")
    return got


# ---------------------------------------------------------------- Sports Direct
def sportsdirect():
    h = get("https://ie.sportsdirect.com/running/running-shoes/nike-alphafly", browser=True)
    s = h.replace('\\"', '"').replace("\\u0026", "&")
    dec = json.JSONDecoder()
    seen, out = set(), []
    for m in re.finditer(r'\{"image":"https://cdn\.media\.amplience', s):
        try:
            p, _ = dec.raw_decode(s, m.start())
        except ValueError:
            continue
        if "alphafly" not in p.get("name", "").lower() or p.get("key") in seen:
            continue
        seen.add(p.get("key"))
        url = p.get("url") or p.get("productUrl") or ""
        if url.startswith("/"):
            url = "https://ie.sportsdirect.com" + url
        price = p.get("discountedPrice") or p.get("price")
        out.append(offer("Sports Direct", p["name"], p.get("color", ""), price, p.get("price"),
                         [v["description"].split(" ")[0] for v in p.get("sizeVariants", [])],
                         url, p.get("image")))
    return out


SHOPS = {"Nike": nike, "Elverys": elverys, "Lifestyle Sports": lifestyle,
         "Top4Running": top4running, "Sports Direct": sportsdirect}


def main():
    """python3 check.py [shop ...]  - checks the named shops, or all of them."""
    names = sys.argv[1:] or list(SHOPS)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    data = pathlib.Path(__file__).parent / "data"
    (data / "latest").mkdir(parents=True, exist_ok=True)
    (data / "history").mkdir(exist_ok=True)
    offers = []
    for shop in names:
        slug = shop.lower().replace(" ", "-")
        try:
            got = SHOPS[shop]()
        except Exception as e:
            # Keep the last good result; just note the failure.
            print(f"{shop:17} FAILED: {str(e)[:200]}")
            continue
        print(f"{shop:17} OK {len(got)} shoes")
        offers += got
        (data / "latest" / f"{slug}.json").write_text(json.dumps({"checked": now, "offers": got}, indent=1))
        with open(data / "history" / f"{slug}.jsonl", "a") as f:
            for o in got:
                f.write(json.dumps({"t": now, "url": o["url"], "price": o["price"], "sizes": o["sizes"]}) + "\n")
    print()
    for o in sorted(offers, key=lambda o: o["price"]):
        was = f" (was €{o['was']:.0f})" if o["was"] else ""
        print(f"€{o['price']:>7.2f}{was:14} {o['shop']:16} {o['model']} {o['gender']:5} {o['colour'][:22]:22} sizes: {', '.join(o['sizes']) or 'none'}")


if __name__ == "__main__":
    sys.exit(main())
