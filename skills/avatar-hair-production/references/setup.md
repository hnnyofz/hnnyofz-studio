# 环境与目录

目标是把 skill 整个目录交给另一位设计师后，仍能从新工作目录执行；不要求存在历史 `tasks/2026-*` 或其他个人 skill。

## 依赖

- Python 3.10+；图像工具用 Pillow，自动 GPU 采集用 Playwright。
- Blender：本次实测 4.5.13 LTS。脚本应以 `--python-exit-code 1` 启动，让模型错误真正返回失败。
- 支持 WebGL2 的 Chromium/Chrome；Node 用于模板语法检查；Avatar Demo 使用其仓库指定的 Node/pnpm 版本。
- `gradio_client` 仅在提交免费公共模型任务时需要；只查 schema 不需要它。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install Pillow playwright gradio_client
.venv/bin/python -m playwright install chromium
.venv/bin/python "$SKILL/scripts/doctor.py" --blender /path/to/blender
```

先检查 `python3 --version`，确认是3.10+；macOS系统自带的3.9应换成已安装的新版Python再创建虚拟环境。

先把 `SKILL` 设为安装后的本 skill **绝对目录**。macOS Blender 常见位置为 `/Applications/Blender.app/Contents/MacOS/Blender`；Windows/Linux 使用自己的可执行文件路径。没有 Blender 时先完成描述、三视图与输入准备，不把其他渲染器伪装成已经编辑过的 Blender 模型。

目标 Avatar 项目须提供实际 Assets 和运行时代码。本次来源为团队 `skybox/avatar_demo`；用团队正常 Git 访问方式获取，不把凭据写入 skill。没有仓库权限时仍可交付 `.blend`、像素图和来源包，明确尚未接入真实 Avatar。

## 工作目录建议

```text
hair-project/
  brief.json
  references/three-views.png
  inputs/{front,right,back}.png
  generation/                 # 单次请求状态与原始 GLB
  source/raw.glb              # 不可覆盖的输入副本
  model/avatar.blend          # 完整头+发+相机的真场景
  model/hair-{whole,front,back}.blend
  realtime.json              # scene adapter、材质、语义、相机
  runs/review-v001/           # 一次确定构建，不猜“最新目录”
  exporter/
  gpu.json
  export/
  qa/
```

不要把上 GB 的模型 JSON、浏览器缓存、原始账号响应或用户隐私素材复制进 skill。生产资产放项目；skill 只携带通用工具、中性代理头和模板。打包前检查跨机器的绝对路径、失效 symlink 和未完成占位。

## 工具边界

图像生成可用当前环境可用的图像工具；用户指定工具时优先按指定选择。不是必须装 fal，也不因默认图像工具存在就把模型生成切到付费通道。网站不等于远程部署：本 skill 默认构建本地 Avatar 预览，公开上线另按任务范围执行。

## 本包验证范围

实测步骤与边界见 [validation.md](validation.md)。本包没有把历史生产模型、私有Avatar仓库或API凭据打包进去。
