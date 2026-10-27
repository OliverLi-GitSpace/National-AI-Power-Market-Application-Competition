# 全国 AI 电力市场应用大赛：线上赛本地准备

已阅读用户提供的《全国AI电力市场应用大赛-赛事说明(1).pdf》。这是本地开发起点，不是官方基线或平台 SDK。

## 已配置

- `.venv`：Python 3.12，复用当前环境已有科学计算包（网络代理不可用，暂未在线安装）。
- 电价预测：最近至多七个完整日的同小时价格均值。
- 储能交易：SciPy/HiGHS 混合整数优化，包含容量、功率、SOC、效率、充放电互斥和期末最低 SOC。
- 模拟数据、示例电池参数、约束测试及当前核心依赖版本。

## 运行

在本项目根目录执行：

```bash
export PYTHONPATH="$PWD/src"
.venv/bin/python -m power_market forecast --input examples/history.csv --output runs/forecast.csv
.venv/bin/python -m power_market trade --input runs/forecast.csv --battery examples/battery.json --output runs/trade.csv
.venv/bin/python -m unittest discover -s tests -v
```

新环境网络可用后可执行 `python -m venv .venv` 和 `.venv/bin/python -m pip install -e .`；模型研究依赖可用 `pip install -e '.[model]'`。

## 内部数据约定

CSV UTF-8，电价列 `price`。历史输入每行一小时，从日内 0 点起按时间升序，必须是完整的 24 小时日，不允许缺时；使用前须自行核对时间戳、时区和重复行。`hour` 在示例中仅用于阅读，程序按行顺序处理。预测结果为 `hour,price`；交易结果为 `hour,power_mw,soc_after`。正功率放电，负功率充电，时段长度 1 小时；容量 MWh，功率 MW，价格须统一为每 MWh 的同种货币。

示例数据完全模拟；电池参数不是赛事参数。`efficiency` 分别作用于充电和放电，往返效率为其平方。期末最低 SOC 默认等于初始 SOC，是本地保守策略约束，非官方硬性要求。优化最大化预测价格下的储能售电收入，没有计入交易费用、退化成本或不平衡结算。实际预测存在误差，不保证真实盈利。

**上述格式不是官方提交格式。获得官方样例后必须增加字段、单位、时区和序列对齐适配，不能直接上传本地结果。**

## 说明文件中的线上赛要求

见 `docs/competition-notes.md`。后续需要从平台取得数据样例、提交模板、实际储能参数、赛事日期和规则更新，才能完成真实数据训练及提交联调。
