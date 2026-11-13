# alpha buys

Tracks super-shoe prices (Nike Alphafly + Vaporfly, adidas Adios Pro, ASICS Metaspeed, Puma Nitro Elite, Saucony Endorphin Elite/Pro, New Balance SC Elite, Hoka Rocket X, On Cloudboom) and in-stock sizes across shops that deliver to Ireland
(Nike, Elverys, Lifestyle Sports, Top4Running, Sports Direct, Zalando, Pro:Direct, The Run Hub,
Mister Running, 365rider, SportsShoes).

- `check.py`: visits each shop for every shoe in `SHOES` (add a shoe there), writes `data/latest.json` and appends to `data/history.jsonl`
- `.github/workflows/check.yml`: runs the check every 3 hours (GitHub drops some scheduled runs) and saves the results
- `mac-check.sh`: checks Top4Running, Lifestyle Sports and 365rider from the Mac (they block GitHub's servers), run by
  launchd 4 times a day while the Mac is on
