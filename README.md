# 袋子视频与数字资产的材料对应探索

目标：把人类视频里的袋子抓取区域，转换成数字 Asset 上可持续跟踪的材料锚点，供后续抓取生成使用。

本项目以已有 **case00 原生 RGB-D + bag2 测量资产** 为起点。先研究同一实物的局部非刚性对应，再扩展到不同袋子的结构与功能对应。当前完成了目录、计划、输入复制、数据检查和标注模板；对应求解、视频跟踪、模型训练与机器人验证列为后续阶段。

## 先读什么

| 文件 | 内容 |
|---|---|
| [完整计划](docs/PLAN_ZH.md) | 阶段、任务、依赖、验收、时间与资源建议 |
| [技术路线](docs/TECHNICAL_ROUTE_ZH.md) | 表示、映射关系、非刚性配准、时序跟踪、跨袋学习 |
| [数据准备与下载](docs/DATA_PREPARATION_ZH.md) | 已放入的数据、缺少的标注与采集、分阶段下载 |
| [标注指南](docs/ANNOTATION_GUIDE_ZH.md) | 先标哪几帧、怎么定义袋壁、如何记录材料锚点 |
| [参考项目](docs/REFERENCES_ZH.md) | 论文、官方代码、适用范围和迁移条件 |

## 已放入的内容

- `data/raw/`：887 个独立复制文件，共 102,904,447 字节，约 98.14 MiB。包括原视频、137 张采样深度、103 帧有效序列、袋子与手掩码、标定、MANO、bag1/2/3 OBJ/XML 和历史参考标注。
- `data/manifests/local_data_manifest.json`：逐文件来源、大小和 SHA-256；872 个文件另与上游清单核对。
- `data/derived/case00/rgb_native/`：按显式帧映射恢复的 103 张 1280×720 RGB。
- `data/derived/case00/frame_table.csv`：active/source/pretrim 索引与时间戳。
- `data/derived/case00/pointclouds/`：12 个关键帧的可见袋子表面点云，单位米，含相机／上游世界坐标及原生像素。
- `data/derived/assets/`：保留原始网格索引的拓扑数组与边界检查结果。
- `data/annotations/`：三个资产区域模板、视频关键点模板和抓取区域待审模板。
- `outputs/bootstrap/`：输入预览、准备报告与完整性检查。

原始输入不移动、不改写。`raw`、`derived` 和输出默认忽略于 Git。数据清单与待审标注模板可以版本管理。复制的是与对应探索有关的输入，不包含整套旧抓取实验和机器人缓存。

## 立即查看

打开 [关键帧预览](outputs/bootstrap/contact_sheet.jpg)，然后查看 [验证报告](outputs/bootstrap/validation_report.json)。预览中的绿色区域是已有袋子掩码，不是对应预测或接触真值。

在本目录执行：

```powershell
python -B scripts/validate.py
```

当前机器已有初始化依赖，已直接运行准备脚本。在新环境中可使用 Python 3.10/3.11：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-bootstrap.txt
.\.venv\Scripts\python.exe -B scripts/validate.py
```

重新从原仓库复制和重建派生数据：

```powershell
python -B scripts/prepare_data.py --dry-run
python -B scripts/prepare_data.py
python -B scripts/bootstrap.py
python -B scripts/validate.py
```

复制命令完成后再执行下一条。再次复制会复用哈希一致的文件，发现不同内容会停止。`bootstrap.py` 会刷新派生数据，保留已有人工标注文件。如果目录已移出原仓库，只有重新导入时需要 `prepare_data.py --source-root <原仓库路径>`；已复制的数据可独立检查和重建。

## 接下来第一件事

按[标注指南](docs/ANNOTATION_GUIDE_ZH.md)，先复核 active 15、30、34、50、90 帧，标注袋口附近的材料关键点及其资产位置。**现在最缺的是可靠对应标注和资产语义分区，首轮无需下载大型衣物数据集或训练权重。**

## Git 使用

本目录已是独立仓库（`main` 分支，无父仓库），只管理代码、文档、配置、标注模板与数据台账；`data/raw/`、`data/derived/`、`outputs/` 与归档包不进版本库。

日常流程：

```powershell
git status --short
git add -A
git diff --cached --stat   # 确认只动了自己想动的文件
git commit -m "feat: ..."
```

数据体的恢复顺序：解压归档包（或 `prepare_data.py` 重新导入）→ `bootstrap.py` → `validate.py`。任何时候都可以用 `git ls-files data/` 确认数据确实没有被误提交。
