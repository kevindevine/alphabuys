# Alpha Buys

Tracks race-shoe prices (Nike Alphafly, adidas Adios Pro, ASICS Metaspeed) and in-stock sizes across Irish and UK shops
(Nike, Elverys, Lifestyle Sports, Top4Running, Sports Direct, Zalando, Pro:Direct, Run4It).

- `check.py`: visits each shop for every shoe in `SHOES` (add a shoe there), writes `data/latest.json` and appends to `data/history.jsonl`
- `.github/workflows/check.yml`: runs the check 4 times a day and saves the results
- `mac-check.sh`: checks Top4Running and Lifestyle Sports from the Mac (they block GitHub's servers), run by
  launchd 4 times a day while the Mac is on
