# 使用指南

## 安装与更新

Release 包里的主 Skill 已内嵌封面资源。直接安装 `photo-story-magazine` 可以制作整刊；需要单独调用封面时再安装 `photo-magazine-cover`。

源码中两个目录各维护一份，需同时复制到同一个 Skill 根目录，或运行仓库的安装脚本。源码主 Skill 通过相邻目录读取封面指南；自包含发布包由打包器改写为内部引用。

```sh
python scripts/install_local.py
python scripts/install_local.py --skills-dir /path/to/your/skills
```

已有目录会备份到目标目录旁的 `backups/travelogue-editor/`。自定义附加文件会保留；不要在安装目录维护项目源代码，更新应回到本仓库。

## Python 环境

在仓库根目录创建虚拟环境：

```sh
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

macOS / Linux：

```sh
source .venv/bin/activate
python -m pip install -r requirements.txt
```

生成 PDF 所需的字体源已包含在主 Skill 内。Poppler 的 `pdftoppm` 用于预览；没有它时先生成 PDF，再用阅读器完成目视检查。

## 给助手的输入

提供照片目录、本期想讲的内容和已知经历；也可以授权助手自行策划。地点、人物和时间等事实越具体，编辑判断越有依据。不要将账户凭据或不愿公开的照片加入开源仓库。

首次制作先审阅相册与联系表，形成主题和逐跨页方案，实际渲染封面及代表跨页。已授权全权设计时，助手自行完成校准后继续，不增加重复确认。

## 技术自检

以下命令仅运行随包组件教学样张。在仓库根目录执行：

```sh
python skills/photo-story-magazine/scripts/prepare_fonts.py --out work/fonts-demo --text skills/photo-story-magazine/assets/specimens/specimen.json
python skills/photo-story-magazine/scripts/magazine_layout.py --plan skills/photo-story-magazine/assets/specimens/pilot.json --fonts work/fonts-demo/font-manifest.json --out work/technical-smoke --demo
```

需要预览时追加 `--preview`。正式制作应为本期新建 plan，正文定稿后重新生成相应字体子集；自检用子集不保证覆盖新一期文字。首次完整实例化可省略 `--text`。

## 单独制作封面

先查看[成品示例](../skills/photo-magazine-cover/references/visual-examples.md)，再根据本期照片填写配方。编译提示词示例：

```sh
python skills/photo-magazine-cover/scripts/build_cover_prompt.py --recipe skills/photo-magazine-cover/assets/examples/architecture-close.json --out work/cover-prompt.txt
```

这条命令只生成提示词。助手还要调用实际可用的图片工具或进行可编辑排字，并检查最终图像的中文、主体、局部对比和层次。不要把示例中的刊名与地点当作本期输入。
