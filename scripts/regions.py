"""Administrative membership from Sichuan NPC's 2026 official county list.

Weather catalog names are joined explicitly; an unserved county stays missing.
"""
SOURCE = 'https://www.scspc.gov.cn/jyjd/202604/152661.html'
GROUPS = {
 '成都市': '锦江区 青羊区 金牛区 武侯区 成华区 龙泉驿区 青白江区 新都区 温江区 双流区 郫都区 新津区 简阳市 都江堰市 彭州市 邛崃市 崇州市 金堂县 大邑县 蒲江县',
 '自贡市': '自流井区 贡井区 大安区 沿滩区 荣县 富顺县',
 '攀枝花市': '东区 西区 仁和区 米易县 盐边县',
 '泸州市': '江阳区 龙马潭区 纳溪区 泸县 合江县 叙永县 古蔺县',
 '德阳市': '旌阳区 罗江区 广汉市 什邡市 绵竹市 中江县',
 '绵阳市': '涪城区 游仙区 安州区 江油市 三台县 梓潼县 盐亭县 平武县 北川羌族自治县',
 '广元市': '利州区 昭化区 朝天区 苍溪县 旺苍县 剑阁县 青川县',
 '遂宁市': '船山区 安居区 射洪市 蓬溪县 大英县',
 '内江市': '市中区 东兴区 隆昌市 资中县 威远县',
 '乐山市': '市中区 五通桥区 沙湾区 金口河区 峨眉山市 犍为县 井研县 夹江县 沐川县 峨边彝族自治县 马边彝族自治县',
 '南充市': '顺庆区 高坪区 嘉陵区 阆中市 南部县 西充县 仪陇县 营山县 蓬安县',
 '宜宾市': '翠屏区 南溪区 叙州区 江安县 长宁县 高县 筠连县 珙县 兴文县 屏山县',
 '广安市': '广安区 前锋区 华蓥市 岳池县 武胜县 邻水县',
 '达州市': '通川区 达川区 万源市 宣汉县 大竹县 渠县 开江县',
 '巴中市': '巴州区 恩阳区 南江县 通江县 平昌县',
 '雅安市': '雨城区 名山区 天全县 芦山县 宝兴县 荥经县 汉源县 石棉县',
 '眉山市': '东坡区 彭山区 仁寿县 洪雅县 丹棱县 青神县',
 '资阳市': '雁江区 安岳县 乐至县',
 '阿坝藏族羌族自治州': '马尔康市 金川县 小金县 阿坝县 若尔盖县 红原县 壤塘县 汶川县 理县 茂县 松潘县 九寨沟县 黑水县',
 '甘孜藏族自治州': '康定市 泸定县 丹巴县 九龙县 雅江县 道孚县 炉霍县 甘孜县 新龙县 德格县 色达县 石渠县 白玉县 理塘县 巴塘县 乡城县 稻城县 得荣县',
 '凉山彝族自治州': '西昌市 会理市 德昌县 会东县 宁南县 普格县 布拖县 昭觉县 金阳县 雷波县 美姑县 甘洛县 越西县 喜德县 冕宁县 盐源县 木里藏族自治县',
}
ALIASES = {'北川羌族自治县':'北川','木里藏族自治县':'木里','峨边彝族自治县':'峨边','马边彝族自治县':'马边','郫都区':'郫都','安州区':'安州','峨眉山市':'峨眉','九寨沟县':'九寨沟','广安区':'广安区','会理市':'会理城区'}
CENTERS = {'阿坝藏族羌族自治州':'马尔康','甘孜藏族自治州':'康定','凉山彝族自治州':'凉山'}


def build_regions(catalog):
    regions = []
    for parent, counties in GROUPS.items():
        center = CENTERS.get(parent, parent.removesuffix('市'))
        city_matches = [c for c in catalog if c['city'] == center]
        # Same display name can denote distinct products; only the city slug is used.
        city_matches = [c for c in city_matches if not c['url'].endswith('yibinxian.html')]
        for county in [None] + counties.split():
            if county is None:
                matches = city_matches
            else:
                alias = ALIASES.get(county, county[:-1] if county[-1] in '区县市' and len(county)>2 else county)
                matches = [c for c in catalog if c['city'] == alias]
                if county == '叙州区':
                    matches = [c for c in catalog if c['url'].endswith('yibinxian.html')]
                if sum(county in names.split() for names in GROUPS.values()) > 1:
                    matches = []
                # Never reuse a prefecture city product as a county product.
                if parent not in CENTERS:
                    matches = [c for c in matches if c not in city_matches]
            match = matches[0] if len(matches)==1 else None
            regions.append({'id':parent+'|'+(county or '市州代表点'), 'parent':parent,
                            'name':county or '市州代表点', 'kind':'county' if county else 'city',
                            'weatherCode':match['code'] if match else None})
    return regions
