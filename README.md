# 彩票历史数据与模型研究

在线页面：<https://liangren6666.github.io/marksix-predict/>

打开后选择日期，正码和特码各显示 20 个号码。不同日期的结果不同。

Python 负责抓取、校验、时间顺序评估和参考结果导出；Vue 3 + Vite 展示本地 CSV 和 JSON。
三个彩种属于独立数据集，不能因期号相同而合并。

## 安装与运行

本次验证环境：Python 3.12、Node.js 22。以下命令在项目根目录执行：

```powershell
python -m pip install -r requirements.txt -r requirements-ml.txt
cd web
npm ci
npm run dev
```

开发和构建前会自动将 `data/` 同步到 `web/public/data/`。
首页展示正码前 20 名和特码前 5 名，两组各自按模型分值排序。点击「生成预测」会读取最新的本地已校验 CSV，拟合正码模型并运行已有特码模型。
开发服务器和 `npm run preview` 支持实时计算；纯静态部署会展示构建时保存的预测快照。

## 更新数据与模型

在项目根目录依次运行：

```powershell
python fetch_marksix.py --kind newam6hc
python verify_marksix.py --kind newam6hc
python -m ml.run_train
python -m ml.run_benchmark
python -m ml.run_regular_benchmark
python -m ml.export_next_reference
python -m ml.web_prediction --out data/prediction_reference.json
python scripts/sync_viz_data.py
```

抓取和校验需要联网。训练默认读取 `data/newam6hc_5y_verified.csv`，因此不能跳过校验步骤。
修改特征代码后必须重新训练，再导出下一期参考；旧模型与新特征不能混用。

```powershell
python -m ml.predict_next --topk 10
python -m unittest discover -s tests -v
cd web
npm test
npm run build
```

`web/dist/` 是生产构建结果。由于使用 history 路由，部署服务需要将前端路由回退到 `index.html`。
模型文件是 Python pickle，只加载自己生成或可信来源的文件。

## 评估约定

- 样本按期号升序切分为 train / val / test，默认比例为 70% / 15% / 15%。
- 在 train 上拟合两个模型，只用 val 选择融合权重；验证成绩属于调参成绩。
- 固定权重后在 train + val 上重新训练，只在独立 test 上报告最终成绩；保存的也是这两个模型。
- 训练报告中的集成模型与模型对比页中的独立 HGB 使用不同配置，指标不应混为一谈。
- `k/49` 是均匀随机选择 k 个不同号码的理论命中率，不能用一次随机模拟代替理论值。
- 每个特征只使用目标期之前的信息；下一期参考额外使用最新已开奖一期，不复用最后一个训练样本。
- 概率按模型 `classes_` 映射到 49 个号码；小样本训练中缺失的类别不会导致号码错位。

本次修复后，现有 262 期测试集上的集成 Top-1 为 1.53%；验证集为 3.45%。
这些结果没有证明稳定的预测优势。下一步模型研究应增加滚动时间外评估与不确定性区间，避免继续围绕同一测试集调参。

## 本次优化与待处理项

已修复：下一期特征滞后一期、验证数据参与训练、训练内选择融合权重、遗漏值越过上限、
模型概率列错位、CSV 非法数据静默进入统计、并发加载状态竞争、空数据重复请求、图表纵轴计算产生 NaN。
已补充 Python 和 Node 回归测试，并重新生成模型、报告和前端数据。

原文件备份在 `.backups/optimization-20261109-150023/`。

仍值得继续处理：

1. `data/macau6hc_168.csv` 和对应 verified CSV 当前只有表头；原始 JSON 有 414 期数据。
   本次没有把这些原始记录标记为已校验。可重新运行 `python fetch_marksix.py --kind macau6hc_168`，
   然后 `python verify_marksix.py --kind macau6hc_168`，最后同步前端数据。
2. 当前目录没有 Git 仓库；建议建立版本管理，分开保存源码、原始数据快照和模型产物。

本次未进行外部数据源的实时准确性复核，也未运行耗时的 LSTM/MLP 可行性训练。
