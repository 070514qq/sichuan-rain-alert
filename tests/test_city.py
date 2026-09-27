import json
import unittest
from datetime import datetime
from scripts.collect_weather import numeric
from scripts.nmc_city import BJT, parse_hours, rain_window, collect_alerts


def column(time, code, rain='-'):
    return f'<div class="hour3"><div>{time}</div><div><img src="/assets/img/w/40x40/3/{code}.png"></div><div>{rain}</div></div>'


class CityTests(unittest.TestCase):
    def test_month_rollover_and_missing_quantity(self):
        rows = parse_hours(column('23:00', 2)+column('01日02:00', 7, '0.2mm'), '2026-09-30', numeric)
        self.assertIsNone(rows[0]['rainMm'])
        self.assertFalse(rows[0]['rainExpected'])
        self.assertTrue(rows[1]['rainExpected'])
        self.assertTrue(rows[1]['at'].startswith('2026-10-01'))

    def test_interval_bounds(self):
        rows = parse_hours(column('11:00', 2)+column('14:00', 7)+column('17:00', 7)+column('20:00', 2), '2026-09-27', numeric)
        w = rain_window(rows, datetime(2026, 9, 27, 10, tzinfo=BJT))
        self.assertEqual(w['status'], 'estimated')
        self.assertEqual(w['durationMinHours'], 3)
        self.assertEqual(w['durationMaxHours'], 9)

    def test_unknown_does_not_become_no_rain(self):
        rows = parse_hours(column('11:00', 9999)+column('14:00', 7), '2026-09-27', numeric)
        self.assertEqual(rain_window(rows, datetime(2026, 9, 27, 10, tzinfo=BJT))['status'], 'unknown')
        self.assertEqual(rain_window(rows, datetime(2026, 9, 27, 12, tzinfo=BJT))['status'], 'start_uncertain')

    def test_broken_timeline_rejected(self):
        with self.assertRaises(ValueError):
            parse_hours(column('11:00', 2)+column('17:00', 7), '2026-09-27', numeric)

    def test_identical_duplicate_is_deduplicated(self):
        rows = parse_hours(column('11:00', 2)*2+column('14:00', 7), '2026-09-27', numeric)
        self.assertEqual(len(rows), 2)
        with self.assertRaises(ValueError):
            parse_hours(column('11:00', 2)+column('11:00', 7), '2026-09-27', numeric)

    def test_alert_scope_and_lifecycle(self):
        payload = {'code': 0, 'data': {'page': {'totalPage': 1, 'list': [{'title': '四川省成都市气象台发布暴雨黄色预警信号', 'issuetime': '2026/09/27 10:00', 'alertid': 'test', 'url': '/publish/alarm/test.html'}]}}}
        result = collect_alerts(lambda url: json.dumps(payload), datetime.now(BJT))
        self.assertEqual(result['items'][0]['level'], '黄色')
        self.assertEqual(result['items'][0]['lifecycleStatus'], 'not_verified')
        payload['data']['page']['list'][0]['title'] = '云南省暴雨黄色预警'
        with self.assertRaises(ValueError):
            collect_alerts(lambda url: json.dumps(payload), datetime.now(BJT))
