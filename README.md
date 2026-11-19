# Chennai Gold Rate Calculator

Live Chennai gold (24K / 22K / 18K), silver and platinum rates from
goodreturns.in (MJDTA rates), with a jewellery price calculator, a
22K vs 18K comparison for any weight, and a 10-day trend.

Live: https://pragadee24.github.io/chennai-gold-rate/

## How it stays current

`.github/workflows/rates.yml` runs every 30 minutes (and on push): it runs
`scraper.py`, writes `static/rates.json`, and deploys `static/` to GitHub Pages.

## Run locally

```
pip install -r requirements.txt
uvicorn app:app --port 7860   # serves the page plus a live /rates.json
```
