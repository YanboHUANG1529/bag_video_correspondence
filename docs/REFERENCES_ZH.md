# 技术参考与复用边界

核对日期：2026-10-18。下列论文能力来自作者论文／官方项目；对袋子与当前数据的适用性判断属于本探索的技术推断，尚未完成袋子实验。代码版本与权重需要在实际引入时固定。

| 项目／来源状态 | 类型 | 已有能力 | 本项目如何使用 |
|---|---|---|---|
| [UniGarmentManip，CVPR2024论文](https://openaccess.thecvf.com/content/CVPR2024/html/Wu_UniGarmentManip_A_Unified_Framework_for_Category-Level_Garment_Manipulation_via_Dense_CVPR_2024_paper.html)；[官方代码](https://github.com/luhr2003/UniGarmentManip) | 方法 | 学习同类别衣物的结构与功能稠密对应，用少量示范指导操作 | 主要跨袋学习参考；需要袋子结构标签、材料对应与训练数据 |
| [DexGarmentLab，2025论文](https://arxiv.org/abs/2505.11032)；[GAM官方使用说明](https://github.com/wayrise/DexGarmentLab/blob/main/GAM_Usage.md) | 系统＋方法 | GAM将示范衣物点云上的操作点迁移到目标点云 | 参考描述子和操作点接口；公开封装使用预设示范点云，视频观测需额外对接 |
| [GarmentNets，ICCV2021官方项目](https://garmentnets.cs.columbia.edu/)；[代码](https://github.com/real-stanford/garmentnets) | 方法 | 在标准空间补全衣物形状，再映回观测空间并保留标准坐标标签 | 参考标准材料坐标学习；完整补全可留到局部方法不足时 |
| [GarmentTracking，CVPR2023官方项目](https://sites.google.com/view/garment-tracking)；[代码](https://github.com/xiaoxiaoxh/GarmentTracking) | 方法＋数据 | 从点云序列跟踪标准空间与任务空间的衣物状态 | 参考时序标准坐标；现有衣物数据不构成袋子测试集 |
| [Dense Object Nets，2018论文](https://arxiv.org/abs/1806.08756)；[代码](https://github.com/RobotLocomotion/pytorch-dense-correspondence) | 方法 | 学习稠密视觉描述子，展示形变物体上的位置抓取与类内迁移 | 描述子路线的基础参考；原环境较旧，首轮无需部署整套系统 |
| [Neural Non-Rigid Tracking，NeurIPS2020官方代码](https://github.com/DeformableFriends/NeuralTracking) | 方法 | RGB-D非刚性对应、对应置信度与变形图优化 | 参考可见表面跟踪和置信加权；不是直接接收任意袋Asset的现成插件 |
| [Trimesh NRICP官方文档](https://github.com/mikedh/trimesh/blob/main/docs/content/nricp.md) | 工具 | 非刚性ICP及源面／重心坐标形式的关键点约束 | 几何基线入口；语义、遮挡、材料侧与交叠处理需自行对接 |
| [CoTracker3官方代码](https://github.com/facebookresearch/co-tracker)；[2024预印本](https://arxiv.org/abs/2410.11831) | 方法／工具 | 视频点轨迹和可见性估计 | 先建立Asset对应，再传播视频材料点 |
| [SpaTrackerV2，ICCV2025官方代码](https://github.com/henry123-boy/SpaTrackerV2) | 方法／工具 | 三维点跟踪，提供RGB和RGB-D输入路径 | 仓库已有源码快照；需要核对实际调用的是跟踪器还是深度前端 |

局部结构坐标和关键点配准是本项目的起始工程路线；跨袋描述子／标准坐标预测是学习扩展。借用这些组件本身不构成已验证的新方法贡献。当前主要未知量是：袋子的多层表面、无纹理和把手结构差异下，局部材料约束是否足够稳定；由计划中的独立材料标注和跨袋测试回答。
