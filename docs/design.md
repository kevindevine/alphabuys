# alpha buys design

alpha buys follows **jrny's design system**: `docs/design.md` in the jrny repo
(jrny.run). Font, palette, type scale, spacing, the black band, buttons and
motion all come from there; when the two disagree, jrny's doc wins. This file
holds only what's specific to alpha buys. Started 21 Oct 2026 from jrny `main`
at 1a8f413 (fonts and tokens copied then; refresh both if jrny changes them).

## 0. Point of view (draft, Kevin to own)

> **alpha buys reports super-shoe prices: which shop, what size, how much, and
> whether it just dropped.**

Same voice as jrny: it reports, it doesn't sell. No "deal of the day", no
urgency, no "grab them before they're gone". Facts: "Down €50 since 20 Oct",
"Lowest price we've seen", "140 pairs · 7 shops".

### 0.1 "They thought of that" details

Add to this list; don't let it shrink.

- **Your size stays when you switch shoes.** Same feet.
- **Only shops that deliver to Ireland.** Run4It and Pro:Direct's UK site were
  dropped for that (13 Oct); Pro:Direct's Irish site lists EU sizes, which are
  converted to UK with each brand's own chart.
- **"Lowest price we've seen" only after a drop.** A price that has never moved
  isn't news.
- **Sold-out pairs are hidden**, but their history still counts for the chart.
- **Icon, link preview, home screen.** The icon is v1's logo in miniature: a white
  "a" beside a neon "b" block on the band's black. Links preview with `icons/og.png`
  (the title on black). Added to the home screen it opens full screen, the band
  running up under the clock.
- **Share any pair.** A share icon beside Buy and on every row opens the phone's
  share panel (name, price, shop, your size, link); without one it copies the link.
  The link is alpha buys' own (`?pair=<id>&size=9`), never the shop's: the friend
  lands on that pair as "Shared with you", with today's price, the shoe, fit and
  size picked, and the other shops below. If it has sold out since, they get the
  cheapest of that shoe now. Buys from a shared visit carry Awin `clickref=share`.

## 0.2 Words

- **Super shoes**, everywhere (never "race shoes": that could mean spikes or
  any racing flat). Kevin, 21 Oct.
- **alpha buys**: two words, lowercase. Not tied to super shoes, so it can
  grow beyond race shoes later (Kevin, 21 Oct). The web address stays
  alphabuys.jrny.run.

## 1. What colour means here

jrny's rule applies: colour means something or it isn't used.

| Colour | Means |
|---|---|
| Neon `#d4ff3a` | **Your size**: the selected size chip (with a jrny-black edge), and your size tagged in every size line. Kevin, 21 Oct: "I don't mind the shock neon being used in places for this." The one colour from v1 that stays: for this, and for **buys** in the title (on a neon block, as v1's logo; Kevin, 21 Oct). |
| jrny teal `#009ead` | The price chart's line and fill |
| Small teal text `#007a87` | **A price fact**: "50% off", "Down €50", "Lowest" |
| jrny black `#2e2e2e` | Everything else: all text, the Buy button, selected controls ("Any", Men's) |
| Band `#242424` | The header band |

- **No red or green** (v1's red discount badges and green "lowest" note are
  retired). Neon only ever means your size (plus "buys" in the name).
- **"Any" size is black, not neon**: nothing is "yours" until you pick a size.
- **The sash is not used.** In jrny it means "race"; reusing it for "best
  price" would blur that. (Open: see §4.)

## 2. Structure (top to bottom)

1. **Black band.** No jrny wordmark or nav line (Kevin, 21 Oct: it's a side
   project, not a jrny screen). Large Title **alpha buys** (two words, lowercase like
   jrny, "buys" on the neon block; Kevin, 21 Oct) at the very top, then a
   Footnote "a jrny.run experiment" (jrny.run links home), one context line of facts
   ("357 pairs of super shoes in stock at 7 Irish shops · checked 2h ago"), then
   the **brand pills** (All · Nike · adidas · ASICS · Puma · Saucony; Kevin,
   21 Oct: brands, not models) in jrny's week-pill style: one line, semibold,
   the selected brand a white pill in bold. Right under them, still in the
   band, the **models** of the chosen brand as a quieter row (thin white
   outline, medium weight; selected a brighter outline in bold): "All Nike ·
   Alphafly 3 · Alphafly 4 · Vaporfly 4". Kept next to the brand so the two
   read as one choice (Kevin). Words the brand already says are dropped
   ("Deviate 4", "Sky Tokyo", "Pro 5"); rows in the list keep the full name.
2. **Filters on white.** Fit as a segmented control (selected in jrny black). **UK size chips**: 44 × 44, 9 px radius, white with
   the date-card shadow; your size neon. **All sizes visible, wrapping onto
   rows, never a sideways scroll** (Kevin, 21 Oct); "Any" spans two.
3. **Cheapest pair card.** The one card on the page (white, card shadow, 16 px
   radius). Photo on page grey, then: "Cheapest men's super shoe in UK 9"
   (Subheadline), brand + model (Title 3), shop · colour, **"In stock UK 7 · 8 ·
   9 · 10"** with your size tagged in neon (Kevin, 21 Oct: you need to see the sizes
   up top), the price as Large
   Title (34 bold) with the old price struck through and "50% off" in small
   teal, any price note, and a full-width black **Buy at {shop}** button
   (48 px, 12 px radius, as jrny's primary button).
4. **Cheapest each day.** jrny's chart style: teal line that draws itself in,
   eased teal fill (≈15 stops, never two), lowest day marked with a teal dot.
   Drawn at the screen's real width so its labels stay 13 px.
5. **In stock list.** Full width on white, **no dividers** (as jrny's week):
   64 px photo tile (9 px radius, page grey), Headline brand + model,
   Subheadline shop · colour, Data line "UK 7 · 8 · **9** · 10" (wraps, never
   cut off) with your size tagged in neon; price on the right (17 semibold), old price struck through
   (13 regular), then one teal fact.
6. **Shops we check.** Name (link, semibold) · pairs in stock, and "checked 2h
   ago" on the right; red (jrny's destructive) only when a shop hasn't been
   checked for 36 hours.
7. **Footnote.** How often prices are checked, delivery, confirm on the shop's
   site; **"Helps keep the jrny.run app running."** (Kevin, 22 Oct: short; the
   commission goes to jrny; same price, cheapest always first); **privacy** (no accounts, no
   tracking, no cookies of our own); contact hello@jrny.run; not affiliated;
   "A jrny.run experiment". Added 22 Oct for the Awin application. Buy links
   to affiliate shops carry `rel="sponsored"`.

## 3. Type, spacing, motion

All from jrny: General Sans only (self-hosted in `fonts/`, 400/500/600/700),
Apple text styles only, tabular figures everywhere, no grey text, 8-point
spacing, 20 px side margins, 44 px tap targets, one 720 px column on desktop,
jrny's motion tokens. Light only (jrny has no dark mode yet).

## 4. Open

- A mark for "the cheapest pair in your size" stronger than its place at the
  top of the page? (Not the sash: see §1.)
- Shoe photos come from the shops on different backgrounds (white, grey,
  lifestyle). A consistent tile would need our own cut-outs.
- ~~Name~~ Decided 21 Oct: **alpha buys**, two words, lowercase.
- Affiliate links (Awin) and the disclosure line.

## 5. Rejected along the way

- v1's sneaker-drop look (Anton display font, volt yellow, red badges, big
  photo cards): loud and fun, but not jrny, and the photos dominated.
