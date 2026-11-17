# 从模型导出到 Avatar 网页

以下路径均由本次工作目录和目标项目提供；`SKILL`指本skill目录，`PROJECT`指发型项目，`DEMO`指有团队访问权限的Avatar仓库。命令以已激活Python环境为例。

## 冻结与渲染

完成 Blender 清理、比例、贴头、分层及材质检查后，保存 `model/avatar.blend`，冻结文件哈希。以后改了源文件就重新冻结并构建新run：

```sh
python "$SKILL/scripts/freeze_source.py" --project "$PROJECT"
python "$SKILL/scripts/build_renderer.py" --project "$PROJECT" \
  --out "$PROJECT/runs/review-v001" --blender /path/to/blender
```

通过本地HTTP服务打开输出 `preview.html`，看左侧真3D／右侧像素。造型还不对就先回Blender，不直接把不合格视图安装进Demo。每个run用新目录；保留之前已认可版本，不靠字母排序猜真源。

```sh
python "$SKILL/scripts/prepare_exporter.py" \
  --run "$PROJECT/runs/review-v001" --style "$PROJECT/style.json" \
  --out "$PROJECT/exporter"
python "$SKILL/scripts/capture_atlas.py" \
  --exporter "$PROJECT/exporter" --out "$PROJECT/gpu.json"
```

捕获器只启动本地loopback服务和浏览器GPU，默认检查136唯一姿态、同源SHA、PNG类型和0°／360°一致性。Playwright Chromium不可用时安装它，或用 `--browser /path/to/chrome`；没有WebGL2时停止并说明，不改用图片轮播假充3D导出。

## 打包与真实头脸对齐

```sh
python "$SKILL/scripts/package_atlas.py" \
  --gpu "$PROJECT/gpu.json" --style "$PROJECT/style.json" \
  --avatar-assets "$DEMO/Assets" --out "$PROJECT/export"
```

输出8张分层图集、136原生头发帧、四类真实头脸合成对照、正确灰头图标及manifest。`--cleanup-singletons`和`--promote-visible-rear`只在对应缺陷已判定时启用，后者还需要style里明确的 `protectedEarColors`；不要把修复开关当通用美化滤镜。

## 安装与网页

先确认ID未被其他设计师占用。新建安装默认拒绝碰撞；明确替换同款时用 `--replace`，只替换该ID，不清空全目录：

```sh
python "$SKILL/scripts/install_demo.py" --export "$PROJECT/export" \
  --id hair_055 --demo-root "$DEMO" --dry-run
python "$SKILL/scripts/install_demo.py" --export "$PROJECT/export" \
  --id hair_055 --demo-root "$DEMO"
python "$SKILL/scripts/make_gallery.py" \
  --demo-root "$DEMO" --ids hair_055
```

安装器先校验manifest哈希、所有PNG、尺寸和icon姿态，再写指定款8 PNG+icon及其局部/父catalog。备份和事务位于目标项目 `.hair-production/transactions/`；出现写入错误会尝试还原。其他款素材、业务代码与Git暂存区不由脚本改写。

网页复用目标仓库 `index.ts` 导出的 Avatar／CanvasBackend，以及 `demo/demoAssets.ts` 的资源加载。不是另一套简化人物renderer。默认入口是 `/hair-production-gallery.html`，可多款并排，看正背、左右、抬头／低头、**右上第1行第9列**、说话单步和翻转；页面显示实际行列。摄像头不会启动。

在目标仓库按它自己的说明安装依赖并运行，例如：

```sh
cd "$DEMO"
pnpm install
python "$SKILL/scripts/configure_demo.py" --demo-root "$DEMO"
pnpm exec vite --config hair-production.vite.config.mjs --host 127.0.0.1
```

单独的config会把新gallery加入构建入口，并保留原入口、build插件和资源布局。它还避开已实测的 `vite-plugin-static-copy:serve` 拦截 `Assets/catalog.json?import&url`、返回JSON而非JS模块的问题；原项目配置不改写，开发服务直接使用原Assets目录。若目标项目不使用这套Vite配置，按其框架接入，不套用adapter。

需要可分发网页构建时，用 `pnpm exec vite build --config hair-production.vite.config.mjs`，构建结果包含gallery；本地预览可用 `pnpm exec vite preview --config hair-production.vite.config.mjs`。仅新增HTML而不加入原多页build入口，不能宣称生产构建已包含网页。

实际端口以输出为准。打开开发服务里的gallery路径，不能直接双击TS模块HTML。没有现成Avatar代码时先获取目标项目；本skill不把只会画几个PNG的页面称为完整Avatar Demo。

## 团队交付

- 原输入、原GLB与来源；记录免费服务实际成功还是仅检查schema。
- 完整与分区可打开Blender场景、UV/材质、场景adapter、源SHA。
- 确定run、GPU、8图集、图标、manifest与修复记录。
- 安装ID、事务/备份、网页启动方法和实际浏览器结果。
- 简洁正背汇报与必要GIF；外观名、共用视口、整数nearest放大，不重画素材。

如本次要求提交，遵守目标仓库的分支、检查、MR规范，只加入本次已确认文件。像素变更后刷新相关来源哈希和已维护预览；不把其他设计师的未提交改动一起stage。发布站点、合并MR和付费生成不是本skill的隐含权限。

## 安装本skill给另一位设计师

复制或解压整个 `avatar-hair-production/` 到该工具的skills目录（Codex通常为 `~/.codex/skills/`），保留scripts/assets/references/agents。可说：

> 使用 $avatar-hair-production，基于这些三视图，为我们的Avatar制作一款墨黑碎齐刘海。优先免费生成模型，接入已有Demo；允许自然刘海接触眼睛。

无需复制原作者的历史项目目录。需另外具备Blender、Python依赖、WebGL2浏览器和目标Avatar资产访问权限。
