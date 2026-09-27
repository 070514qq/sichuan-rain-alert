# 四川雨情

[打开网站](https://070514qq.github.io/sichuan-rain-alert/) · [数据接入与部署说明](docs/数据接入与部署.md) · [原始计划书](docs/项目计划书.md)

使用用户指定的中央气象台降水实况页面，筛选四川站点，展示真实1小时降水、24小时累计降水、最近24个时次降雨图与雨量颜色区块。

GitHub Actions 按每十五分钟调度采集并部署 Pages，可能受 GitHub 排队和源端更新延迟影响。页面显示采集时间与观测时间，过期、失败和缺失数据均有明确提示。

另接入中央气象台四川目录中的城市及区县的气温、湿度、未来七天概况及逐三小时预报，以及四川暴雨预警发布列表。城市选择与降水观测站选择独立，避免套用其他城市预报。

预计开始、结束和持续时间是逐三小时预报中首段连续降雨的区间推算，非官方精确时刻。源发布时间异常、过期、未知天气或边界不足时不编造估算。预警按官方原等级和发布时间显示；发布记录的解除/变更状态未核验，空列表不表示安全。

- [24小时降水实况来源](https://www.nmc.cn/publish/observations/24hour-precipitation.html)
- [1小时降水实况来源](https://www.nmc.cn/publish/observations/hourly-precipitation.html)
- [城市预报来源（成都）](https://www.nmc.cn/publish/forecast/ASC/chengdu.html)
- [官方预警信号列表](https://www.nmc.cn/publish/alarm.html)
- [模拟数据演示版](https://070514qq.github.io/sichuan-rain-alert/demo.html)

## 本地验证

```sh
python3 -m unittest discover -s tests -v
python3 scripts/collect_weather.py data/weather.json
python3 -m http.server 8080
```

打开 `http://localhost:8080/`。实时版需要通过 HTTP 加载本地 JSON；演示版 `demo.html` 可以直接打开。

不需要接口密钥。仅部署明确列出的静态文件与运行时数据，脚本和测试不打包到网站。


市区县分布采用四川人大2026年名单，提供21个市州、183个区县。数据仅按独立天气目录条目匹配，无独立产品的区县保留缺失。市州代表点不代表全市面积雨量。区划来源：https://www.scspc.gov.cn/jyjd/202604/152661.html 。

未来降水图可选择48小时、72小时或七天，逐三小时显示；同时展示七天源预报日雨量和所选地区最近24小时实况。全国降水产品历史图扩大为最近24个发布时次，源端可访问时才有数据，缺测不填零。
