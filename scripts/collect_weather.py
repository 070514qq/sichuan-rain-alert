"""Read the public NMC precipitation products used by its observation pages.

Only Sichuan station facts are retained. Missing rows are NOT zero rainfall.
No image or bulletin text is downloaded or republished.
"""
import json
import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

BJT = timezone(timedelta(hours=8))
BASE = "https://www.nmc.cn"
PAGES = {"24h": BASE + "/publish/observations/24hour-precipitation.html",
         "1h": BASE + "/publish/observations/hourly-precipitation.html"}
EXPECTED_COLUMNS = ["province", "stname", "lon", "lat", "pcode", "pinyin", "value"]


class ProductTimes(HTMLParser):
    def __init__(self):
        super().__init__()
        self.times = set()

    def handle_starttag(self, tag, attrs):
        value = dict(attrs).get("data-time1")
        if value:
            try:
                self.times.add(datetime.strptime(value, "%Y/%m/%d %H:%M").replace(tzinfo=BJT))
            except ValueError:
                pass


def times_from_page(text, now):
    parser = ProductTimes()
    parser.feed(text)
    result = sorted((t for t in parser.times if t <= now + timedelta(minutes=5)), reverse=True)
    if not result:
        raise ValueError("No valid product time")
    return result


def numeric(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError):
        return None
    return number if math.isfinite(number) and 0 <= number < 9999 else None


def stations_from_payload(payload):
    if payload.get("unit") != "mm" or payload.get("columns") != EXPECTED_COLUMNS:
        raise ValueError("Unexpected precipitation units or columns")
    if not isinstance(payload.get("rows"), list):
        raise ValueError("Missing station rows")
    stations = {}
    for row in payload["rows"]:
        if not isinstance(row, list) or len(row) != 7:
            raise ValueError("Unexpected station row")
        if row[4] != "ASC" or row[0] != "四川":
            continue
        if not isinstance(row[1], str) or not isinstance(row[5], str):
            raise ValueError("Invalid station name")
        # Name + source slug is a product key, not a fabricated WMO station code.
        key = row[1] + "|" + row[5]
        stations[key] = {"key": key, "name": row[1], "valueMm": numeric(row[6]),
                         "sourceUrl": BASE + "/publish/forecast/ASC/" + row[5] + ".html"}
    return stations


def fetch(url):
    for attempt in range(2):
        try:
            with urlopen(Request(url, headers={"User-Agent": "SichuanRainAlert/1.0"}), timeout=20) as response:
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise ValueError("Response too large")
                return raw.decode("utf-8")
        except Exception:
            if attempt:
                raise
            time.sleep(1)


def product(kind, dt, now):
    code = "pre_24h" if kind == "24h" else "pre_1h"
    url = BASE + "/product/realmap/" + code + "/" + dt.strftime("%Y%m%d%H") + ".json"
    payload = json.loads(fetch(url))
    stations = stations_from_payload(payload)
    return {"kind": kind, "observedAt": dt.isoformat(), "sourcePeriod": payload.get("obs_time", ""),
            "sourceDescription": payload.get("source", ""), "dataUrl": url,
            "stale": now - dt > timedelta(minutes=90), "stations": list(stations.values())}


def collect(now):
    result = {"schemaVersion": 2, "isDemo": False, "fetchedAt": now.isoformat(),
              "source": {"name": "中央气象台 · 降水实况", "url": PAGES["24h"]},
              "status": "error", "products": {}, "history": [], "errors": [],
              "forecastStatus": "not_provided", "alertsStatus": "not_provided"}
    for kind in ("24h", "1h"):
        try:
            available = times_from_page(fetch(PAGES[kind]), now)
            chosen = None
            # Published page and JSON may be briefly out of sync; retain real older timestamps.
            for dt in available[:3]:
                try:
                    chosen = product(kind, dt, now)
                    break
                except Exception:
                    continue
            if chosen is None:
                raise ValueError("No accessible published product")
            result["products"][kind] = chosen
            if kind == "1h":
                result["history"].append(chosen)
                for dt in [t for t in available if t < datetime.fromisoformat(chosen["observedAt"])][:5]:
                    try:
                        result["history"].append(product(kind, dt, now))
                    except Exception:
                        result["history"].append({"kind": kind, "observedAt": dt.isoformat(),
                                                  "stations": [], "status": "unavailable"})
        except Exception:
            result["errors"].append(kind + " 降水产品获取失败；未使用模拟或零值替代。")
    result["history"].sort(key=lambda item: item["observedAt"])
    if result["products"]:
        result["status"] = "partial" if result["errors"] else "ok"
    result["message"] = "已获取中央气象台降水实况；本来源不提供预测开始时间、持续时间或地方预警。" if result["products"] else "降水实况获取失败，当前数据无法确认。"
    return result


def main():
    result = collect(datetime.now(BJT))
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "data/weather.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print("Acquisition status:", result["status"], "products:", len(result["products"]))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write("## 气象采集\n\n" + result["message"] + "\n\n状态：`" + result["status"] + "`\n")
            for kind, data in result["products"].items():
                stream.write(f"\n- {kind}：观测 {data['observedAt']}；四川 {len(data['stations'])} 条记录。\n")
    if result["status"] == "error":
        print("::warning::Weather collection failed; deployed page will clearly display unavailable data.")


if __name__ == "__main__":
    main()
