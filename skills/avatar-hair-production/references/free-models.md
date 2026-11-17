# 免费形状原型路线与额度边界

核查日期：2026-11-17。默认采用腾讯官方 Hugging Face **Hunyuan3D-2mv** 公共 Space。此路线曾在本项目以匿名方式成功生成三视图白模；本次核查只读取公开状态与 schema，没有生成、登录或消耗 GPU 额度。

## 默认：匿名 HF Space

- [官方 Space](https://huggingface.co/spaces/tencent/Hunyuan3D-2mv)
- [公开状态](https://huggingface.co/api/spaces/tencent/Hunyuan3D-2mv)、[Gradio config](https://tencent-hunyuan3d-2mv.hf.space/config)、[接口 schema](https://tencent-hunyuan3d-2mv.hf.space/info)
- 本次状态为公开、RUNNING，schema 中仍有 `/shape_generation` 及历史成功的13个输入字段。这只能证明接口信息可读，不能证明当前账号／访客还有生成额度。
- [HF ZeroGPU 官方说明](https://huggingface.co/docs/hub/en/spaces-zerogpu) 当前列匿名每日2分钟、免费登录账号5分钟；额度和排队规则可能变更。免费共享服务没有可用性、完成时间或无限次数保证。额度报错后按返回时间停止，勿持续重提。

脚本只依赖 Python 3.10+ 即可只读检查：

```bash
python scripts/hf_generate.py --inspect --out ./generation --timeout 60
```

`--inspect` 是默认模式，不执行生成函数。保存 `space.json`、`schema.json` 和 `inspection.json`。检查 schema 与当前支持的端点一致、确认本轮确实要消耗免费额度后，才显式运行：

```bash
python scripts/hf_generate.py --generate \
  --front ./inputs/front.png --right ./inputs/right.png --back ./inputs/back.png \
  --out ./generation --seed 1234 --timeout 300
```

仅生成模式需要 `gradio_client`。脚本明确使用匿名客户端，不读取本机登录状态作认证，也没有付费后备路线。每个输出目录只允许一次提交尝试；`submission-once.json` 已出现时，不再提交。超时表示停止观察，远端任务可能仍存在，不能换目录自动重提；此客户端流程没有保证可跨进程找回任务的持久句柄。拿到结果时先保存私有 `download-result.json` 再下载；下载失败时可检查同一个结果地址，不能重新生成。临时模型地址可能失效，该私有文件及整个作业目录不发布进团队 Skill 仓库。

输入为同一造型的正、右、背三张独立图。方向必须真实对应，不镜像凑图；保持比例、完整发梢，去掉文字和相邻视图碎片。可用纯背景补成方图，但不要把本项目768／820像素方图的习惯写成接口强制要求。脚本复制原输入并记录 SHA，保存固定参数及原始 `raw/model.glb`；校验真实网格后保存模型 SHA，并将原 GLB 设为只读。后续 Blender 编辑使用副本。

历史成功设置是形状端点：正／右／背输入，左图和文字／单图入口留空，5步、guidance 5、seed 1234、octree 256、chunks 8000、去背景开启、固定随机种子。脚本会重新检查字段和类型；schema、登录要求、额度或观察超时出现变化即停止，不自动循环重试。官方客户端用法见 [Gradio Python client](https://github.com/gradio-app/gradio/blob/main/client/python/README.md)。

## 免费形状不等于成品发型

`shape_generation` 得到几何原型，不能保证贴图、正确发色、自然头皮贴合、无灰脸／耳残留或可直接接入 Avatar。需要在 Blender 保留识别轮廓、清理源灰头、校准真实头形、处理侧根与后脑覆盖，再制作 UV／颜色并导出实际像素视图。下载成功和网格非空不等于美术验收。

## 可选备选

- **官方网页手动生成**：[Hunyuan3D Studio](https://3d.hunyuan.tencent.com/)。如当前匿名公共服务不可用，可由用户在网页中选择并下载原模型；网页登录、额度和价格按当时界面确认，不把网页权益当作公共 HF API 权益。已有成功原模型时直接进入 Blender，无需再生成。
- **本地 Hunyuan3D-2mv**：[官方模型卡](https://huggingface.co/tencent/Hunyuan3D-2mv)、[官方代码](https://github.com/Tencent-Hunyuan/Hunyuan3D-2)。模型卡提供 CUDA 多视图 pipeline；不占公共 Space 额度，但 GPU、电费／租机和部署成本并非免费，也须遵守模型许可证。该 Skill 的 HF 脚本不会自动安装或启动本地模型。
- **腾讯云／TokenHub 3.1**是显式选择的计费或体验额度备选，不能作为匿名默认。经典 HT 批历史实际使用了腾讯云专业版和积分账本，并非匿名免费 HF 3.1。[腾讯云专业版接口](https://cloud.tencent.com/document/api/1804/123447) 与 [TokenHub 原生接口](https://cloud.tencent.com/document/product/1823/137181) 是不同协议，不混用字段。当前 [新人体验包](https://cloud.tencent.com/document/product/1823/130053) 列一次性体验额度及有效期；是否可领取、扣费来源及后付费状态需由用户确认，不能承诺永久免费。此脚本不实现这两条路线，也不自动切换。
