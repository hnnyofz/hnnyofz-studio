# Avatar 图集与语义契约

本文件是 **FFA 当前64px头发适配器**，不是所有Avatar产品的通用参数。目标项目若改了头模、行列映射、锚点或使用拆分五官，先在真实运行时确认其适配方式；不要把这个profile强套进去。

## Scene → GPU

标准parts字典顺序为 `head`、`hair_front`、`hair_back`，据此生成结构ID 1、2、3。不要排序改写该字典。每个可见mesh必须且只能属于一个语义组，并声明在旋转根或固定根下。

`model.json` 的三角形流为每顶点8个float：world XYZ、world normal XYZ、UV。当前导出器按loop-triangle面法线输出；`chunk.part`固定1，不是前后发。`chunk.structure`是语义；low-parts PNG的 **G字节**保存其ID。纹理从packed PNG解码并翻转Y一次供WebGL上传。

8×8高采样先进行真实深度测试，再在64格内选可见语义，颜色／深度／法线来自同一获胜组件。完整pass保留头代理，hair-only只作诊断和受约束恢复。

## 136帧校准profile

画布64×64、正交尺度64、target Z26、导出画面偏移Y6。新造型在固定画布中调整位置，不能逐帧缩放或裁紧。

| track | 帧数／布局 | yaw（渲染器模型角） | pitch | 竖向比例 |
|---|---|---|---|---|
| front | 63，9列×7行 | `(4-col)*7` | 行表 | 1 |
| back | 63，9列×7行 | `180-(4-col)*7` | 行表反号 | 1 |
| speak_front | 5，5列×1行 | 339 | `[-5.5,-22,-14,-5.5,-22]` | `[1,1.2,1.1,1,1.2]` |
| speak_back | 5，5列×1行 | 194 | `[5.5,22,14,22,14]` | `[1,1.2,1.1,1.2,1.1]` |

标准pitch行表：`[-22,-16.5,-11,-5.5,0,7,10]`。少数历史发型曾用第6行5°，应由已批准profile显式声明，不偷偷改全批。说话拉伸围绕Z16：`z=16+(z-16)*verticalScale`，只应用一次。

人类“第1行第9列”是零基 `(0,8)`，即渲染模型yaw=-28°/332°、pitch=-22°。Avatar UI的 `lookAt({yaw:28,pitch:-22})` 对应相同格；UI输入与模型角不是同一符号约定。

未进行sprite后处理时，说话首相位对应普通front `(3,7)`、back `(3,6)`。后处理可能因真实头脸PNG轮廓不同导致少量像素差异；回归应先按记录还原对应修复，再比较三维姿态，不把这个合理差异当作“角度必须重新调整”。

每个GPU frame保存：

```text
track,row,col,yaw,pitch,verticalScale
beauty,parts,proxyParts,hairOnlyBeauty,hairOnlyParts
```

两个pass必须同一模型、相机、位移、竖向比例、色板、描边设置。不要用另一次渲染的hair-only混补新模型。

## 图集与合成顺序

| 目录 | rear文件 | front文件 | 尺寸 |
|---|---|---|---|
| front | slot010_HairRear.png | slot168_HairFront.png | 576×448 |
| back | slot177_HairRear.png | slot178_HairFront.png | 576×448 |
| speak_front | slot010_HairRear.png | slot168_HairFront.png | 320×64 |
| speak_back | slot177_HairRear.png | slot178_HairFront.png | 320×64 |

- 正面：rear → 项目真实head PNG → 真实face PNG → front。
- 背面：真实head PNG → rear → front。
- 五官说话目录是 `face/face_000/speak`，不是speak_front。
- 当前打包器要求标准 `head/head_000/{track}`、`face/face_000/{front,speak}` 参考；迁移别的项目时显式写adapter，缺文件就报告，不能用空白PNG假通过。

## 像素修复

默认恢复条件同时成立：proxy semantic=head1、真实head+face alpha=0、原front/rear都透明、hair-only中有语义2/3与实色。恢复原模型采样色，并保留其前／后语义。真实皮肤内的缺口不满足条件，要回三维或分层排查。

可选后层提升需实际深度证明语义3可见、与前层连接、避开face以及adapter中明确的耳/轮廓保护色。不能按某个固定肤色推断所有人的头。`--promote-visible-rear`需提供真实头的保护色；默认关闭，先看raw/parts/head对照。

`--cleanup-singletons`也是显式选项：只删真实头脸内的前层8连通孤立1px。尖刺、呆毛、外轮廓峰值、细带、耳轮廓不适用全图“去噪”。所有修复写入manifest，便于再导出与审阅。

## 缩略图

取front **零基row4 col6**（人类第5行第7列）；rear与front分别平移 `(-1,-5)`，中间合成 `hair_004/icon_hair_004.png` 灰色小人头。保持64×64，不使用纯正面 `(4,4)`，不烘入真实五官，不裁切后重新居中。

style至少含`id`和冻结 `.blend` 的`sourceSHA256`；建议含kind、外观name与实际头适配参数。GPU、export manifest与安装事务的SHA必须能串回同一真源。
