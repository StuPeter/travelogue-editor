# 开发与发布

## 唯一维护源

在 `skills/photo-story-magazine` 与 `skills/photo-magazine-cover` 修改源文件。主包内的嵌套封面由 `scripts/build_release.py` 生成，仓库不提交那份重复副本。

主 Skill 源码的相邻封面链接在组装时改写为内部链接，因此从仓库使用应安装两个目录，或使用自包含 Release 包。

## 本地检查

```sh
python -m pip install -r requirements-dev.txt
python scripts/check.py --test
```

检查引用、Skill 元数据、字体/图片哈希、自包含打包、封面配方和排版行为，以及更新安装的备份。字体测试在临时目录按真实测试文本准备子集，不依赖维护者的系统字体。

涉及视觉变化时，还要实际查看最终封面/跨页。程序检查、示例生成与独立模型整套 Skill 冷启动评估应分别记录。

## Git 更新流程

1. 为有明确范围的改动创建分支。
2. 更新相关 Skill、程序、案例或文档并完成相应检查。
3. 提交改动，合并到 main。
4. 需要本地使用时运行 `python scripts/install_local.py`。
5. 发布时更新 `project.json`、对应 Skill 的版本及 `CHANGELOG.md`，打标签后发布。

首次公开项目版本为2.1.0，内含主Skill 2.1.0与封面Skill 1.4.0。后续项目版本和组件版本可分别演进。

## 构建与发布

```sh
python scripts/build_release.py --out dist
```

构建生成完整版、平台轻量版、独立封面包、清单与SHA-256，已有同名产物不会覆盖。更新测试或重新构建时使用新输出目录。轻量版字体下载固定依赖公开的 v2.1.0 完整发布包及其哈希；维护后续版本时应保留该发布资产，或同步调整下载地址与校验值。

GitHub CI 在推送main及Pull Request时运行；以 `v*` 标签触发的发布工作流会再次检查、验证标签与项目版本一致，构建并上传到GitHub Release。推送前检查本次版本的变更记录。

构建、缓存、虚拟环境、用户素材与临时输出不进入Git。字体保留原许可；新增示例应附来源、生成属性和可复用的输入。
