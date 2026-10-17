# 首轮标注指南

## 1. 标注顺序

先查看 `../outputs/bootstrap/contact_sheet.jpg` 与 `../data/derived/case00/rgb_native/`，再在Blender查看 `data/raw/assets/bag2/bag_2.obj`。首批选择active15、30、34、50、90，其他帧按可见性补充。

| 索引域 | 使用规则 |
|---|---|
| active | 本探索主索引0–102；所有新标注使用它 |
| source | 原视频索引，由frame_map查找；例如active30对应source192 |
| pretrim | 原137帧采样索引，active0对应pretrim18 |
| user-extracted | 历史35帧用户抽帧；本数据已记录active=3×local，读取该来源时才使用 |
| simulation factor | 历史值8是视频／模拟节奏参数，不用于换算以上视频索引 |

新标注像素统一使用原生1280×720的 `[x,y]`，原点左上角。旧518×294图中的点需要分别按1280/518、720/294转换并复核。历史30帧 `[684,308]` 已属于原生坐标，只是待审近似提示。

## 2. Asset语义分区

编辑 `data/annotations/assets/bag2_regions.json`：

1. 确认参考姿态下两片袋壁的身份。推荐 `wall_visible_reference` 与 `wall_opposite_reference`，用截图／几何定义说明，不能根据每帧图像左右重新命名。
2. 标注实际抓取所在袋口边带、把手连接区域、桥面及侧缝；每个part列出原始OBJ零基 `face_ids`。
3. 从 `data/derived/assets/bag2/mesh_audit.json` 查看边界候选。分叉处人工选择相邻链；不要直接把整个连通块当有序袋口环。
4. 为使用的chart记录边界链、起点、方向、参考宽度、坐标构造和单位。袋壁身份与材料内外侧分开标注。
5. 审核完成后将本文件 `review_status` 改为 `reviewed`，保留mesh SHA。未判断区域继续留空／pending。

在Blender中**不要先Merge by Distance、Triangulate或重新导出再把新面号写回旧文件**。如果工具改变索引，必须显式保存新旧面映射并切换到新指纹。也可在原始拓扑数组上用程序拾取三角面，避免不透明的导入／导出重排。

## 3. 关键点与可见性

模板为 `data/annotations/case00/landmarks.json`。每个landmark代表固定材料位置，在不同帧中的观测共享同一ID。

模板中的8个结构名只是待确认候选，不能假定每一帧都存在或可见。需要时替换为真实可辨认的缝线／角点／材料标记，并填写 `part_id`、`asset_anchor` 和各帧观测。

- `pixel_xy`：清楚可见时填原生像素；遮挡或出画面时留null。
- `visibility`：`visible`、`occluded`、`out_of_frame`或`unknown`；初始 `unreviewed` 表示尚未看过。
- `reviewed`：逐观测人工审核标志；点不可见也可以完成可见性审核。
- `asset_anchor`：遵循 `../schemas/anchor.schema.json`。`face_id`为原始OBJ零基面号，重心坐标和为1。
- `surface_side`：`inner`／`outer`；不能辨认时为`unknown`，执行抓取前需解决或保留多解。

初始化点应分布在实际目标区域附近，并提供二维／三维约束，避免全部共线。衣物轮廓上的最高点、最左点可能随着折叠更换材料身份；只有能持续辨识为同一材料位置的点才适合固定ID。

另外新增8–12个评估点或材料面片，在实验配置中明确 `initialization_ids` 和 `evaluation_ids` 且不重叠。用于优化的关键点误差不能当独立对应性能。

## 4. 抓取区域

编辑 `data/annotations/case00/contacts.json`。目前有左手active30和右手active90两个待审事件，资产锚点均未填。30帧保留历史像素／比例提示，`ground_truth=false`。

记录内容：哪只手、抓取部件、袋壁、内外侧或接触两侧、单层／多层、区域轮廓或材料面片、是否遮挡、参考帧及不确定范围。可以借助抓取前后帧确认材料区域，无法确认时保留候选区域或null。

`ground_truth`的升级需要独立可解释依据，例如可见材料标记、多视角或经人工确认的清楚结构。两张mask贴近、手模型最近点、邻域支持深度和物理仿真成功均不能单独证明视频接触点的精确材料真值。

## 5. 标注质量检查

先用叠图检查像素与分辨率，在Asset上渲染同一材料点和邻域；由第二次独立复核或另一位标注者确认关键点。保存分歧、区间和未确定的袋壁身份，避免把不确定区域压成一个精确点。

`python -B scripts/validate.py`检查已有点的像素范围、面号、网格指纹和重心坐标。它不判断人工选中的点是否真正对应，语义审核仍需可视化证据。
