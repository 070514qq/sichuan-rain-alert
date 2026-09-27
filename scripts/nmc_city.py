"""Supplement NMC precipitation products with its public city forecast and alerts."""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import urlencode

BASE = "https://www.nmc.cn"
BJT = timezone(timedelta(hours=8))
CITY_NAMES = ["成都", "绵阳", "德阳", "南充", "内江", "资阳", "乐山", "自贡", "达州", "遂宁",
              "泸州", "宜宾", "巴中", "广安", "雅安", "广元", "眉山", "甘孜", "阿坝", "凉山", "攀枝花"]
RAIN_CODES = {3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 19, 21, 22, 23, 24, 25}


def parse_time(value):
    return datetime.strptime(value.replace("/", "-"), "%Y-%m-%d %H:%M").replace(tzinfo=BJT)


class HourParser(HTMLParser):
    """Extract only hour3 columns; never execute source HTML or scripts."""
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.field_depth = 0
        self.fields = []
        self.text = []
        self.code = None
        self.rows = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div" and "hour3" in attrs.get("class", "").split() and not self.depth:
            self.depth = 1
            self.fields = []
            self.code = None
            return
        if self.depth and tag == "div":
            self.depth += 1
            if self.depth == 2:
                self.text = []
                self.field_depth = 2
        if self.depth and tag == "img":
            match = re.search(r"/3/(\d+)\.png", attrs.get("src", ""))
            if match:
                self.code = int(match[1])

    def handle_data(self, data):
        if self.depth and self.field_depth:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag != "div" or not self.depth:
            return
        if self.depth == 2:
            self.fields.append("".join(self.text).strip())
            self.field_depth = 0
        self.depth -= 1
        if not self.depth:
            self.rows.append((self.fields, self.code))


def parse_hours(html, first_date, numeric):
    parser = HourParser()
    parser.feed(html)
    current_date = datetime.strptime(first_date, "%Y-%m-%d").date()
    previous_hour = -1
    rows = []
    for fields, code in parser.rows:
        if len(fields) < 3:
            continue
        match = re.fullmatch(r"(?:(\d+)日)?(\d{2}):(\d{2})", fields[0])
        if not match:
            continue
        hour, minute = int(match[2]), int(match[3])
        if hour < previous_hour:
            current_date += timedelta(days=1)
        if match[1] and int(match[1]) != current_date.day:
            raise ValueError("Forecast day mismatch")
        previous_hour = hour
        at = datetime.combine(current_date, datetime.min.time(), tzinfo=BJT).replace(hour=hour, minute=minute)
        rain_match = re.fullmatch(r"([0-9.]+)\s*mm", fields[2])
        value = numeric(rain_match[1]) if rain_match else None
        # '-' remains unknown rainfall quantity; weather icons may still predict rain.
        rainy = True if value is not None and value > 0 or code in RAIN_CODES else False if code in {0, 1, 2} else None
        row = {"at": at.isoformat(), "rainMm": value, "weatherCode": code, "rainExpected": rainy}
        if rows and rows[-1]["at"] == row["at"]:
            if rows[-1] != row:
                raise ValueError("Conflicting duplicate forecast time")
            continue
        rows.append(row)
    if not rows:
        raise ValueError("No three-hour forecast columns")
    for before, after in zip(rows, rows[1:]):
        if parse_iso(after["at"]) - parse_iso(before["at"]) != timedelta(hours=3):
            raise ValueError("Noncontiguous three-hour forecast")
    return rows


def parse_iso(value):
    return datetime.fromisoformat(value)


def rain_window(rows, now):
    """First upcoming contiguous rainy run; bounds, not minute-level certainty."""
    future = [row for row in rows if parse_iso(row["at"]) > now]
    first = next((i for i, row in enumerate(future) if row["rainExpected"] is True), None)
    if first is None:
        return {"status": "unknown" if any(r["rainExpected"] is None for r in future) or not future else "no_rain_in_window"}
    if any(r["rainExpected"] is None for r in future[:first]):
        return {"status": "unknown"}
    # A rainy first slot may describe an already ongoing process; start is unknown.
    at = parse_iso(future[first]["at"])
    if first == 0:
        return {"status": "start_uncertain", "firstRainAt": at.isoformat()}
    start_lo = parse_iso(future[first - 1]["at"])
    end = first
    while end + 1 < len(future) and future[end + 1]["rainExpected"] is True:
        end += 1
    result = {"status": "estimated", "startFrom": start_lo.isoformat(), "startTo": at.isoformat(),
              "lastRainAt": future[end]["at"]}
    if end + 1 >= len(future) or future[end + 1]["rainExpected"] is None:
        result["endStatus"] = "unknown"
        return result
    end_lo, end_hi = parse_iso(future[end]["at"]), parse_iso(future[end + 1]["at"])
    result.update(endStatus="estimated", endFrom=end_lo.isoformat(), endTo=end_hi.isoformat(),
                  durationMinHours=max(0, (end_lo - at).total_seconds() / 3600),
                  durationMaxHours=(end_hi - start_lo).total_seconds() / 3600)
    return result


def city_record(city, fetch, numeric, now):
    out = {"name": city["city"], "code": city["code"], "sourceUrl": BASE + city["url"], "status": "error"}
    try:
        response = json.loads(fetch(BASE + "/rest/weather?" + urlencode({"stationid": city["code"]})))
        if response.get("code") != 0 or not isinstance(response.get("data"), dict):
            raise ValueError("Invalid city response")
        data = response["data"]
        if data.get("real", {}).get("station", {}).get("province") != "四川省":
            raise ValueError("Province mismatch")
        real = data["real"]
        observed = parse_time(real["publish_time"])
        weather = real.get("weather", {})
        temp = weather.get("temperature")
        temp = float(temp) if temp is not None and -90 < float(temp) < 65 else None
        humidity = numeric(weather.get("humidity"))
        if humidity is not None and humidity > 100:
            humidity = None
        out.update(status="ok", observation={"observedAt": observed.isoformat(), "temperatureC": temp,
                                            "humidityPct": humidity}, forecast=None)
        predict = data.get("predict", {})
        details = predict.get("detail", [])
        if not details:
            return out
        issued = parse_time(predict["publish_time"])
        hours = parse_hours(fetch(out["sourceUrl"]), details[0]["date"], numeric)
        # Keep anomalous source timing visible; never silently adjust it.
        timing = "future_source_time" if issued > now + timedelta(minutes=5) else "stale" if now-issued > timedelta(hours=18) else "current"
        out["forecast"] = {"sourceTime": issued.isoformat(), "timing": timing, "resolutionHours": 3,
                           "hours": hours, "window": rain_window(hours, now),
                           "daily": [{"date": d["date"], "rainMm": numeric(d.get("precipitation")),
                                      "day": d.get("day", {}).get("weather", {}).get("info"),
                                      "night": d.get("night", {}).get("weather", {}).get("info")}
                                     for d in details[:3]]}
    except Exception:
        # A failed forecast does not suppress valid observations collected above.
        out["forecastError"] = "城市预报获取失败或格式不匹配"
    return out


def collect_cities(fetch, numeric, now):
    catalog = json.loads(fetch(BASE + "/rest/province/ASC"))
    if not isinstance(catalog, list):
        raise ValueError("Invalid Sichuan catalog")
    selected = [c for c in catalog if c.get("province") == "四川省" and c.get("city") in CITY_NAMES]
    if not selected:
        raise ValueError("No Sichuan cities")
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(lambda city: city_record(city, fetch, numeric, now), selected))
    return {"status": "ok" if all(r.get("forecast") for r in records) else "partial", "cities": records,
            "missingCities": [name for name in CITY_NAMES if name not in {c["name"] for c in records}],
            "sourceUrl": BASE + "/publish/forecast/ASC/chengdu.html"}


def collect_alerts(fetch, now):
    items = []
    for page in range(1, 11):
        query = urlencode({"pageNo": page, "pageSize": 100, "signaltype": "暴雨", "signallevel": "", "province": "四川省"})
        result = json.loads(fetch(BASE + "/rest/findAlarm?" + query))
        if result.get("code") != 0 or not isinstance(result.get("data", {}).get("page", {}).get("list"), list):
            raise ValueError("Invalid alert response")
        listing = result["data"]["page"]
        for item in listing["list"]:
            title = item.get("title", "")
            if "四川" not in title or "暴雨" not in title:
                raise ValueError("Unexpected alert region or type")
            issued = parse_time(item["issuetime"])
            level = next((color for color in ["红色", "橙色", "黄色", "蓝色"] if color in title), None)
            path = item.get("url", "")
            if not path.startswith("/publish/alarm/"):
                raise ValueError("Unexpected alert link")
            items.append({"id": item["alertid"], "title": title, "level": level, "issuedAt": issued.isoformat(),
                          "sourceUrl": BASE + path, "issuer": title.split("发布")[0],
                          "lifecycleStatus": "not_verified"})
        if page >= int(listing.get("totalPage", 1)):
            return {"status": "ok", "checkedAt": now.isoformat(), "items": items,
                    "sourceUrl": BASE + "/publish/alarm.html", "scope": "四川省暴雨预警发布记录"}
    raise ValueError("Incomplete alert pagination")
