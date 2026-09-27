import unittest
from scripts.regions import GROUPS, build_regions


class RegionTests(unittest.TestCase):
    def test_administrative_count(self):
        self.assertEqual(len(GROUPS),21)
        self.assertEqual(sum(len(x.split()) for x in GROUPS.values()),183)

    def test_city_is_not_substituted_for_unserved_district(self):
        catalog=[{'city':'成都','code':'city','url':'/publish/forecast/ASC/chengdu.html'},
                 {'city':'郫都','code':'county','url':'/publish/forecast/ASC/zuodu.html'}]
        regions=build_regions(catalog)
        self.assertIsNone(next(r for r in regions if r['name']=='锦江区')['weatherCode'])
        self.assertEqual(next(r for r in regions if r['name']=='郫都区')['weatherCode'],'county')
        self.assertEqual(next(r for r in regions if r['parent']=='成都市' and r['kind']=='city')['weatherCode'],'city')

    def test_same_county_name_is_not_assigned_to_two_cities(self):
        regions=build_regions([{'city':'市中','code':'ambiguous','url':'/publish/forecast/ASC/test.html'}])
        # NMC catalog has no parent metadata: avoid claiming identical names have unique geography.
        for r in regions:
            if r['name']=='市中区':
                self.assertIsNone(r['weatherCode'])
