# 四川雨情

[打开网站](https://070514qq.github.io/sichuan-rain-alert/) · [数据接入与部署说明](docs/数据接入与部署.md) · [原始计划书](docs/项目计划书.md)

使用用户指定的中央气象台降水实况页面，筛选四川站点，展示真实1小时降水、24小时累计降水、最近6个时次降雨图与雨量颜色区块。

GitHub Actions 按每十五分钟调度采集并部署 Pages，可能受 GitHub 排队和源端更新延迟影响。页面显示采集时间与观测时间，过期、失败和缺失数据均有明确提示。

**本来源不提供预测开始时间、持续时间或四川地方暴雨预警。相应栏目明确显示未提供；未出现的站点不补零，不据此判断安全。**

- [24小时降水实况来源](https://www.nmc.cn/publish/observations/24hour-precipitation.html)
- [1小时降水实况来源](https://www.nmc.cn/publish/observations/hourly-precipitation.html)
- [模拟数据演示版](https://070514qq.github.io/sichuan-rain-alert/demo.html)

## 本地验证

```sh
python3 -m unittest discover -s tests -v
python3 scripts/collect_weather.py data/weather.json
python3 -m http.server 8080
```

打开 `http://localhost:8080/`。实时版需要通过 HTTP 加载本地 JSON；演示版 `demo.html` 可以直接打开。

不需要接口密钥。仅部署明确列出的静态文件与运行时数据，脚本和测试不打包到网站。
