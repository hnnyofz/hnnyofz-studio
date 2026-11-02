# Chibi Pixel Studio

用于 Codex 的 Q 版 3D 道具建模 Skill，提供原始模型与实时像素 Shader 的同步双窗预览。

## 功能

- 圆润、紧凑的 Q 版造型，真实可旋转的三维几何。
- 每隔 45° 的视角按钮、自由拖动、缩放与显著位置的像素密度控制。
- 向外扩展的 1 像素描边、细部件保护和顶部直射地面投影。
- 暖纸界面与多套颜色材质预设，同步改变模型、像素色板与导出图片。
- 透明 PNG 与旋转序列 ZIP 导出。

## 安装

将整个仓库目录复制到 `~/.codex/skills/chibi-pixel-studio`，保留 `SKILL.md`、`assets`、`scripts`、`references` 和 `agents`。

使用时可以说：`用 chibi-pixel-studio 做一个 Q 版电视柜。`

## 创建可编辑项目

需要 Python 3、Node.js，以及支持 WebGL2 的浏览器。构建无需安装第三方依赖。

```sh
python3 scripts/create_project.py /absolute/path/to/my-prop
node /absolute/path/to/my-prop/build.mjs
```

编辑新项目的 `scene.mjs` 后重新构建。输出为自包含的 `dist/preview.html`，可离线打开。

材质预设是分层着色的颜色方案，不包含 PBR 金属度、粗糙度或程序木纹。地面投影由实际模型生成，不包含模型表面的自阴影。

## 验证

```sh
node scripts/test_geometry.mjs
```

建模规范见 [SKILL.md](SKILL.md)，渲染与材质约定见 [renderer.md](references/renderer.md)。

## 来源

造型流程与网页风格参考 [Colorfigures](https://april-zhu.com/colorfigures)。来源记录见 `references/provenance.json`，第三方版权与许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
