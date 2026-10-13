# Alpha Buys

Tracks Nike Alphafly prices and in-stock sizes across Irish shops
(Nike, Elverys, Lifestyle Sports, Top4Running, Sports Direct).

- `check.py`: visits each shop, writes `data/latest.json` and appends to `data/history.jsonl`
- `.github/workflows/check.yml`: runs the check 4 times a day and saves the results
