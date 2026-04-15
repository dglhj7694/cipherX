import re

import yfinance as yf

from infrastructure.etf import FunctionHoldingsProvider, HoldingsProviderRegistry

_SCAN_SYMBOL_PATTERN = re.compile(r"\b[A-Z]{1,6}(?:[.-][A-Z0-9]{1,4})?\b")


def _build_etf_payload(symbol, tickers, source_label, as_of=""):
    tickers = list(dict.fromkeys([str(t).strip().upper() for t in tickers if str(t).strip()]))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "스캔 가능한 종목이 없습니다.", "as_of": ""}
    basis = f"As of {as_of}" if as_of else "기준일 표기 없음"
    return {
        "symbol": symbol,
        "tickers": tickers,
        "note": f"{source_label} · {basis} · {len(tickers)}종목",
        "error": "",
        "as_of": as_of,
    }


def _fetch_wikipedia_index_constituents(symbol):
    symbol = str(symbol or "").strip().upper()
    page_map = {
        "QQQ": ("https://en.wikipedia.org/wiki/Nasdaq-100", "Ticker", "Wikipedia Nasdaq-100 구성종목 기준"),
        "SPY": ("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", "Symbol", "Wikipedia S&P500 구성종목 기준"),
    }
    if symbol not in page_map:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "지원하지 않는 지수입니다.", "as_of": ""}

    import requests
    from bs4 import BeautifulSoup

    url, ticker_header, note = page_map[symbol]
    response = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    target_table = None
    for table in soup.select("table.wikitable"):
        headers = [th.get_text(" ", strip=True) for th in table.select("tr th")[:20]]
        if ticker_header in headers:
            target_table = table
            break
    if target_table is None:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "구성종목 표를 찾지 못했습니다.", "as_of": ""}

    tickers = []
    for row in target_table.select("tr")[1:]:
        cells = row.select("th,td")
        if not cells:
            continue
        ticker = str(cells[0].get_text(" ", strip=True) or "").upper().replace(".", "-")
        if _SCAN_SYMBOL_PATTERN.fullmatch(ticker):
            tickers.append(ticker)

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "구성종목 티커를 찾지 못했습니다.", "as_of": ""}

    lastmod = soup.select_one("#footer-info-lastmod")
    as_of = ""
    if lastmod:
        text = lastmod.get_text(" ", strip=True)
        date_match = re.search(r"edited on\s+(.+?)\s+\(UTC\)", text, flags=re.I)
        as_of = date_match.group(1).strip() if date_match else ""
    return _build_etf_payload(symbol, tickers, f"{note} (Wikipedia 페이지 수정일)", as_of)


def _fetch_first_trust_holdings(symbol):
    symbol = str(symbol or "").strip().upper()
    import requests
    from bs4 import BeautifulSoup

    url = f"https://www.ftportfolios.com/Retail/Etf/EtfHoldings.aspx?Ticker={symbol}&Print=Y"
    response = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    as_of_match = re.search(r'Holdings of the Fund as of\s+([0-9/]+)', response.text, flags=re.I)
    as_of = as_of_match.group(1) if as_of_match else ""

    collecting = False
    tickers = []
    for row in soup.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
        if not cells:
            continue
        if cells[:2] == ["Security Name", "Identifier"]:
            collecting = True
            continue
        if not collecting or len(cells) < 7:
            continue
        ticker = str(cells[1] or "").strip().upper().replace(".", "-")
        if _SCAN_SYMBOL_PATTERN.fullmatch(ticker):
            tickers.append(ticker)

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "First Trust holdings 표를 찾지 못했습니다.", "as_of": as_of}
    return _build_etf_payload(symbol, tickers, "First Trust 공식 holdings", as_of)


def _fetch_ishares_holdings(symbol):
    symbol = str(symbol or "").strip().upper()
    import csv
    import io
    import requests

    page_map = {
        "IGV": "https://www.ishares.com/us/products/239771/ishares-north-american-techsoftware-etf",
        "EUSA": "https://www.ishares.com/us/products/239693/ishares-msci-usa-etf",
        "IWB": "https://www.ishares.com/us/products/239707/ishares-russell-1000-etf",
        "IWM": "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf",
    }
    page_url = page_map.get(symbol)
    if not page_url:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "지원하지 않는 iShares ETF입니다.", "as_of": ""}

    page_text = requests.get(page_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}).text
    match = re.search(
        rf'href="([^"]*fileType=csv[^"]*fileName={symbol}_holdings[^"]*dataType=fund)"',
        page_text,
        flags=re.I,
    )
    if not match:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "iShares CSV 링크를 찾지 못했습니다.", "as_of": ""}

    csv_url = requests.compat.urljoin("https://www.ishares.com", match.group(1))
    raw_csv = requests.get(csv_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}).content
    csv_text = raw_csv.decode("utf-8-sig", errors="ignore")
    as_of_match = re.search(r'Fund Holdings as of,\s*"?([^"\n]+)"?', csv_text, flags=re.I)
    as_of = as_of_match.group(1).strip() if as_of_match else ""
    lines = [line for line in csv_text.splitlines() if line.strip()]
    data_start = None
    for idx, line in enumerate(lines):
        if line.startswith("Ticker,"):
            data_start = idx
            break
    if data_start is None:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "iShares CSV 헤더를 찾지 못했습니다.", "as_of": as_of}

    reader = csv.DictReader(io.StringIO("\n".join(lines[data_start:])))
    tickers = []
    for row in reader:
        ticker = str(row.get("Ticker") or "").strip().upper().replace(".", "-")
        if _SCAN_SYMBOL_PATTERN.fullmatch(ticker):
            tickers.append(ticker)

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "iShares holdings CSV에서 티커를 찾지 못했습니다.", "as_of": as_of}
    return _build_etf_payload(symbol, tickers, "iShares 공식 CSV", as_of)


def _fetch_alpha_architect_holdings(symbol):
    symbol = str(symbol or "").strip().upper()
    import requests
    from bs4 import BeautifulSoup

    url = f"https://funds.alphaarchitect.com/{symbol.lower()}/"
    response = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    target_table = None
    for table in soup.find_all("table"):
        headers = [th.get_text(" ", strip=True) for th in table.find_all("th")[:12]]
        if {"Ticker", "Name"}.issubset(set(headers)) and "% of Net Assets" in headers:
            target_table = table
            break
    if target_table is None:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "Alpha Architect holdings 표를 찾지 못했습니다.", "as_of": ""}

    date_hits = re.findall(r"\b\d{2}/\d{2}/\d{4}\b", response.text)
    as_of = date_hits[0] if date_hits else ""

    tickers = []
    for row in target_table.find_all("tr")[1:]:
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
        if not cells:
            continue
        ticker = str(cells[0] or "").strip().upper().replace(".", "-")
        if _SCAN_SYMBOL_PATTERN.fullmatch(ticker):
            tickers.append(ticker)

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "Alpha Architect 구성종목을 찾지 못했습니다.", "as_of": as_of}
    return _build_etf_payload(symbol, tickers, "Alpha Architect 공식 holdings", as_of)


def _fetch_innovator_holdings(symbol):
    symbol = str(symbol or "").strip().upper()
    import requests
    from bs4 import BeautifulSoup

    page_map = {
        "FFTY": "https://www.innovatoretfs.com/ffty",
    }
    page_url = page_map.get(symbol)
    if not page_url:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "지원하지 않는 Innovator ETF입니다.", "as_of": ""}

    response = requests.get(page_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    date_hits = re.findall(r"As of\s+(\d{1,2}/\d{1,2}/\d{4})", response.text)
    as_of = date_hits[0] if date_hits else ""

    tickers = []
    for row in soup.select("tr.hold_row"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
        if not cells:
            continue
        ticker = str(cells[0] or "").strip().upper().replace(".", "-")
        if _SCAN_SYMBOL_PATTERN.fullmatch(ticker):
            tickers.append(ticker)

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "Innovator 공식 holdings 표에서 티커를 찾지 못했습니다.", "as_of": as_of}
    return _build_etf_payload(symbol, tickers, "Innovator 공식 holdings", as_of)


def _fetch_ark_holdings(symbol):
    symbol = str(symbol or "").strip().upper()
    import csv
    import io
    import json
    import urllib.parse

    import cloudscraper
    import requests
    from bs4 import BeautifulSoup

    page_text = cloudscraper.create_scraper().get(
        f"https://www.ark-funds.com/funds/{symbol}",
        timeout=20,
    ).text
    api_match = re.search(r"/api/fund/holdings/(\d+)\?fundHoldingData=", page_text)
    if not api_match:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "ARK holdings API를 찾지 못했습니다.", "as_of": ""}

    payload = {
        "Heading": "Top 10 Holdings",
        "PdfLinkText": "Full Holdings PDF",
        "CsvLinkText": "Full Holdings CSV",
        "Link": {"Style": "", "Href": "", "Aria": "", "Target": "", "Text": ""},
    }
    data_json = urllib.parse.quote(json.dumps(payload, separators=(",", ":")))
    api_url = f"https://www.ark-funds.com/api/fund/holdings/{api_match.group(1)}?fundHoldingData={data_json}"
    html = cloudscraper.create_scraper().get(api_url, timeout=20).text
    soup = BeautifulSoup(html, "html.parser")
    csv_link_el = soup.find("a", href=re.compile(r"csv", re.I))
    as_of_match = re.search(r"As of\s+([0-9/]+)", soup.get_text(" ", strip=True), flags=re.I)
    as_of = as_of_match.group(1) if as_of_match else ""
    if not csv_link_el:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "ARK 공식 CSV 링크를 찾지 못했습니다.", "as_of": as_of}

    csv_text = requests.get(csv_link_el["href"], timeout=20, headers={"User-Agent": "Mozilla/5.0"}).text
    reader = csv.DictReader(io.StringIO(csv_text))
    tickers = []
    for row in reader:
        ticker = str(row.get("ticker") or "").strip().upper().replace(".", "-")
        if _SCAN_SYMBOL_PATTERN.fullmatch(ticker):
            tickers.append(ticker)
        if not as_of and row.get("date"):
            as_of = str(row.get("date")).strip()

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "ARK 공식 CSV에서 티커를 찾지 못했습니다.", "as_of": as_of}
    return _build_etf_payload(symbol, tickers, "ARK 공식 CSV", as_of)


def _fetch_wisdomtree_holdings(symbol):
    symbol = str(symbol or "").strip().upper()
    import cloudscraper
    from bs4 import BeautifulSoup

    page_map = {
        "WCBR": "https://www.wisdomtree.com/investments/etfs/megatrends/wcbr",
    }
    page_url = page_map.get(symbol)
    if not page_url:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "지원하지 않는 WisdomTree ETF입니다.", "as_of": ""}

    scraper = cloudscraper.create_scraper()
    page_text = scraper.get(page_url, timeout=20).text
    modal_match = re.search(r'data-href="([^"]*all-holdings[^"]+)"', page_text)
    if not modal_match:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "WisdomTree holdings 모달 링크를 찾지 못했습니다.", "as_of": ""}

    modal_html = scraper.get(modal_match.group(1), timeout=20).text
    soup = BeautifulSoup(modal_html, "html.parser")
    timestamp = soup.select_one(".timestamp")
    as_of = ""
    if timestamp:
        date_parts = [span.get_text(" ", strip=True) for span in timestamp.select("span")]
        if date_parts:
            as_of = date_parts[-1]

    tickers = []
    for table in soup.select("table.table"):
        title_cell = table.select_one("tr.table-section-head td")
        if not title_cell or "Securities" not in title_cell.get_text(" ", strip=True):
            continue
        for row in table.select("tbody tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.select("td")]
            if len(cells) < 2:
                continue
            raw_ticker = str(cells[1] or "").strip().upper()
            ticker = raw_ticker.split()[0].replace(".", "-") if raw_ticker else ""
            if _SCAN_SYMBOL_PATTERN.fullmatch(ticker):
                tickers.append(ticker)

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "WisdomTree holdings 모달에서 티커를 찾지 못했습니다.", "as_of": as_of}
    return _build_etf_payload(symbol, tickers, "WisdomTree 공식 holdings", as_of)


def _fetch_wedbush_holdings(symbol):
    symbol = str(symbol or "").strip().upper()
    import csv
    import io
    import requests

    page_map = {
        "IVES": "https://wedbushfunds.com/funds/ives/",
    }
    page_url = page_map.get(symbol)
    if not page_url:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "지원하지 않는 Wedbush ETF입니다.", "as_of": ""}

    page_text = requests.get(page_url, timeout=20, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"}).text
    date_match = re.search(r"Top Holdings\s+As of\s+([0-9/]+)", page_text, flags=re.I)
    csv_match = re.search(r'href="(https://wedbushfunds\.com/latest-sod-holdings-ives)"', page_text, flags=re.I)
    as_of = date_match.group(1) if date_match else ""
    if not csv_match:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "Wedbush 공식 CSV 링크를 찾지 못했습니다.", "as_of": as_of}

    csv_text = requests.get(csv_match.group(1), timeout=20, headers={"User-Agent": "Mozilla/5.0"}).text
    header_match = re.search(r'Holdings:,\s*"As of ([^"]+)"', csv_text, flags=re.I)
    if header_match:
        as_of = header_match.group(1).strip()

    lines = [line for line in csv_text.splitlines() if line.strip()]
    data_start = 0
    for idx, line in enumerate(lines):
        if line.startswith("Ticker,Name,"):
            data_start = idx
            break
    reader = csv.DictReader(io.StringIO("\n".join(lines[data_start:])))
    tickers = []
    for row in reader:
        ticker = str(row.get("Ticker") or "").strip().upper().replace(".", "-")
        if _SCAN_SYMBOL_PATTERN.fullmatch(ticker):
            tickers.append(ticker)

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "Wedbush 공식 CSV에서 티커를 찾지 못했습니다.", "as_of": as_of}
    return _build_etf_payload(symbol, tickers, "Wedbush 공식 CSV", as_of)


def _safe_fetch_etf_payload(fetcher, symbol, log_prefix):
    try:
        return fetcher(symbol)
    except Exception as exc:
        print(f"{log_prefix}{symbol}: {exc}")
        return {"symbol": symbol, "tickers": [], "note": "", "error": str(exc), "as_of": ""}


def _fetch_yahoo_holdings_payload(symbol):
    try:
        holdings = yf.Ticker(symbol).funds_data.top_holdings
    except Exception as exc:
        return {"symbol": symbol, "tickers": [], "note": "", "error": str(exc), "as_of": ""}

    if holdings is None or holdings.empty:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "구성종목 정보를 찾지 못했습니다.", "as_of": ""}

    tickers = []
    for raw in holdings.index.tolist():
        ticker = str(raw or "").strip().upper()
        if not ticker or ticker in {symbol, "$USD", "USD", "CASH"}:
            continue
        if _SCAN_SYMBOL_PATTERN.fullmatch(ticker):
            tickers.append(ticker)

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "스캔 가능한 종목이 없습니다.", "as_of": ""}
    return _build_etf_payload(symbol, tickers, "Yahoo Finance 상위 보유")


def fetch_etf_holdings_preview(symbol):
    symbol = str(symbol or "").strip().upper()
    if not symbol:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "ETF 심볼이 비어 있습니다.", "as_of": ""}

    registry = HoldingsProviderRegistry(
        providers=[
            FunctionHoldingsProvider(
                supported_symbols={"QQQ", "SPY"},
                fetcher=lambda ticker: _safe_fetch_etf_payload(_fetch_wikipedia_index_constituents, ticker, "[ETF-WIKI]"),
            ),
            FunctionHoldingsProvider(
                supported_symbols={"SKYY"},
                fetcher=lambda ticker: _safe_fetch_etf_payload(_fetch_first_trust_holdings, ticker, "[ETF-OFFICIAL]"),
            ),
            FunctionHoldingsProvider(
                supported_symbols={"IGV", "EUSA", "IWB", "IWM"},
                fetcher=lambda ticker: _safe_fetch_etf_payload(_fetch_ishares_holdings, ticker, "[ETF-OFFICIAL]"),
            ),
            FunctionHoldingsProvider(
                supported_symbols={"QMOM"},
                fetcher=lambda ticker: _safe_fetch_etf_payload(_fetch_alpha_architect_holdings, ticker, "[ETF-OFFICIAL]"),
            ),
            FunctionHoldingsProvider(
                supported_symbols={"FFTY"},
                fetcher=lambda ticker: _safe_fetch_etf_payload(_fetch_innovator_holdings, ticker, "[ETF-OFFICIAL]"),
            ),
            FunctionHoldingsProvider(
                supported_symbols={"IVES"},
                fetcher=lambda ticker: _safe_fetch_etf_payload(_fetch_wedbush_holdings, ticker, "[ETF-OFFICIAL]"),
            ),
            FunctionHoldingsProvider(
                supported_symbols={"ARKK", "ARKQ", "ARKW", "ARKG", "ARKF"},
                fetcher=lambda ticker: _safe_fetch_etf_payload(_fetch_ark_holdings, ticker, "[ETF-OFFICIAL]"),
            ),
            FunctionHoldingsProvider(
                supported_symbols={"WCBR"},
                fetcher=lambda ticker: _safe_fetch_etf_payload(_fetch_wisdomtree_holdings, ticker, "[ETF-OFFICIAL]"),
            ),
        ],
        fallback=FunctionHoldingsProvider(fetcher=_fetch_yahoo_holdings_payload),
    )
    return registry.fetch(symbol).to_dict()


def resolve_etf_universe(etf_items):
    resolved_items, combined, alias_notes, errors, date_notes = [], [], [], [], []
    for item in etf_items or []:
        requested = str(item.get("requested") or "").strip()
        resolved = str(item.get("resolved") or "").strip().upper()
        if not resolved:
            continue
        payload = fetch_etf_holdings_preview(resolved)
        if payload.get("tickers"):
            resolved_items.append(
                {
                    "requested": requested or resolved,
                    "resolved": resolved,
                    "note": payload.get("note", ""),
                    "as_of": payload.get("as_of", ""),
                }
            )
            combined.extend(payload["tickers"])
            if requested and requested.upper() != resolved:
                alias_notes.append(f"{requested} -> {resolved}")
            date_notes.append(f"{resolved} {payload.get('as_of') or '기준일 표기 없음'}")
        else:
            errors.append(f"{requested or resolved}: {payload.get('error') or '불러오기 실패'}")

    combined = list(dict.fromkeys([str(t).strip().upper() for t in combined if str(t).strip()]))
    summary = ""
    if date_notes:
        summary = f"{summary} 데이터 기준일: {' / '.join(date_notes)}".strip()
    if alias_notes:
        summary = f"{summary} 매핑: {' / '.join(alias_notes)}".strip()

    return {
        "items": resolved_items,
        "tickers": combined,
        "note": summary,
        "errors": errors,
    }
