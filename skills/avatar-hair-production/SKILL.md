---
name: avatar-hair-production
description: 从发型描述、头部三视图和免费公共图生3D路线，制作可编辑 Blender 发型、64px 多角度与说话图集，并接入 FARFAR AWAY Avatar Demo。用于团队发型资产新建、批量生产和贴头／分层／像素缺陷修复。
---

# Avatar 发型生产

交付可追溯、可编辑、能在真实 Avatar 里转头与说话的发型。三视图是设计依据，Blender 是几何真源；像素图来自同一真模型的深度渲染。原始生成网格、修整模型和最终贴图分别保存，不用示意图冒充模型效果。

## 开始与分流

先读取用户已有参考、模型及目标 Avatar 项目约定，确定外观名、发色、目标数量和当前阶段。已有可用成果就从该阶段继续；一次小修不要求重做三视图或重新生成模型。

- 新发型：描述／参考 → 一致三视图 → 免费形状生成或手工模型 → Blender 修整与材质 → 白模贴头验证 → 真模型像素预览 → 图集 → Avatar 网页与交付。
- 现有发型：先在同一角度对照实际头图、原模型和像素分层，定位最早出错的环节，再局部修改。
- 批量：先做一款代表样本确认造型与接入，再复用参数化流程。数量和阶段服从本次任务，不固定为100款或20款。

如果目标 Demo 或服务权限尚未明确，先完成不依赖它的设计和本地建模；不要猜测仓库、账号、付费权限或目标 ID。

## 分阶段资料与工具

按当前阶段阅读，避免一次加载全部实现。

| 阶段 | 说明 | 可执行入口 |
|---|---|---|
| 环境、项目位置 | [setup.md](references/setup.md) | `scripts/doctor.py` |
| 描述与一致三视图 | [brief-and-views.md](references/brief-and-views.md) | `scripts/prepare_views.py` |
| 免费模型与限额恢复 | [free-models.md](references/free-models.md) | `scripts/hf_generate.py` |
| Blender 清理、配色、贴头 | [blender-modeling.md](references/blender-modeling.md) | `scripts/init_project.py`、`scripts/split_hair.py` |
| 连续 3D／像素预览及导出 | [renderer-contract.md](references/renderer-contract.md) | `scripts/build_renderer.py`、`scripts/prepare_exporter.py`、`scripts/capture_atlas.py` |
| Avatar 图集与缩略图契约 | [avatar-contract.md](references/avatar-contract.md) | `scripts/package_atlas.py` |
| 接入可交互网页 | [demo-and-delivery.md](references/demo-and-delivery.md) | `scripts/install_demo.py`、`scripts/make_gallery.py`、`scripts/configure_demo.py` |
| 漏肤色、空气层、毛刺、背光排查 | [qa-and-repair.md](references/qa-and-repair.md) | 同姿态 raw／parts／head／hair-only 对照 |

`assets/hair-brief.example.json` 是需求示例；`assets/head-proxy.blend` 和配套 JSON 是本项目已校准的中性代理头与相机。目标项目的真实头脸 PNG、灰头图标和 Avatar 代码由该项目提供，不包含在 skill 里。脚本通过参数取路径，不依赖制作人的电脑或旧任务目录。

## 核心操作约束

1. **免费路线默认不带账号、不自动付费。** 先查看官方 Space/schema，再显式提交一次生成。限额、登录要求、协议变化或提交状态不明时保存状态并停止重发；可等待、手工建模或用已下载模型。腾讯云与 TokenHub 的体验积分／计费 API 是不同的可选分支，不能冒充匿名免费服务。三视图图像生成和本地算力也不因此自动免费。
2. **造型从整体比例和贴头关系判断。** 位移问题先整副移动；局部侧根缺失补真实贴头几何。双髻／双马尾可以横向宽，顶部高度仍参考批准的头部比例。自然刘海可以接触眼睛，不设置全角度零遮眼门槛。
3. **几何和变换只应用一次。** 重新从已移动的 `.blend` 导出后，不再叠加旧缓存的 `wholeHairDrop`。记录当前是 baked 几何还是 pending render transform，避免说话时二次拉伸／位移。
4. **前后发不是颜色分类。** 标准语义为 head=1、hair_front=2、hair_back=3；GPU parts PNG 的 G 字节是语义 ID。近侧贴头 cap 可明确归前层，即使部分坐标在 Y+；真深度仍阻挡远侧。
5. **保留64×64原生画布和锚点。** 不逐帧裁紧或单独缩放。标准为前／背各63帧、说话前／背各5帧，共136帧。当前图标使用人类第5行第7列，即零基 `(4,6)`，与灰头按 `(-1,-5)` 合成。
6. **hair-only 不是整脸覆盖层。** 仅在代理头误遮、真实头脸完全透明、原头发也透明的区域恢复有几何依据的发色。若缺口位于真实皮肤内，先检查局部模型覆盖和前后层，不能用远侧内壁涂脸。
7. **背面也从转过来的模型导出。** 固定世界光照并旋转模型，不用换到背面相机拍一张烘焙阴影就当同一光照。旧贴图有明暗时使用保留材质家族的法线补偿；无纹理新模型可用固定法线光照。不要给所有发型套同一灰色／深蓝补片。

## 最小验收与交付

在实际小人头上检查中立正面、左右转向、抬头两角、低头、背面及五个说话相位。**第1行第9列**是本项目上右角侧根问题的已知回归点，邻居和反方向也要看。根据变更范围选取检查，不为通过数字门槛改变已认可造型。

输出编辑模型与引用、原模 SHA、构建参数与版本、GPU／图集来源、8张分层图集和图标、安装备份／事务、实际 Demo 网页和简洁预览。汇报用外观名，原生像素等比例放在一起；PNG/GIF 从已安装素材合成，不重新生成插画。

接入只修改指定发型及必要 catalog／来源记录，保留其他人的未提交修改。按目标仓库要求运行检查；交付 MR 或部署只在本次请求包含相应动作时执行，不把调用 skill 当作任意发布权限。
