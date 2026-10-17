# 数据准备、采集与下载清单

## 1. 已放置的数据

本次从现有仓库实际复制了887个文件，共102,904,447字节。逐文件来源和SHA-256在 `../data/manifests/local_data_manifest.json`。这份清单是复制来源证明，不是材料对应标注。

| 本项目路径 | 实际内容 | 用途与注意事项 |
|---|---|---|
| `data/raw/case00/input_bundle/input.mp4` | 原始547帧、1280×720、约29.964 fps视频 | 按source索引恢复原生RGB；不是103帧active视频 |
| `data/raw/case00/input_bundle/native_depth_frames/` | 137张采样原生深度 | 预裁剪窗口的备份；不能逐编号直接配active RGB |
| `data/raw/case00/active/rgb_frames/` | 103张518×294 RGB | 与上游有效窗口一致 |
| `data/raw/case00/active/input.mp4` | 103帧、518×294、约7.491 fps | 有效窗口预览与现有示范标注背景 |
| `data/raw/case00/active/native_depth_frames/` | 103张1280×720 uint16深度 | 几何主输入；0无效、每单位0.001米 |
| `data/raw/case00/active/masks/` | 袋子103张、左手101张、右手91张 | 袋子与手的现有分割；不是逐点材料标签 |
| `data/raw/case00/active/calibration.json` | 原生内参、畸变、单位与注册说明 | 示例去畸变射线的来源；仍需物理精度复核 |
| `data/raw/case00/active/frame_map.json` | 每帧source/active/pretrim、RGB-D时间戳 | 唯一帧索引关联表 |
| `data/raw/case00/active/T_camera_world.npy` | 上游相机到桌面世界估计 | 不等同于机器人手眼标定 |
| `data/raw/case00/active/data/case_00_native_rgbd/hand_*` | 左右手各103个MANO网格和4×4位姿 | 近手区域／方向先验 |
| `data/raw/case00/active/annotations/` | 袋口轨迹、交互候选、候选任务标注 | 保留原 `needs_review`，不升级成接触或对应真值 |
| `data/raw/case00/user_annotations/` | 当前用户版动作label与rectify | 与上游早期label分开保留；其索引域为35帧用户抽帧 |
| `data/raw/case00/historical_review/` | 旧抓取区域JSON、任务JSON、复核叠图 | 像素、袋口比例和单层语义提示，均需新项目复核 |
| `data/raw/assets/bag1/`、`bag2/`、`bag3/` | 每个资产原始OBJ和XML | bag2为主线，bag1/3尚无本项目配对实拍 |
| `data/raw/provenance/` | 上游清单、旧工程较新资产身份审计与运行配置 | 解释不同文档版本的来源 |

原包上游清单覆盖其中872个文件，其余15个是本地资产、用户标注和来源资料，均核对复制前后的SHA。没有重新下载现有输入，也没有运行旧抓取流水线。

## 2. 已生成的派生数据

| 路径 | 内容 |
|---|---|
| `data/derived/case00/rgb_native/` | 从原视频按active→source表恢复的103张原生RGB |
| `data/derived/case00/frame_table.csv` | 统一索引与active相对时间 |
| `data/derived/case00/pointclouds/*.npz` | 12帧示例云：相机点、世界点、原生像素、RGB与内参 |
| `data/derived/assets/*/topology.npz` | 原始顶点、原始三角面、材料边、边界边和原始索引 |
| `data/derived/assets/*/mesh_audit.json` | 顶点／面数量、边界连通块、分叉顶点等 |
| `outputs/bootstrap/contact_sheet.jpg` | 12帧预览，叠加袋子mask供检查 |
| `outputs/bootstrap/bootstrap_report.json` | 环境、点云覆盖、mask缺失、RGB对照差异与几何假设 |
| `outputs/bootstrap/validation_report.json` | 复制哈希、帧覆盖、单位／投影回环和后续门槛 |

点云去掉已有手mask覆盖，且未填零深度；若该帧缺手mask，报告会标记遮挡过滤不完整。示例云全部暂标为不具备正式度量评估资格，等待物理标定与标注审核。

## 3. 需要人工补充：首轮必需

- [ ] **资产语义分区**：填写 `data/annotations/assets/bag2_regions.json`。确认哪片袋壁、哪段材料边、把手连接点、内外侧以及坐标方向。
- [ ] **初始化对应点**：填写 `data/annotations/case00/landmarks.json`。先复核15/30/34/50/90帧，选择有结构辨识力的材料点；模板未填坐标不代表该位置不可见。
- [ ] **独立评估点／区域**：新增不参与拟合的点／面片；分别记录精确点、区间或区域标签。
- [ ] **抓取语义**：复核 `contacts.json` 的左手30帧和右手90帧候选。记录抓的是袋口还是把手、哪片袋壁、夹一层还是多层。
- [ ] **缺手mask**：左手active `[23,31]`；右手 `[9,10,17,18,33,46,47,48,49,50,51,52]`。补标或确认不可见，不能把缺文件自动理解为全黑。
- [ ] **bag2局部边界**：复核顶点299、440、514、515、526、527附近的分叉，指定实际使用的袋口链。
- [ ] **几何精度**：核对相机注册、尺度和畸变。需要毫米级误差时，补一段已知尺寸标定板或可测量参照物的RGB-D。

现有视频足够开始可视化和初始化基线；精确、遮挡中的真实接触材料位置目前没有直接观测。邻域深度和MANO可用来提出候选，不作为被遮挡点的直接测量。

## 4. 需要额外采集：扩展时准备

### 同一袋子的形变测试

补录bag2的平放、部分打开、折叠／扭转等初态，每种至少两次独立录制。尽量在抓取前后停留，让袋口和把手清楚可见。每段建议15–30秒，保留原始RGB、原生深度、时间戳、K、畸变和相机姿态信息。

若要测真实材料误差，可在袋口／把手旁临时贴可识别材料标记，并保存无标记外观记录；标记随材料移动。遮挡点可用第二视角或多视角记录确认。另采无标记序列检查方法是否依赖标记外观。

### 跨袋测试与学习

首批建议3–5只结构可比较的实物袋子，每只3种初态、每种2次录制，形成18–30段探索数据。优先补bag1/3的配对实拍；现有OBJ本身不能替代真实采集。

每只袋子准备：测量或扫描Asset、单位与坐标轴说明、部件标签、参考材料坐标、OBJ/纹理及许可证来源。记录把手形式、开口结构、尺寸、材质与是否明显拉伸。不能共享结构的袋子归为单独类别或只评估共有部件。

按实物袋子与独立录制切分训练／验证／测试。当前case00是一个录制，35／103／137／547这些数量不代表多个数据集。

## 5. 需要安装或下载：按阶段执行

机器可读清单在 `../configs/downloads.json`。本轮没有下载新模型权重或外部大型数据集。

| 优先级 | 内容 | 当前情况 | 获取与放置 |
|---|---|---|---|
| P0 | NumPy、Pillow、OpenCV | 当前环境已可用，初始化已运行 | 新环境安装 `requirements-bootstrap.txt` |
| P1 | Blender | 未检查安装状态 | [官方下载安装](https://www.blender.org/download/)，用于Asset查看／材料面标注 |
| P2 | SciPy、Trimesh、rtree | 需在独立环境按需安装；当前默认Python未发现Trimesh | `requirements-registration.txt` |
| P3任选一个 | CoTracker3代码及权重 | 本探索未下载 | [官方仓库](https://github.com/facebookresearch/co-tracker)；代码放 `external/co-tracker`，权重缓存放 `weights/` |
| P3另一路 | SpaTrackerV2 | 原仓库有源码快照，源目录未发现权重；全局缓存未核查 | [官方仓库](https://github.com/henry123-boy/SpaTrackerV2)；固定代码版本后按Quick Start下载相应模型 |
| P4 | UniGarmentManip | 本探索未下载 | [官方仓库](https://github.com/luhr2003/UniGarmentManip)，放 `external/UniGarmentManip` |
| P4 | DexGarmentLab GAM | 本探索未下载 | [官方仓库](https://github.com/wayrise/DexGarmentLab)，放 `external/DexGarmentLab`；仅使用对应模块时先检查其依赖 |
| 可选 | GarmentNets／GarmentTracking数据与权重 | 未下载，非首轮前置条件 | 从[参考清单](REFERENCES_ZH.md)的官方入口获取；用于验证衣物方法，不替代袋子标签 |
| 按需 | SAM2／WiLoR重新推理依赖与权重 | 现有mask／MANO已复制 | 只有补分割、处理新录制或重跑手估计时再准备；模型缓存状态未核查 |
| P5 | MuJoCo／现有抓取工程环境 | 原仓库有实现与历史环境记录 | 接口阶段复用，当前数据初始化未验证模拟器或GPU |

### 可选源码下载命令

以下在探索目录执行，分别在需要的阶段选择；不要重复clone已经存在的目录：

```powershell
New-Item -ItemType Directory -Force external
git clone --depth 1 https://github.com/facebookresearch/co-tracker.git external/co-tracker
git clone --depth 1 https://github.com/luhr2003/UniGarmentManip.git external/UniGarmentManip
git clone --depth 1 https://github.com/wayrise/DexGarmentLab.git external/DexGarmentLab
```

下载后记录每个仓库的 `git rev-parse HEAD`、所用权重文件SHA-256、依赖版本和运行参数。不能在并非独立Git仓库的源码目录中，把父仓库的HEAD误记成第三方版本。

CoTracker3官方Quick Start提供 `torch.hub.load('facebookresearch/co-tracker', 'cotracker3_offline')` 加载方式，会取代码和检查点。执行前先在独立环境按[PyTorch官方安装入口](https://pytorch.org/get-started/locally/)匹配系统、CUDA与PyTorch，并设置项目自己的模型缓存目录。首轮不需要同时安装两个跟踪系统。

衣物项目的检查点用于其原始衣物任务。袋子类别需要对应数据和适配，不能仅下载衣物权重就认定已有跨袋映射能力。

## 6. 搬到独立项目时

完整复制本探索目录，包括被Git忽略的 `data/raw`。若只复制Git跟踪文件，原始输入不会随仓库搬走，需另行搬运或在原环境运行准备脚本。复制之后可独立运行bootstrap与validate，不依赖旧抓取工程的源码或机器人环境。

原始来源文件可能含采集机器的历史路径，作为原始证据原样保留在忽略目录；本探索新写配置和清单只使用相对路径。对外共享前按实际数据授权处理视频、相机标识和原始元数据。
