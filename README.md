# agent-skills

我的技能库：所有 AI 工具共用的 Agent Skills 原件，一个技能一个目录，只存一份。

> 入口可以有很多个，原件永远只有一份。项目里只放指向这里的链接（junction），改一次原件，所有项目立即生效。

## 快速开始

在某个项目里启用技能：

```powershell
pwsh -File D:\AI\agent-skills\link-skill.ps1 -Skill <技能名> -Project <项目路径>
```

脚本会在项目的 `.agents\skills\<技能名>` 建一个 junction 指向这里。项目的 `.claude\skills`、`.codex\skills` 若也指向 `.agents\skills`，一次链接三个工具都能用。

不想链接、只想临时用一次，也可以直接让 AI 工具读这里的目录。

## 技能目录

<!-- BEGIN CATALOG -->
| 技能 | 用途 | 标签 | 版本 | 许可 | 来源 |
|---|---|---|---|---|---|
| [`ppt-master`](ppt-master/) | 从大纲/讲稿生成可编辑 PPTX 的完整工作流：SVG 分页、质量门、导出、可选配音 | `ppt` `pptx` `slides` `deck` | 6.7.3 | MIT | [hugohe3/ppt-master](https://github.com/hugohe3/ppt-master) |
| [`refactoring-ui`](refactoring-ui/) | Web UI 的规则书与诊断层：层级、间距、排版、配色对比度、阴影、空状态、设计 token | `ui` `design` `css` `tailwind` | 2026-08-21 | MIT | [edisonmbli/refactoring-ui-skill](https://github.com/edisonmbli/refactoring-ui-skill) |

共 2 个技能。
<!-- END CATALOG -->

## 找技能

```powershell
python tools/catalog.py list            # 全部技能
python tools/catalog.py find 配色        # 按名字/标签/用途/备注搜
python tools/catalog.py find ppt tailwind
```

## 新增一个技能

1. **放原件**：把技能目录复制到本仓库根目录，命名用 kebab-case（`<技能名>/SKILL.md`，大小写敏感，与 frontmatter 的 `name` 一致）。
2. **体检**：

   ```powershell
   python tools/catalog.py check <技能名>
   ```

   会检查 frontmatter 能否被 YAML 解析（含「冒号+空格」这类常见坑）、`name` 是否与目录名一致、`description` 是否过长。
3. **登记元数据**：在 [`catalog/skills.json`](catalog/skills.json) 的 `skills` 数组里加一条，必填 `name` / `path` / `summary` / `tags` / `source` / `version` / `license`，建议补 `requires` / `notes` / `added`。
4. **刷新目录表并校验**：

   ```powershell
   python tools/catalog.py render
   python tools/catalog.py verify
   ```

5. **提交**：`git add -A && git commit -m "add <技能名>"`。

## 更新 / 删除技能

- **更新**：删掉旧目录，把新版放进来（保持目录名不变），改 `skills.json` 里的 `version` / `source.upstreamVersion` / `notes`，然后 `render` + `verify`。项目里的 junction 指向同一路径，不用重建。
- **删除**：删目录、从 `skills.json` 移除条目、`render` + `verify`。记得同时删掉各项目 `.agents\skills\<技能名>` 里的 junction，否则会留下断链。

## 目录结构

```text
agent-skills/
├─ README.md              # 本文件（技能表由 tools/catalog.py render 生成）
├─ link-skill.ps1         # 把技能链接进某个项目
├─ catalog/skills.json    # 元数据单一来源：用途、标签、来源、版本、许可、依赖
├─ tools/catalog.py       # 校验 / 渲染目录表 / 搜索
├─ <技能名>/SKILL.md       # 技能本体
└─ <技能名>/scripts/...    # 技能自带的脚本、模板、参考资料（可选）
```

## 约定

- 目录名 = frontmatter 的 `name`，kebab-case。
- `SKILL.md` 的 frontmatter 必须是合法 YAML：值里出现「冒号+空格」时整段加双引号。
- 每个技能必须记清 `source`(来源 URL) 和 `license`；上游自带 `LICENSE` / `ATTRIBUTION` 的，一并放进技能目录。
- 单个技能超过 50 MB 或上万文件时，提交前先想清楚要不要进 git（可以考虑排除大体积模板，或在仓库外保留副本）。

## 运行环境

需要脚本的技能统一用 `D:\AI\python\python.exe`（Python 3.13.17，per-user 安装，已写入用户 PATH 最前面）：

```powershell
python  -V            # 3.13.17
python3 -V            # 同一个解释器，附带的 python3.exe 别名
```

已装依赖：PyYAML / python-pptx / XlsxWriter / skia-pathops（导入名 `pathops`）/ uharfbuzz / edge-tts / mammoth / markdownify / ebooklib / nbconvert / openpyxl / Pillow / numpy / requests / beautifulsoup4 / flask（对应 `ppt-master` 的 requirements.txt）。
未装 PyMuPDF（AGPL-3.0，只有 PDF→Markdown 才需要）、pandoc（`.docx/.html/.epub/.ipynb/.xlsx` 都有纯 Python 路径）。

装完或改过 PATH 后，已经开着的 AI 工具进程读到的还是旧环境变量，要重启该工具（或注销重登）才会直接认到 `python` / `python3`。

## 注意

- Windows 上不用软链接（要管理员权限），统一用 junction。
- git 会跟随 junction 把内容当普通目录提交，所以**项目里**被链接进来的技能目录不要提交（项目 `.gitignore` 已排除 `.agents/skills/*/`、`.claude/skills`、`.codex/skills`）。
- 沙箱里直接运行「工作区内」的 exe 可能启动不起来（表现为静默卡住），把安装包复制到工作区外再运行即可；创建指向工作区外的 junction 同样需要完全权限。
- 部分技能脚本会用 `mkdtemp` 建 0700 私有目录，沙箱受限身份下会报 `Permission denied`，需要完全权限或在普通终端执行。
