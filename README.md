# Hnnyofz Studio

供团队设计师使用的 Codex Skill 仓库。每个 Skill 可以独立安装。

| Skill | 用途 | 目录 |
| --- | --- | --- |
| [chibi-pixel-studio](SKILL.md) | Q 版 3D 道具建模、模型与像素双窗预览 | 仓库根目录（保留原安装路径） |
| [avatar-hair-production](skills/avatar-hair-production/SKILL.md) | 发型描述、三视图、免费图生 3D、Blender 修整、多角度像素图集、Avatar Demo 接入 | `skills/avatar-hair-production/` |

## 安装 Skill

在仓库根目录运行，可分别安装或同时安装两款：

```sh
# Q 版道具 Skill：只复制自身资源，不嵌套安装其他 Skill。
mkdir -p ~/.codex/skills/chibi-pixel-studio
cp -R SKILL.md THIRD_PARTY_NOTICES.md agents assets references scripts ~/.codex/skills/chibi-pixel-studio/

# Avatar 发型 Skill
mkdir -p ~/.codex/skills
cp -R skills/avatar-hair-production ~/.codex/skills/
```

两款 Skill 的运行依赖不同，请分别查看各自的说明。

## Avatar 发型生产

使用时可以说：`使用 $avatar-hair-production，把这些发型参考做成 Avatar Demo 可以换装和说话的像素发型。`

从 [Skill 入口](skills/avatar-hair-production/SKILL.md) 开始；环境配置见 [setup.md](skills/avatar-hair-production/references/setup.md)。资源包包含 13 个命令脚本、可编辑的 Blender 标准头模、像素渲染器和 Demo 模板。免费图生 3D 使用公共服务，额度与可用性以服务实际响应为准。

流程为：发型描述 → 头部三视图 → 免费图生 3D 或手工建模 → Blender 修整与白模验证 → GPU 转像素 → 正反面与说话图集 → Avatar Demo → 视觉检查与交付。

## Chibi Pixel Studio

用于 Codex 的 Q 版 3D 道具建模 Skill，提供原始模型与实时像素 Shader 的同步双窗预览。

## 功能

- 圆润、紧凑的 Q 版造型，真实可旋转的三维几何。
- 每隔 45° 的视角按钮、自由拖动、缩放与显著位置的像素密度控制。
- 向外扩展的 1 像素描边、细部件保护和顶部直射地面投影。
- 暖纸界面与多套颜色材质预设，同步改变模型、像素色板与导出图片。
- 透明 PNG 与旋转序列 ZIP 导出。

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
