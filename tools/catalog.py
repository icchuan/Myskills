#!/usr/bin/env python3
"""技能仓库目录工具（只用标准库）。

    python tools/catalog.py verify          # 校验 skills.json 与磁盘一致、frontmatter 合法
    python tools/catalog.py render          # 用 skills.json 重写 README 里的技能目录表
    python tools/catalog.py find <关键词>   # 按名字/标签/用途/备注搜索
    python tools/catalog.py list            # 列出全部技能
    python tools/catalog.py check <目录>    # 单独体检一个技能目录（新增前用）
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog" / "skills.json"
README = ROOT / "README.md"
BEGIN = "<!-- BEGIN CATALOG -->"
END = "<!-- END CATALOG -->"

REQUIRED = ("name", "summary", "tags", "source", "version", "license")
KNOWN_FRONTMATTER_KEYS = {
    "name",
    "description",
    "license",
    "version",
    "metadata",
    "allowed-tools",
    "disable-model-invocation",
    "user-invocable",
}

# 一行 frontmatter 里，未加引号的纯文本值出现「冒号+空格」会让整个 YAML 解析失败。
SCALAR_LINE = re.compile(r"^(?P<key>[A-Za-z0-9_-]+):(?P<rest>\s+.*)$")


def out(text: str = "") -> None:
    print(text)


def load_catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def skill_dirs() -> list[Path]:
    return sorted(
        d
        for d in ROOT.iterdir()
        if d.is_dir()
        and (d / "SKILL.md").is_file()
        and not d.name.startswith((".", "_"))
    )


def read_frontmatter(skill_md: Path) -> str:
    """返回 frontmatter 正文（不含首尾 --- 行），不合法时抛 ValueError。"""
    text = skill_md.read_text(encoding="utf-8-sig", errors="replace")
    if not text.startswith("---"):
        raise ValueError("SKILL.md 第一行不是 ---，缺少 frontmatter")
    match = re.match(r"---\r?\n(.*?)\r?\n---[ \t]*(\r?\n|$)", text, re.S)
    if not match:
        raise ValueError("frontmatter 没有单独成行的闭合 ---")
    return match.group(1)


def frontmatter_field(frontmatter: str, key: str) -> str | None:
    """取顶层字段值；支持 "..." / '...' 引号和 > / | 块标量。"""
    lines = frontmatter.splitlines()
    for index, line in enumerate(lines):
        if line.startswith((key + ":", key + " :")):
            value = line[len(key) + 1 :].strip()
            if value[:1] in {">", "|"}:
                block: list[str] = []
                for follow in lines[index + 1 :]:
                    if follow.strip() and not follow.startswith((" ", "\t")):
                        break
                    block.append(follow.strip())
                return " ".join(part for part in block if part).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            return value
    return None


def check_skill_dir(directory: Path) -> tuple[list[str], list[str]]:
    """返回 (错误, 警告)。"""
    errors: list[str] = []
    warnings: list[str] = []
    skill_md = directory / "SKILL.md"

    try:
        frontmatter = read_frontmatter(skill_md)
    except ValueError as exc:
        return [f"{directory.name}: {exc}"], warnings

    name = frontmatter_field(frontmatter, "name")
    description = frontmatter_field(frontmatter, "description")

    if not name:
        errors.append(f"{directory.name}: frontmatter 缺少 name")
    elif name != directory.name:
        warnings.append(f"{directory.name}: frontmatter name={name!r} 与目录名不一致")
    elif not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
        warnings.append(f"{directory.name}: name 建议用 kebab-case 小写短横线")

    if not description:
        errors.append(f"{directory.name}: frontmatter 缺少 description")
    elif len(description) > 1024:
        warnings.append(
            f"{directory.name}: description {len(description)} 字符，超过 1024 可能被客户端截断"
        )

    for line in frontmatter.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indented = line[:1] in (" ", "\t")
        match = SCALAR_LINE.match(line.strip())
        if not match:
            continue
        key, rest = match.group("key"), match.group("rest").strip()
        if match.group("rest")[:1] not in (" ", "\t"):
            continue
        if not indented and key not in KNOWN_FRONTMATTER_KEYS:
            errors.append(
                f"{directory.name}: frontmatter 出现未知顶层键 {key!r}，多半是上一行值里的 "
                f"「冒号+空格」把它拆成了新键（YAML 会整段解析失败）"
            )
            continue
        if rest[:1] in "\"'|>":
            continue
        if ": " in rest:
            errors.append(
                f"{directory.name}: {key} 的值里含未加引号的「冒号+空格」，会让 YAML 解析失败；"
                f"整段值用双引号括起来即可"
            )

    nested_git = directory / ".git"
    if nested_git.exists():
        warnings.append(f"{directory.name}: 内含 .git，会变成嵌套仓库，建议发布时删掉")

    return errors, warnings


def cmd_check(args) -> int:
    directory = Path(args.path).resolve()
    if not (directory / "SKILL.md").is_file():
        out(f"[错误] {directory} 下没有 SKILL.md")
        return 1
    errors, warnings = check_skill_dir(directory)
    for message in errors:
        out(f"[错误] {message}")
    for message in warnings:
        out(f"[警告] {message}")
    if errors:
        return 1
    out(f"[通过] {directory.name}" + (f"（{len(warnings)} 条警告）" if warnings else ""))
    return 0


def cmd_verify(_args) -> int:
    catalog = load_catalog()
    entries = catalog.get("skills", [])
    errors: list[str] = []
    warnings: list[str] = []

    names: list[str] = []
    for entry in entries:
        name = entry.get("name", "")
        names.append(name)
        missing_fields = [field for field in REQUIRED if not entry.get(field)]
        if missing_fields:
            errors.append(f"{name or '<未命名>'}: skills.json 缺少字段 {', '.join(missing_fields)}")
        if entry.get("path") and entry["path"] != name:
            errors.append(f"{name}: path 应与 name 相同（当前 {entry['path']}）")
        source = entry.get("source") or {}
        if source and not str(source.get("url", "")).startswith("http"):
            errors.append(f"{name}: source.url 不是 http(s) 地址")
        summary = entry.get("summary") or ""
        if len(summary) > 90:
            warnings.append(f"{name}: summary {len(summary)} 字偏长，目录表会不好看")
        tags = entry.get("tags") or []
        if len(tags) < 2:
            warnings.append(f"{name}: tags 少于 2 个，以后不好找")

    duplicates = {name for name in names if names.count(name) > 1}
    if duplicates:
        errors.append(f"skills.json 有重复条目：{', '.join(sorted(duplicates))}")

    on_disk = {d.name: d for d in skill_dirs()}
    listed = set(names)
    for name in sorted(set(on_disk) - listed):
        errors.append(f"{name}: 目录存在但 skills.json 没登记（跑 tools/catalog.py check {name} 看看）")
    for name in sorted(listed - set(on_disk)):
        errors.append(f"{name}: skills.json 登记了但目录不存在")

    for name, directory in sorted(on_disk.items()):
        dir_errors, dir_warnings = check_skill_dir(directory)
        errors.extend(dir_errors)
        warnings.extend(dir_warnings)

    for message in warnings:
        out(f"[警告] {message}")
    for message in errors:
        out(f"[错误] {message}")
    out()
    out(f"技能 {len(entries)} 个，磁盘 {len(on_disk)} 个；错误 {len(errors)}，警告 {len(warnings)}")
    return 1 if errors else 0


def source_label(source: dict) -> str:
    url = str(source.get("url", "")).rstrip("/")
    if "github.com/" in url:
        parts = url.split("github.com/")[-1].split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
    return url


def render_table(catalog: dict) -> str:
    rows = [
        "| 技能 | 用途 | 标签 | 版本 | 许可 | 来源 |",
        "|---|---|---|---|---|---|",
    ]
    for entry in sorted(catalog.get("skills", []), key=lambda item: item["name"]):
        name = entry["name"]
        tags = " ".join(f"`{tag}`" for tag in entry.get("tags", [])[:4])
        source = entry.get("source") or {}
        label = source_label(source)
        rows.append(
            f"| [`{name}`]({entry.get('path', name)}/) "
            f"| {entry.get('summary', '')} "
            f"| {tags} "
            f"| {entry.get('version', '')} "
            f"| {entry.get('license', '')} "
            f"| [{label}]({source.get('url', '')}) |"
        )
    rows.append("")
    rows.append(f"共 {len(catalog.get('skills', []))} 个技能。")
    return "\n".join(rows)


def cmd_render(_args) -> int:
    catalog = load_catalog()
    text = README.read_text(encoding="utf-8")
    if BEGIN not in text or END not in text:
        out(f"[错误] README.md 里缺标记 {BEGIN} / {END}")
        return 1
    head, rest = text.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    new_text = f"{head}{BEGIN}\n{render_table(catalog)}\n{END}{tail}"
    if new_text == text:
        out("[未变] 目录表已是最新")
        return 0
    README.write_text(new_text, encoding="utf-8", newline="\n")
    out(f"[已更新] README 目录表（{len(catalog.get('skills', []))} 个技能）")
    return 0


def haystack(entry: dict) -> str:
    source = entry.get("source") or {}
    parts = [
        entry.get("name", ""),
        entry.get("summary", ""),
        entry.get("notes", ""),
        entry.get("license", ""),
        str(source.get("url", "")),
        " ".join(entry.get("tags", [])),
    ]
    return "\n".join(parts).lower()


def print_rows(entries: list[dict]) -> None:
    if not entries:
        out("没有匹配的技能。")
        return
    width = max(len(entry["name"]) for entry in entries)
    for entry in entries:
        out(f"{entry['name'].ljust(width)}  {entry.get('version', '').ljust(10)} {entry.get('summary', '')}")
        out(f"{' ' * width}  {' '.join('#' + tag for tag in entry.get('tags', []))}")
    out()
    out("链接到项目：")
    out(f"  pwsh -File {ROOT / 'link-skill.ps1'} -Skill <技能名> -Project <项目路径>")


def cmd_find(args) -> int:
    catalog = load_catalog()
    entries = catalog.get("skills", [])
    if not args.query:
        print_rows(sorted(entries, key=lambda item: item["name"]))
        return 0
    query = " ".join(args.query).lower()
    hits = [entry for entry in entries if query in haystack(entry)]
    print_rows(hits)
    return 0 if hits else 1


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    import argparse

    parser = argparse.ArgumentParser(description="agent-skills 目录工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("verify", help="校验目录元数据与磁盘内容").set_defaults(func=cmd_verify)
    subparsers.add_parser("render", help="重写 README 技能目录表").set_defaults(func=cmd_render)

    find_parser = subparsers.add_parser("find", help="按关键词搜索技能")
    find_parser.add_argument("query", nargs="*", help="关键词（名字/标签/用途/备注）")
    find_parser.set_defaults(func=cmd_find)

    list_parser = subparsers.add_parser("list", help="列出全部技能")
    list_parser.set_defaults(func=lambda _args: cmd_find(argparse.Namespace(query=[])))

    check_parser = subparsers.add_parser("check", help="体检单个技能目录")
    check_parser.add_argument("path")
    check_parser.set_defaults(func=cmd_check)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
