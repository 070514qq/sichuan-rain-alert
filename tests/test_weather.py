import unittest
from datetime import datetime
from scripts.collect_weather import BJT, EXPECTED_COLUMNS, numeric, stations_from_payload, times_from_page


class WeatherTests(unittest.TestCase):
    def test_province_filter_and_missing_values(self):
        payload = {"unit": "mm", "columns": EXPECTED_COLUMNS, "rows": [
            ["四川", "成都", 104, 30, "ASC", "chengdu", 0],
            ["四川", "松潘", 103, 32, "ASC", "songpan", 999999],
            ["云南", "昆明", 102, 25, "AYN", "kunming", 12]]}
        result = stations_from_payload(payload)
        self.assertEqual(len(result), 2)
        self.assertEqual(result["成都|chengdu"]["valueMm"], 0)
        self.assertIsNone(result["松潘|songpan"]["valueMm"])
        self.assertNotIn("武侯|wuhou", result)

    def test_invalid_units_or_columns_rejected(self):
        for unit, columns in [("cm", EXPECTED_COLUMNS), ("mm", ["unknown"])]:
            with self.assertRaises(ValueError):
                stations_from_payload({"unit": unit, "columns": columns, "rows": []})

    def test_numeric_sentinels(self):
        for value in [None, True, -1, "NaN", "Infinity", 9999, "bad"]:
            self.assertIsNone(numeric(value))
        self.assertEqual(numeric("11.8"), 11.8)

    def test_times_are_sorted_and_future_excluded(self):
        html = '<div data-time1="2026/09/27 09:00"></div><div data-time1="2026/09/27 10:00"></div><div data-time1="2027/01/01 00:00"></div>'
        times = times_from_page(html, datetime(2026, 9, 27, 11, tzinfo=BJT))
        self.assertEqual([t.hour for t in times], [10, 9])
        self.assertEqual(times[0].utcoffset().total_seconds(), 28800)

    def test_missing_page_format_rejected(self):
        with self.assertRaises(ValueError):
            times_from_page("<html>maintenance</html>", datetime.now(BJT))


if __name__ == "__main__":
    unittest.main()
