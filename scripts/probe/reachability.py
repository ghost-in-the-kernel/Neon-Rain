"""Reachability probe for Neon Rain phase 0.3: one small GET per candidate host, report status."""
import urllib.request, urllib.error, socket, sys, time

CANDIDATES = {
    "Stooq daily CSV":        "https://stooq.com/q/d/l/?s=aapl.us&i=d",
    "Yahoo chart API":        "https://query1.finance.yahoo.com/v8/finance/chart/AAPL?range=5d&interval=1d",
    "Tiingo (needs token)":   "https://api.tiingo.com/tiingo/daily/aapl/prices?startDate=2024-01-02&endDate=2024-01-03",
    "Polygon (needs key)":    "https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/day/2024-01-02/2024-01-03",
    "Alpha Vantage (demo)":   "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=IBM&apikey=demo",
    "GDELT doc API":          "https://api.gdeltproject.org/api/v2/doc/doc?query=apple&mode=artlist&maxrecords=1&format=json",
    "Hugging Face Hub API":   "https://huggingface.co/api/datasets/Zihan1004/FNSPID",
    "Kaggle":                 "https://www.kaggle.com/api/v1/datasets/list?search=stock",
    "SEC EDGAR":              "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000320193&type=10-K&count=1",
    "FRED (needs key)":       "https://api.stlouisfed.org/fred/series?series_id=DGS10",
    "GitHub API":             "https://api.github.com/repos/ghost-in-the-kernel/Neon-Rain",
    "PyPI":                   "https://pypi.org/pypi/polars/json",
}

def probe(name, url):
    req = urllib.request.Request(url, headers={"User-Agent": "neon-rain-probe/0.1 (ghost-in-the-kernel)"})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read(200)
            return f"reachable (HTTP {r.status}, {len(body)}+ bytes, {time.time()-t:.1f}s)"
    except urllib.error.HTTPError as e:
        return f"host reachable, HTTP {e.code} ({e.reason})"
    except urllib.error.URLError as e:
        return f"refused: {e.reason}"
    except (socket.timeout, TimeoutError):
        return "refused: timeout"
    except Exception as e:
        return f"refused: {type(e).__name__}: {e}"

for name, url in CANDIDATES.items():
    print(f"{name:24} {probe(name, url)}")
