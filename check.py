"""Alpha Buys price checker.

Visits each shop, finds every race shoe in SHOES, and records price + in-stock
sizes (UK). Writes data/latest/<shop>.json and appends to data/history/<shop>.jsonl.
Run:  python3 check.py [shop ...]
"""
import json, re, subprocess, html, datetime, pathlib, sys, time
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
    # --fail: a blocked page (403 etc.) is an error, so the last good prices are kept.
    # --retry: shops sometimes say "slow down" (429); wait and try again.
    cmd = ["curl", "-s", "-L", "--fail", "--retry", "4", "--retry-delay", "10", "--max-time", "30", "-A", UA]
    if browser:  # Sports Direct only answers requests that look fully like Chrome
        cmd += ["--http2", "--compressed"] + [x for h in BROWSER_HEADERS for x in ("-H", h)]
    for h in headers:
        cmd += ["-H", h]
    r = subprocess.run(cmd + [url], capture_output=True, text=True)
    if r.returncode or not r.stdout:
        raise RuntimeError(f"fetch failed ({r.returncode}): {url}")
    return r.stdout


def alphafly_model(name):
    m = re.search(r"alphafly\s*(?:next\s*(?:%|percent)?\s*)?(\d)?", name, re.I)
    return f"Alphafly {m.group(1) or 1}"


def adios_model(name):
    m = re.search(r"adios\s*pro\s*(evo\s*)?(\d)?", name, re.I)
    return "Adios Pro " + ("Evo " if m.group(1) else "") + (m.group(2) or "1")


def metaspeed_model(name):
    m = re.search(r"metaspeed\s*(sky|edge|ray)\s*(\+|plus)?\s*(tokyo|paris)?", name, re.I)
    name = "Metaspeed " + m.group(1).title() + ("+" if m.group(2) else "")
    return f"{name} {m.group(3).title()}" if m.group(3) else name


def vaporfly_model(name):
    m = re.search(r"vaporfly\s*(?:next\s*(?:%|percent)?\s*)?(\d)?", name, re.I)
    return f"Vaporfly {m.group(1) or 1}"


def puma_model(name):
    m = re.search(r"(deviate|fast-?r)\s*nitro\s*elite\s*(\d)?", name, re.I)
    line = "Deviate" if m.group(1).lower() == "deviate" else "Fast-R"
    return f"{line} Nitro Elite {m.group(2) or 1}"


def saucony_model(name):
    m = re.search(r"endorphin\s*(elite|pro)\s*(\d)?", name, re.I)
    return f"Endorphin {m.group(1).title()} {m.group(2) or 1}"


# The race shoes we track. `match` decides whether a product title is one of them
# (so spikes, singlets and lookalike names are skipped). `q` can be a list when
# one entry covers two shoe lines.
SHOES = [
    {"id": "alphafly", "brand": "Nike", "q": "alphafly",
     "match": r"alphafly", "model": alphafly_model, "prodirect_tag": "silo_alphafly"},
    {"id": "adios-pro", "brand": "adidas", "q": "adios pro",
     "match": r"adios\s*pro", "model": adios_model, "prodirect_tag": "silo_adizero"},
    {"id": "metaspeed", "brand": "ASICS", "q": "metaspeed",
     "match": r"metaspeed\s*(sky|edge|ray)", "model": metaspeed_model, "prodirect_tag": "silo_metaspeed"},
    {"id": "vaporfly", "brand": "Nike", "q": "vaporfly",
     "match": r"vaporfly", "model": vaporfly_model, "prodirect_tag": "silo_vaporfly"},
    {"id": "puma-elite", "brand": "Puma", "q": ["deviate nitro elite", "fast-r nitro elite"],
     "match": r"(deviate|fast-?r)\s*nitro\s*elite", "model": puma_model},
    {"id": "saucony-endorphin", "brand": "Saucony", "q": ["endorphin elite", "endorphin pro"],
     "match": r"endorphin\s*(elite|pro)", "model": saucony_model, "prodirect_tag": "silo_endorphin"},
]
NOT_SHOES = (r"singlet|tights?|socks?|calf|shorts?|\btop\b|\bbra\b|\bcap\b|t-shirt|jacket"
             r"|kids|junior|track|spikes?|equipment|trail")


def is_shoe(shoe, title):
    return re.search(shoe["match"], title, re.I) and not re.search(NOT_SHOES, title, re.I)


def gender_of(text):
    t = text.lower()
    return "women" if re.search(r"women|womens|\bw\b", t) else "men"


def size_num(s):
    """UK size as text: '9', '9.5', and adidas thirds as '8⅔' / '9⅓'."""
    s = str(s).strip().replace(",", ".").replace("⅓", " 1/3").replace("⅔", " 2/3")
    m = re.match(r"(\d+)(?:\.(\d+))?(?:\s*([12])/3)?", s)
    if not m:
        return s
    whole, dec, third = m.groups()
    if third:
        return whole + ("⅓" if third == "1" else "⅔")
    if dec in ("33", "3"):
        return whole + "⅓"
    if dec in ("67", "66", "7"):
        return whole + "⅔"
    return whole + (".5" if dec and dec.startswith("5") else "")


def size_key(x):
    m = re.match(r"(\d+)(.*)", x)
    if not m:
        return 99
    return int(m.group(1)) + {"": 0, ".5": .5, "⅓": .33, "⅔": .67}.get(m.group(2), 0)


def offer(shoe, shop, name, colour, price, was, sizes, url, image=None, gender=None):
    return {
        "shoe": shoe["id"], "shop": shop, "model": shoe["model"](name), "name": name.strip(), "colour": colour or "",
        "gender": gender or gender_of(name), "price": round(float(price), 2),
        "was": round(float(was), 2) if was and float(was) > float(price) else None,
        "sizes": sorted({size_num(s) for s in sizes}, key=size_key),
        "url": url, "image": image,
    }


# ---------------------------------------------------------------- Nike
def nike(shoe):
    if shoe["brand"] != "Nike":
        return []
    h = get("https://www.nike.com/ie/w?q=" + shoe["q"].replace(" ", "+"))
    data = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S).group(1))
    prods = {}
    def walk(o):
        if isinstance(o, dict):
            if "copy" in o and "pdpUrl" in o and is_shoe(shoe, o["copy"]["title"]):
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
        return offer(shoe, "Nike", p["copy"]["title"], p["displayColors"]["colorDescription"],
                     p["prices"]["currentPrice"], p["prices"]["initialPrice"], sizes,
                     p["pdpUrl"]["url"], p["colorwayImages"]["squarishURL"], gender_of(p["copy"]["subTitle"]))
    with ThreadPoolExecutor(6) as ex:
        return list(ex.map(one, prods.values()))


# ---------------------------------------------------------------- Shopify shops
def shopify_find(domain, shoe):
    """Product handles matching the shoe. Shopify search returns at most 10, so
    ask a few ways (men's / women's) to catch them all."""
    handles = set()
    for extra in ("", " mens", " womens"):
        q = (shoe["q"] + extra).replace(" ", "+")
        d = json.loads(get(f"https://{domain}/search/suggest.json?q={q}&resources%5Btype%5D=product&resources%5Blimit%5D=10"))
        handles |= {p["handle"] for p in d["resources"]["results"]["products"] if is_shoe(shoe, p["title"])}
    return handles


def elverys(shoe):
    out = []
    for h in shopify_find("www.elverys.ie", shoe):
        handle = "/products/" + h
        j = json.loads(get(f"https://www.elverys.ie{handle}.js"))
        sizes = [v["title"] for v in j["variants"] if v["available"]]
        colour = handle.split("-")[-2] if handle[-1].isdigit() else ""
        out.append(offer(shoe, "Elverys", j["title"], colour, j["price"] / 100,
                         (j["compare_at_price"] or 0) / 100, sizes,
                         f"https://www.elverys.ie{handle}", "https:" + j["featured_image"] if j.get("featured_image") else None))
    return out


# ---------------------------------------------------------------- Lifestyle Sports
def lifestyle(shoe):
    h = get("https://www.lifestylesports.com/ie/search?q=" + shoe["q"].replace(" ", "+"))
    out = []
    for t in re.findall(r'class="product-tile.*?END: \.product-tile', h, re.S):
        name = re.sub(r"<[^>]+>|\s+", " ", re.search(r'product-name-label">(.*?)</h2>', t, re.S).group(1)).strip()
        if not is_shoe(shoe, name):
            continue
        prices = [float(x) for x in re.findall(r"(?:€|&#8364;)\s*([\d.]+)", t)]
        sizes = re.search(r"Sizes in stock: ([^<]*)", t)
        img = re.search(r'<img[^>]*src="([^"]+)"', t)
        out.append(offer(shoe, "Lifestyle Sports", name, "", prices[0], max(prices),
                         sizes.group(1).split(", ") if sizes else [],
                         re.search(r'href="([^"?]+)', t).group(1), img and html.unescape(img.group(1))))
    return out


# ---------------------------------------------------------------- Top4Running
def top4running(shoe):
    q = shoe["q"].replace(" ", "+")
    d = json.loads(get(f"https://live.luigisbox.com/search?tracker_id=214346-251725&q={q}&f[]=type:item&size=48"))
    hits = [h for h in d["results"]["hits"] if is_shoe(shoe, h["attributes"].get("title", ""))]
    paths = [h["url"] for h in hits]
    # Top4Running's own label (Czech): ženy = women, muži = men
    women = {h["url"] for h in hits if "ženy" in (h["attributes"].get("Gender") or [])}

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
                        # e.g. ...?size=42-eu-8-uk-...  or  42-2-3-eu-8-uk-...  (adidas thirds)
                        m = re.search(r"eu-(\d+(?:-5|-1-3|-2-3)?)-uk", v["offers"]["url"])
                        if m:
                            sizes.append(m.group(1).replace("-5", ".5").replace("-1-3", " 1/3").replace("-2-3", " 2/3"))
                            in_stock_prices.append(float(v["offers"]["price"]))
                price = min(in_stock_prices or prices)
                was = re.search(r'class="[^"]*(?:price-old|old-price|crossed)[^"]*"[^>]*>\s*€?\s*([\d.,]+)', page)
                return offer(shoe, "Top4Running", g["name"].replace("Running shoes ", ""), g.get("color", ""),
                             price, was and was.group(1).replace(",", ""), sizes,
                             "https://top4running.ie" + path, (g.get("image") or [None])[0],
                             "women" if path in women or "women" in path else "men")
    with ThreadPoolExecutor(6) as ex:
        got = [o for o in ex.map(one, paths) if o]
    if paths and not got:
        raise RuntimeError("product pages blocked (bot check)")
    return got


# ---------------------------------------------------------------- Sports Direct
def sportsdirect(shoe):
    h = get("https://ie.sportsdirect.com/searchresults?descriptionfilter=" + shoe["q"].replace(" ", "+"), browser=True)
    s = h.replace('\\"', '"').replace("\\u0026", "&")
    dec = json.JSONDecoder()
    seen, out = set(), []
    for m in re.finditer(r'\{"image":"https://cdn\.media\.amplience', s):
        try:
            p, _ = dec.raw_decode(s, m.start())
        except ValueError:
            continue
        if not is_shoe(shoe, p.get("name", "")) or p.get("key") in seen:
            continue
        seen.add(p.get("key"))
        url = p.get("url") or p.get("productUrl") or ""
        if not url.startswith("http"):  # links come without the shop's address
            url = "https://ie.sportsdirect.com/" + url.lstrip("/")
        price = p.get("discountedPrice") or p.get("price")
        out.append(offer(shoe, "Sports Direct", p["name"], p.get("color", ""), price, p.get("price"),
                         [v["description"].split(" ")[0] for v in p.get("sizeVariants", [])],
                         url, p.get("image")))
    return out


# ---------------------------------------------------------------- Zalando
def zalando(shoe):
    h = get("https://www.zalando.ie/catalog/?q=" + shoe["q"].replace(" ", "+"), browser=True)
    dec, prods = json.JSONDecoder(), {}
    # Product cards are cached in pieces; merge every fragment per SKU.
    for m in re.finditer(r'\{"data":\{"product":\{"id":"ern:product::', h):
        try:
            p = dec.raw_decode(h, m.start())[0]["data"]["product"]
        except (ValueError, KeyError):
            continue
        prods.setdefault(p["sku"], {}).update({k: v for k, v in p.items() if v is not None})
    out = []
    for p in prods.values():
        if not is_shoe(shoe, p.get("name", "")) or "displayPrice" not in p:
            continue
        dp = p["displayPrice"]
        orig = dp["original"]["amount"] / 100
        price = (dp.get("promotional") or {}).get("amount", orig * 100) / 100
        model, colour = (re.split(r" - [^-]*(?:shoes|trainers)[^-]* - ", p["name"], 1) + [""])[:2]
        out.append(offer(shoe, "Zalando", model.title(), colour, price, orig,
                         [x["size"] for x in p.get("simples", [])], p["uri"],
                         (p.get("mediumPackshotImage") or {}).get("uri"),
                         "women" if p.get("navigationTargetGroup") == "WOMEN" else "men"))
    return out


# ---------------------------------------------------------------- Pro:Direct (Shopify)
# EU -> UK sizes by brand and fit, taken from Top4Running, which lists both for
# these exact shoes (Pro:Direct Ireland only shows EU sizes). ASICS race shoes are
# unisex, sized as men's.
EU_TO_UK = {
    ("Nike", "men"): {"35.5": "3", "36": "3.5", "36.5": "4", "37.5": "4.5", "38": "5", "38.5": "5.5", "39": "6", "40": "6", "40.5": "6.5", "41": "7", "42": "7.5", "42.5": "8", "43": "8.5", "44": "9", "44.5": "9.5", "45": "10", "45.5": "10.5", "46": "11", "47": "11.5", "47.5": "12", "48.5": "13", "49.5": "14"},
    ("Nike", "women"): {"35.5": "2.5", "36": "3", "36.5": "3.5", "37.5": "4", "38": "4.5", "38.5": "5", "39": "5.5", "40": "6", "40.5": "6.5", "41": "7", "42": "7.5", "42.5": "8", "43": "8.5", "44": "9", "44.5": "9.5"},
    ("adidas", "men"): {"36⅔": "4", "37⅓": "4.5", "38": "5", "38⅔": "5.5", "39⅓": "6", "40": "6.5", "40⅔": "7", "41⅓": "7.5", "42": "8", "42⅔": "8.5", "43⅓": "9", "44": "9.5", "44⅔": "10", "45⅓": "10.5", "46": "11", "46⅔": "11.5", "47⅓": "12", "48": "12.5", "48⅔": "13", "50": "14"},
    ("adidas", "women"): {"36": "3.5", "36⅔": "4", "37⅓": "4.5", "38": "5", "38⅔": "5.5", "39⅓": "6", "40": "6.5", "40⅔": "7", "41⅓": "7.5", "42": "8", "42⅔": "8.5", "43⅓": "9", "44": "9.5", "44⅔": "10", "45⅓": "10.5"},
    ("ASICS", "men"): {"35.5": "2.5", "36": "3", "37": "3.5", "37.5": "4", "38": "4.5", "39": "5", "39.5": "5.5", "40": "6", "40.5": "6.5", "41.5": "7", "42": "7.5", "42.5": "8", "43.5": "8.5", "44": "9", "44.5": "9.5", "45": "10", "46": "10.5", "46.5": "11", "47": "11.5", "48": "12", "49": "13", "50.5": "14", "51.5": "15"},
    ("Puma", "men"): {"39": "6", "40": "6.5", "40.5": "7", "41": "7.5", "42": "8", "42.5": "8.5", "43": "9", "44": "9.5", "44.5": "10", "45": "10.5", "46": "11", "46.5": "11.5", "47": "12", "48": "13", "48.5": "13"},
    ("Puma", "women"): {"35.5": "3", "36": "3.5", "37": "4", "37.5": "4.5", "38": "5", "38.5": "5.5", "39": "6", "40": "6.5", "40.5": "7", "41": "7.5", "42": "8", "42.5": "8.5"},
    ("Saucony", "men"): {"35.5": "2.5", "36": "3", "37": "3.5", "37.5": "4", "38": "4.5", "38.5": "5", "39": "5.5", "40": "6", "40.5": "6.5", "41": "7", "42": "7.5", "42.5": "8", "43": "8.5", "44": "9", "44.5": "9.5", "45": "10", "46": "10.5", "46.5": "11", "47": "11.5", "48": "12", "49": "13", "50": "14"},
    ("Saucony", "women"): {"35.5": "3", "36": "3.5", "37": "4", "37.5": "4.5", "38": "5", "38.5": "5.5", "39": "6", "40": "6.5", "40.5": "7", "41": "7.5", "42": "8", "42.5": "8.5", "43": "9", "43.5": "9.5", "44": "10"},
}


def eu_to_uk(shoe, gender, eu):
    eu = eu.replace(" ½", ".5").replace("½", ".5").replace(" ⅓", "⅓").replace(" ⅔", "⅔").strip()
    table = EU_TO_UK.get((shoe["brand"], gender)) or EU_TO_UK.get((shoe["brand"], "men"), {})
    return table.get(eu)


def shopify_products(domain, handles):
    # One at a time with a pause: Pro:Direct turns away quick bursts of requests.
    out = []
    for h in sorted(handles):
        out.append(json.loads(get(f"https://{domain}/products/{h}.js")))
        time.sleep(1)
    return out


def prodirect(shoe):
    # The Irish site: the UK one stopped shipping to the EU in July 2026.
    domain, out, handles = "www.prodirectsport.ie", [], set()
    if "prodirect_tag" not in shoe:  # Pro:Direct Ireland doesn't stock this line
        return []
    # Its quick search stops at 10, so list the shoe line's tag page instead.
    for page in range(1, 8):
        h = get(f"https://{domain}/collections/all/{shoe['prodirect_tag']}?page={page}")
        found = {x for x in re.findall(r"/products/([a-z0-9-]+)", h) if is_shoe(shoe, x.replace("-", " "))}
        if not found - handles:
            break
        handles |= found
    for p in shopify_products(domain, handles):
        vs = [v for v in p["variants"] if v["available"]] or p["variants"]
        name = p["title"]
        # Pro:Direct keeps the colourway in the URL handle
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        rest = re.sub(r"-(mens|womens)-shoes-\d+$", "", p["handle"])
        colour = rest[len(slug):].strip("-").replace("-", " ").title() if rest.startswith(slug) else ""
        img = p.get("featured_image")
        gender = "women" if "gender_female" in p.get("tags", []) or re.search(r"women", name, re.I) else "men"
        sizes = [eu_to_uk(shoe, gender, v["option1"] or v["title"]) for v in vs if v["available"]]
        out.append(offer(shoe, "Pro:Direct", name, colour,
                         min(v["price"] for v in vs) / 100, max(v["compare_at_price"] or 0 for v in vs) / 100,
                         [x for x in sizes if x], f"https://{domain}/products/{p['handle']}",
                         "https:" + img if img and img.startswith("//") else img, gender))
    return out


SHOPS = {"Nike": nike, "Elverys": elverys, "Lifestyle Sports": lifestyle,
         "Top4Running": top4running, "Sports Direct": sportsdirect, "Zalando": zalando,
         "Pro:Direct": prodirect}



def check_shop(fn):
    """Every tracked shoe at one shop. A shoe that fails is skipped; if all fail, raise."""
    got, errors, seen = [], [], set()
    for shoe in SHOES:
        qs = shoe["q"] if isinstance(shoe["q"], list) else [shoe["q"]]
        for q in qs:
            try:
                for o in fn({**shoe, "q": q}):
                    if o["url"] not in seen:
                        seen.add(o["url"]); got.append(o)
            except Exception as e:
                errors.append(f"{shoe['id']} ({q}): {str(e)[:120]}")
    if errors and len(errors) == sum(len(x["q"]) if isinstance(x["q"], list) else 1 for x in SHOES):
        raise RuntimeError("; ".join(errors))
    for e in errors:
        print("   partial failure,", e)
    return got


def main():
    """python3 check.py [shop ...]  - checks the named shops, or all of them."""
    names = sys.argv[1:] or list(SHOPS)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    data = pathlib.Path(__file__).parent / "data"
    (data / "latest").mkdir(parents=True, exist_ok=True)
    (data / "history").mkdir(exist_ok=True)
    offers = []
    for shop in names:
        slug = re.sub(r"[^a-z0-9]+", "-", shop.lower())
        try:
            got = check_shop(SHOPS[shop])
        except Exception as e:
            # Keep the last good result; just note the failure.
            print(f"{shop:17} FAILED: {str(e)[:200]}")
            continue
        print(f"{shop:17} OK {len(got)} shoes")
        offers += got
        (data / "latest" / f"{slug}.json").write_text(json.dumps({"checked": now, "offers": got}, indent=1))
        with open(data / "history" / f"{slug}.jsonl", "a") as f:
            for o in got:
                f.write(json.dumps({"t": now, "shoe": o["shoe"], "url": o["url"], "price": o["price"], "sizes": o["sizes"]}) + "\n")
    print()
    for o in sorted((o for o in offers if o["sizes"]), key=lambda o: (o["shoe"], o["price"])):
        was = f" (was €{o['was']:.0f})" if o["was"] else ""
        print(f"€{o['price']:>7.2f}{was:14} {o['shop']:16} {o['model']:22} {o['gender']:5} {o['colour'][:22]:22} sizes: {', '.join(o['sizes']) or 'none'}")


if __name__ == "__main__":
    sys.exit(main())
