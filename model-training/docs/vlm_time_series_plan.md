# Qwen3-VL 电池充电曲线 Demo 工程规格

## 目标

本阶段目标是尽快交付一个可演示 demo，而不是开展论文式研究。

端到端链路：

```text
现有电池充电过程 JSON
-> 运行时绘制功率/电流曲线图
-> 构造 Qwen3-VL 多模态 prompt
-> Qwen3-VL 输出可解析诊断结果
-> 保存 demo 结果供客户展示
```

优先级：

1. 先跑通 zero-shot / few-shot demo；
2. 再构造 VLM SFT 数据；
3. SFT 跑通后再接 GRPO；
4. 输出结果只需要稳定、可解析、便于展示，不追求复杂结构化；
5. 图像规则要固定，避免 demo 中出现同类样本展示风格不一致。

## 当前明确决策

- 基座模型：`Qwen3-VL`。
- 默认模型路径：`models/Qwen3-VL`。
- 第一版图像重点绘制 `power_series` 和 `current_series`。
- `voltage_series` 第一版可不画，后续如客户需要再加入。
- `key_processes` 无法判断时允许输出空列表。
- 容量范围使用业务关注区间：`40-60%`、`60-80%`、`80-90%`、`90-100%`、`未知`。
- 第一版避免提前批量保存大量图片；推理时优先运行时绘图并直接输入模型。
- 为了客户展示和问题排查，推理脚本允许通过参数选择是否把图片落盘保存。

## 现有数据契约

项目当前一条样本对应一块电池：

```text
battery_id: str
label: 电池故障 / 电池老化 / 非标电池 / 正常
reason: str | None
charging_process: list[ChargingProcessRecord]
```

每次充电过程：

```text
process_id: str
charge_start_time: str | None
charge_end_time: str | None
current_series: list[float]
voltage_series: list[float]
power_series: list[float]
charge_capacity: list[float]
time_offset: list[float] | None
```

第一版直接复用现有 `dataset/sft.json`、`dataset/grpo.json` 或同结构 JSON 文件。
真实业务数据中可能额外包含 `time_offset`，表示每个数据点距离充电开始的时间，单位为分钟。
VLM 绘图链路需要优先使用 `time_offset`。

## Demo 输入

### 推理脚本

单样本推理：

```bash
python -m chargellm.vision.infer_vlm \
  --data-path dataset/sft.json \
  --index 0 \
  --model-name-or-path models/Qwen3-VL \
  --output-path artifacts/vlm_demo/predictions.jsonl \
  --save-images
```

批量推理：

```bash
python -m chargellm.vision.infer_vlm \
  --data-path dataset/sft.json \
  --limit 20 \
  --model-name-or-path models/Qwen3-VL \
  --output-path artifacts/vlm_demo/predictions.jsonl \
  --save-images
```

建议参数：

```text
--data-path              输入 JSON 文件
--index                  单条样本下标，和 --limit 二选一
--limit                  批量推理条数
--model-name-or-path     默认 models/Qwen3-VL
--output-path            JSONL 输出路径
--image-dir              图片保存目录，默认 artifacts/vlm_demo/images
--save-images            是否保存运行时生成的图片
--max-new-tokens         默认 512
--temperature            demo 默认 0.0
```

## Demo 输出

模型最终输出保持简单 JSON：

```json
{
  "label": "电池故障",
  "capacity_range": "60-80%",
  "confidence": 0.76,
  "key_processes": ["p003"],
  "reason": "p003 的功率曲线相对其他充电过程波动更明显，电流响应也不稳定，疑似存在异常充电行为。"
}
```

字段约束：

- `label`：只能是 `电池故障`、`电池老化`、`非标电池`、`正常`。
- `capacity_range`：只能是 `40-60%`、`60-80%`、`80-90%`、`90-100%`、`未知`。
- `confidence`：`0.0-1.0` 数字。
- `key_processes`：当前样本中的 `process_id` 列表；无法定位时允许 `[]`。
- `reason`：一到三句话，面向客户展示，不输出长篇分析。

推理脚本保存的 JSONL 每行包含：

```json
{
  "battery_id": "battery_001",
  "sample_index": 0,
  "image_paths": ["artifacts/vlm_demo/images/battery_001/summary.png"],
  "raw_output": "...",
  "parsed_output": {
    "label": "电池老化",
    "capacity_range": "80-90%",
    "confidence": 0.82,
    "key_processes": ["p006", "p007"],
    "reason": "..."
  }
}
```

如果未开启 `--save-images`，`image_paths` 输出空列表或运行时图片标识。

## 容量范围规则

第一版容量范围只用于粗粒度展示。

如果数据中有可信容量或 SOH 标注，直接转换为：

```text
[0.40, 0.60) -> 40-60%
[0.60, 0.80) -> 60-80%
[0.80, 0.90) -> 80-90%
[0.90, 1.00+] -> 90-100%
```

如果没有真实容量标注，工程 demo 可以使用近似值：

```text
capacity_score = last_process.charge_capacity[-1] / reference_capacity
```

`reference_capacity` 第一版从当前数据集估计：

```text
reference_capacity = percentile(all_last_charge_capacity, 95)
```

兜底规则：

- `charge_capacity` 缺失、为空或不可用：`未知`；
- `reference_capacity <= 0`：`未知`；
- `capacity_score < 0.40`：仍输出 `40-60%`，但 `confidence` 应偏低；
- 明显异常值需要 clip 到 `[0, 1]` 后再分桶。

## 图像生成总体规格

第一版生成一张主图 `summary.png`，用于直接输入 Qwen3-VL。

如后续发现单图信息太密，再拆成两张：

```text
power_overlay.png
current_overlay.png
```

但第一版以单图为准，减少多图处理复杂度。

### 图像输入策略

默认策略：

- 推理时运行时绘图；
- 图片对象直接送入 Qwen3-VL processor；
- 不强制保存到磁盘。

开启 `--save-images` 时保存到：

```text
artifacts/vlm_demo/images/<battery_id>/summary.png
```

SFT/GRPO 数据构建阶段需要可复现图片路径，因此数据转换脚本默认保存图片。

### 图像内容

`summary.png` 包含两块区域：

```text
上半部分：多次 power_series 叠加曲线
下半部分：多次 current_series 叠加曲线
```

要求：

- 每条曲线代表一次充电过程；
- 图例显示 `process_id`；
- 标题显示 `battery_id`；
- 使用白底；
- 颜色稳定，按充电过程顺序分配；
- 线宽固定，建议 `2.0`；
- 字体大小适合客户展示，不要过小。

### x 轴规则

x 轴必须使用绝对充电时长，不能使用归一化进度。

原因：

- 客户更容易理解；
- 不同充电过程需要在同一个时间坐标下比较；
- 充电时长本身可能是诊断依据。

实现规则：

1. 如果存在 `time_offset`：
   - 优先使用 `time_offset` 作为 x 轴来源；
   - `time_offset` 单位为分钟，绘图时转换为小时；
   - 若 `time_offset[0] != 0`，数据处理阶段必须补一个 `0` 点；
   - 补点时 `power_series`、`current_series`、`voltage_series`、`charge_capacity` 也必须同步补齐；
   - 补齐值第一版使用各序列第一个有效值，表示充电开始时刻的可视化锚点；
   - 补点行为必须写入 manifest 的 `warnings` 或 `preprocess_notes`。
2. 如果没有 `time_offset`，但 `charge_start_time` 和 `charge_end_time` 可解析：
   - 使用真实充电时长；
   - x 轴单位为小时；
   - 每个数据点按真实起止时间均匀分布。
3. 如果时间字段不可用：
   - 默认采样间隔按配置推断；
   - 优先使用 `--default-sample-minutes`，默认 `10`；
   - x 轴单位仍为小时。
4. x 轴范围对同一块电池内所有过程保持一致：
   - `xlim = [0, max_duration_hours]`。

`time_offset` 校验规则：

- 长度应与 `power_series` 和 `current_series` 一致；
- 若长度不一致，按最短长度截断，并在 manifest 中记录 warning；
- 必须单调不降；
- 若存在重复时间点，保留最后一个值或按同一时间点聚合平均，并记录 warning；
- 若存在负数，过滤负数点，并记录 warning；
- 若补 0 后序列长度变化，manifest 需要记录 `inserted_zero_offset=true`。

### 图像尺寸规则

根据单块电池最大充电时长选择图片宽度：

```text
max_duration < 3h      -> 1200 x 800
3h <= max_duration < 6h -> 1600 x 900
6h <= max_duration < 9h -> 2000 x 1000
max_duration >= 9h      -> 2200 x 1000
```

如果客户展示终端加载大图较慢，可以统一降采样到最大宽度 `1600`。

### y 轴规则

第一版使用单块电池内自适应 y 轴，保证曲线展示清楚。

要求：

- power 和 current 分别独立 y 轴；
- 不同充电过程在同一子图内共享 y 轴；
- y 轴范围增加 5%-10% padding；
- 异常极端值可按 1%-99% 分位裁剪用于展示，但文本摘要中需要保留真实 min/max。

### 采样语义与绘制规则

每个充电过程通常 5/10 分钟推送一次数据点，功率可能是上个推送窗口内的平均值。
真实窗口内功率峰值可能高于这个平均值，因此不能简单把平均功率画成折线图或阶梯图。
电流可能更接近推送时刻的瞬时值，可以做二次插值平滑，以获得更直观的展示效果。

第一版绘制目标是尽量尊重采样语义，同时让客户能直观看到功率、电流的变化，并能用数值校验证明绘图没有改变总能量。

实现规则：

- `power_series` 不画折线图；
- `power_series` 不画阶梯图；
- `power_series` 使用面积保持重建曲线；
- `current_series` 使用二次插值平滑曲线；
- 原始采样点必须显示 marker，便于看出采样稀疏程度和插值依据；
- 点数 `< 2` 时只画散点，并在摘要中标注点数过少；
- 同一 process 的 power/current 使用同一个时间轴；
- 不同 process 共享同一个 x 轴范围。

#### 功率面积保持重建

功率数据按窗口平均值理解。第 `i` 个功率值 `p_i` 对应时间区间 `[t_i, t_{i+1}]` 上的平均功率。

先构造累计能量曲线：

```text
E_0 = 0
E_{i+1} = E_i + p_i * (t_{i+1} - t_i)
```

然后对累计能量点 `(t_i, E_i)` 做单调、形状保持插值，例如 PCHIP。
最终功率展示曲线取累计能量插值函数的导数：

```text
P_smooth(t) = dE_smooth(t) / dt
```

这个方法的关键性质：

- 曲线比阶梯图更直观；
- 每个采样区间的面积保持不变；
- `integral(P_smooth, t_i, t_{i+1}) == p_i * dt_i`；
- 不会把平均功率误画成两个点之间的线性变化；
- 可以通过面积误差自动测试验证。

实现要求：

- 优先使用 `scipy.interpolate.PchipInterpolator`；
- 如果环境没有 SciPy，先退化为“保存原始平均功率点 + 标注无法面积重建”，不允许偷偷改用折线或阶梯图；
- 重建后的功率若出现少量负值，按 0 截断，并在 manifest 里记录 warning；
- 截断后需要重新计算面积误差；
- 面积相对误差超过 `1e-3` 的 process 必须在 manifest 中记录 warning。

#### 电流二次插值平滑

电流数据第一版按采样时刻瞬时值处理。

绘制规则：

- 点数 `>= 3` 时使用二次插值；
- 点数 `< 3` 时只画原始点，不做二次插值；
- 插值曲线只用于可视化；
- 原始采样点必须保留 marker；
- 不外推到原始时间范围之外；
- 如果二次插值出现明显异常振荡，允许降级为 PCHIP，但必须在 manifest 中记录 warning。

如果后续确认电流也是窗口平均值，则电流也改成面积保持重建方式。

函数建议：

```text
build_time_axis(process, default_sample_minutes) -> list[float]
reconstruct_power_area_preserving(x, power) -> ReconstructedSeries
smooth_current_quadratic(x, current) -> ReconstructedSeries
validate_power_area(original_x, original_power, reconstructed_x, reconstructed_power) -> AreaValidationResult
```

测试要求：

- 对每个 process 计算原始窗口能量和重建曲线积分；
- 原始窗口能量：`sum(power_i * dt_i)`；
- 重建曲线积分：对 `reconstructed_power` 做数值积分；
- 相对误差 `<= 1e-3` 视为通过；
- 单测中至少构造一条常数功率、一条递增功率、一条先升后降功率样例；
- 图片预览 manifest 必须输出每块电池的最大面积相对误差。

### 图片预览与人工验收

图像生成必须先单独测试，不能直接接入模型后再判断图片是否合格。

新增独立预览命令：

```bash
python -m chargellm.vision.rendering \
  --data-path dataset/sft.json \
  --index 0 \
  --output-dir artifacts/vlm_demo/preview_images \
  --default-sample-minutes 10
```

批量预览：

```bash
python -m chargellm.vision.rendering \
  --data-path dataset/sft.json \
  --limit 10 \
  --output-dir artifacts/vlm_demo/preview_images \
  --default-sample-minutes 10
```

预览输出：

```text
artifacts/vlm_demo/preview_images/<battery_id>/summary.png
artifacts/vlm_demo/preview_images/manifest.jsonl
```

`manifest.jsonl` 每行记录：

```json
{
  "battery_id": "battery_001",
  "sample_index": 0,
  "image_path": "artifacts/vlm_demo/preview_images/battery_001/summary.png",
  "num_processes": 7,
  "max_duration_hours": 6.5,
  "default_sample_minutes": 10,
  "max_power_area_relative_error": 0.0004,
  "power_reconstruction_method": "pchip_cumulative_energy_derivative",
  "current_smoothing_method": "quadratic",
  "time_axis_source": "time_offset",
  "inserted_zero_offset": true,
  "warnings": []
}
```

人工验收检查项：

- 图片是否能清楚区分每次充电过程；
- x 轴是否是绝对小时数；
- power 是否为面积保持重建曲线，而不是折线图或阶梯图；
- manifest 中的 power 面积误差是否在阈值内；
- current 是否为二次插值平滑曲线；
- current 是否保留原始采样 marker；
- 图例中的 `process_id` 是否可读；
- 标题是否包含 `battery_id`；
- 5/10 分钟稀疏采样是否在图上可见；
- 异常点是否没有被过度平滑抹掉。

## 文本摘要规格

VLM 输入同时包含图片和统计摘要，降低模型对图像精确读数的依赖。

摘要示例：

```text
电池ID: battery_001
充电次数: 7
过程ID: p001, p002, p003, p004, p005, p006, p007
估计容量范围: 80-90%
最大充电时长: 6.5 小时
采样间隔: 默认 10 分钟
每次充电点数: p001=40, p002=42, p003=41
每次末端容量: p001=92.1, p002=90.5, p003=88.7
功率范围: min=0.0, max=8.9
电流范围: min=0.0, max=2.4
```

摘要不要包含真实 `label`，避免推理时泄漏答案。

## Prompt 模板

### System Prompt

```text
你是电池充电曲线诊断助手。你会看到同一块电池多次充电过程的功率和电流曲线图，以及统计摘要。
请根据曲线的稳定性、异常波动、充电时长、容量范围和多次充电之间的一致性，判断电池状态。
只输出一个严格合法的 JSON 对象，不要输出 Markdown，不要输出额外解释。
```

### User Prompt

```text
请判断这块电池的状态。

可选 label:
- 电池故障
- 电池老化
- 非标电池
- 正常

capacity_range 只能从以下值选择:
- 40-60%
- 60-80%
- 80-90%
- 90-100%
- 未知

判断参考:
- 电池故障: 单次或少数几次充电过程出现明显突变、异常波动、中断、尖峰或局部不连续。
- 电池老化: 多次充电过程呈现持续退化、容量下降、曲线漂移、充电时长变长或功率/电流响应逐步变差。
- 非标电池: 多次充电形态长期偏离标准模式，但不一定是突发故障。
- 正常: 多次充电过程整体稳定，没有明显异常或持续退化。

统计摘要:
{summary_text}

当前样本 process_id 列表:
{process_ids}

请输出 JSON，格式如下:
{
  "label": "...",
  "capacity_range": "...",
  "confidence": 0.0,
  "key_processes": ["..."],
  "reason": "..."
}
```

## 输出解析规则

解析优先级：

1. 直接 `json.loads(raw_output)`；
2. 失败时截取第一个 `{...}` 再解析；
3. 字段缺失时填默认值；
4. 字段值不合法时规整到允许集合；
5. 完全失败时返回兜底结果。

兜底结果：

```json
{
  "label": "正常",
  "capacity_range": "未知",
  "confidence": 0.0,
  "key_processes": [],
  "reason": "模型未返回可解析 JSON。"
}
```

规整规则：

- 未知 label -> `正常`，并降低 `confidence`；
- 未知 capacity_range -> `未知`；
- `confidence` clip 到 `[0, 1]`；
- `key_processes` 过滤掉不在当前样本中的 ID；
- `reason` 为空时填入简短兜底说明。

## VLM SFT 数据格式

SFT 数据转换脚本输出：

```text
dataset/vlm_sft.json
```

单条记录：

```json
{
  "battery_id": "battery_001",
  "images": [
    "artifacts/vlm_demo/images/battery_001/summary.png"
  ],
  "messages": [
    {
      "role": "system",
      "content": "你是电池充电曲线诊断助手..."
    },
    {
      "role": "user",
      "content": "请判断这块电池的状态..."
    },
    {
      "role": "assistant",
      "content": "{\"label\":\"电池老化\",\"capacity_range\":\"80-90%\",\"confidence\":0.8,\"key_processes\":[\"p006\",\"p007\"],\"reason\":\"多次充电过程末端容量下降，后续过程功率和电流响应变弱，符合老化特征。\"}"
    }
  ],
  "label": "电池老化",
  "capacity_range": "80-90%",
  "process_ids": ["p001", "p002", "p003", "p004", "p005", "p006", "p007"]
}
```

assistant 内容必须是 JSON 字符串。

如果原始样本 `reason` 为空，训练数据构建脚本生成简短默认 reason：

```text
模型根据多次充电过程的功率、电流、容量范围和曲线稳定性给出该诊断。
```

## VLM GRPO 数据格式

GRPO 数据转换脚本输出：

```text
dataset/vlm_grpo.json
```

单条记录：

```json
{
  "battery_id": "battery_001",
  "images": [
    "artifacts/vlm_demo/images/battery_001/summary.png"
  ],
  "messages": [
    {
      "role": "system",
      "content": "你是电池充电曲线诊断助手..."
    },
    {
      "role": "user",
      "content": "请判断这块电池的状态..."
    }
  ],
  "label": "电池老化",
  "capacity_range": "80-90%",
  "process_ids": ["p001", "p002", "p003", "p004", "p005", "p006", "p007"]
}
```

## GRPO Reward 第一版

只实现工程可验证 reward：

1. JSON 可解析；
2. 必需字段存在；
3. `label` 命中标注；
4. `capacity_range` 命中标注或工程估计区间；
5. `key_processes` 均来自当前样本；
6. `confidence` 在 `[0, 1]`；
7. 输出无 Markdown、无 JSON 外多余文本。

暂不做复杂语义 reward。

## 建议代码结构

新增独立模块，不改动现有 TS-Qwen 主链路：

```text
src/chargellm/vision/
  __init__.py
  rendering.py
  prompting.py
  schemas.py
  dataset_builders.py
  rewards.py
  infer_vlm.py
  train_sft_vlm.py
  train_grpo_vlm.py
```

新增测试：

```text
tests/test_vision_rendering.py
tests/test_vlm_prompting.py
tests/test_vlm_schemas.py
tests/test_vlm_dataset_builders.py
tests/test_vlm_rewards.py
```

## 并行工作拆分

以下拆分用于多个 agent 并行开发。每个 agent 只负责自己的文件范围，避免互相覆盖。

### Agent A: 图像渲染

负责文件：

```text
src/chargellm/vision/rendering.py
tests/test_vision_rendering.py
```

交付内容：

- `normalize_process_time_offset()`
- `build_time_axis()`
- `reconstruct_power_area_preserving()`
- `smooth_current_quadratic()`
- `validate_power_area()`
- `estimate_process_duration_hours()`
- `render_summary_image()`
- `render_battery_images()`
- 渲染预览 CLI：`python -m chargellm.vision.rendering`

验收标准：

- 给定 `BatterySample` 可以生成一张包含功率和电流的图片；
- 优先使用 `time_offset` 构造 x 轴；
- `time_offset` 不从 0 开始时会补 0；
- 补 0 时所有序列同步补齐；
- `time_offset` 异常会写入 manifest warning；
- x 轴使用小时；
- 不同 process 在同一 x 轴范围比较；
- power 使用面积保持重建曲线；
- power 不使用折线图或阶梯图；
- power 面积误差可计算、可写入 manifest；
- current 使用二次插值平滑；
- current 保留原始采样 marker；
- 支持运行时返回 PIL image；
- `save_images=True` 时可保存 PNG；
- 预览 CLI 能输出 `summary.png` 和 `manifest.jsonl`，供人工检查。

### Agent B: Schema、Prompt 与解析

负责文件：

```text
src/chargellm/vision/schemas.py
src/chargellm/vision/prompting.py
tests/test_vlm_schemas.py
tests/test_vlm_prompting.py
```

交付内容：

- `VlmDiagnosisOutput`
- `build_capacity_range()`
- `build_vlm_summary()`
- `build_vlm_messages()`
- `parse_vlm_output()`

验收标准：

- 输出 schema 可校验；
- 非法 JSON 可兜底；
- `key_processes` 会过滤到当前样本 process ID 集合；
- prompt 不泄漏真实 label。

### Agent C: 数据转换

负责文件：

```text
src/chargellm/vision/dataset_builders.py
tests/test_vlm_dataset_builders.py
```

交付内容：

- `build_vlm_sft_records()`
- `build_vlm_grpo_records()`
- CLI 参数用于生成 `dataset/vlm_sft.json` 和 `dataset/vlm_grpo.json`

依赖：

- Agent A 的渲染函数；
- Agent B 的 prompt 和容量区间函数。

验收标准：

- 能从 `dataset/sft.json` 生成 `dataset/vlm_sft.json`；
- 能从 `dataset/grpo.json` 生成 `dataset/vlm_grpo.json`；
- 图片路径存在；
- assistant completion 是合法 JSON 字符串。

### Agent D: Zero-shot Demo 推理

负责文件：

```text
src/chargellm/vision/infer_vlm.py
```

交付内容：

- 加载 Qwen3-VL；
- 支持单条和批量推理；
- 支持运行时绘图；
- 支持 `--save-images`；
- 输出 `predictions.jsonl`。

依赖：

- Agent A 的渲染函数；
- Agent B 的 prompt 和解析函数。

验收标准：

- `--index 0` 能跑通单条样本；
- `--limit N` 能保存 JSONL；
- 模型输出无法解析时仍返回兜底 JSON；
- 结果中包含 raw output 和 parsed output。

### Agent E: SFT 训练入口

负责文件：

```text
src/chargellm/vision/train_sft_vlm.py
```

交付内容：

- 加载 `dataset/vlm_sft.json`；
- 接 Qwen3-VL LoRA/QLoRA；
- 支持 smoke training 参数；
- 保存 adapter。

依赖：

- Agent C 的 SFT 数据。

验收标准：

- 1-5 条样本可跑 smoke training；
- 训练后可用于 `infer_vlm.py` 加载。

### Agent F: GRPO 入口与 Reward

负责文件：

```text
src/chargellm/vision/rewards.py
src/chargellm/vision/train_grpo_vlm.py
tests/test_vlm_rewards.py
```

交付内容：

- JSON reward；
- label reward；
- capacity_range reward；
- key_process reward；
- confidence reward；
- GRPO 训练入口。

依赖：

- Agent C 的 GRPO 数据；
- Agent E 的 SFT checkpoint。

验收标准：

- reward 单测通过；
- 可从 SFT checkpoint 启动小步 GRPO。

## 实施顺序

1. Agent A 和 Agent B 可以并行开始；
2. Agent A 必须先输出预览图片，由人工确认图片符合要求；
3. Agent D 等 Agent A/B 接口稳定且预览图片通过人工确认后开始；
4. Agent C 可在 Agent A/B 的最小接口完成后开始；
5. Agent E 等 Agent C 的 SFT 数据完成后开始；
6. Agent F 等 Agent C/E 完成后开始。

第一轮只要求完成 Agent A、B、D，形成可演示 zero-shot demo。

## Demo 验收标准

第一版 demo 必须满足：

- 从现有 JSON 数据读取一块电池；
- 真实数据存在 `time_offset` 时优先使用它作为时间轴；
- `time_offset` 不从 0 开始时，处理阶段自动补 0；
- 能独立运行图片预览命令；
- 预览图片经人工确认后再接入 Qwen3-VL；
- 运行时生成包含功率和电流曲线的图片；
- power 曲线使用面积保持重建，不画折线图或阶梯图；
- manifest 输出 power 面积误差，支持验证重建是否保持总能量；
- current 曲线使用二次插值平滑，并保留采样点 marker；
- 图片可选择保存，便于客户展示；
- Qwen3-VL 可以接收图片和文本摘要；
- 推理脚本输出合法 JSON 或兜底 JSON；
- 输出包含 `label`、`capacity_range`、`confidence`、`key_processes`、`reason`；
- 批量推理结果保存为 JSONL；
- 客户展示时可以同时展示曲线图和模型诊断结果。

## 暂不处理

以下内容暂时不做：

- GAF/GADF/RP 图像；
- 大规模消融实验；
- 精确容量回归；
- 论文式 benchmark；
- 多模型对比；
- 复杂语义 reward；
- 替换现有 TS-Qwen pipeline。

## 开放问题

1. 原始数据中的 `time_offset` 是否一定是分钟单位。
2. 当 `time_offset[0] != 0` 时，补 0 点的序列值是否使用第一个有效值，还是业务上有更合适的默认值。
3. `charge_capacity[-1]` 是否可以代表单次充电末端容量。
4. 客户展示时是否需要把 `voltage_series` 作为第三条曲线加入图中。
