#!/usr/bin/env python3
"""AI Terms Database 校验脚本（仅使用 Python 标准库）。

校验内容：
1. version.json / terms.json 可解析且字段完整；
2. terms_count 与实际词条数一致；
3. english_name 全局唯一（不区分大小写）；
4. difficulty 只能为 1/2/3；
5. application / related_terms 为非空字符串数组；
6. PR 场景下：修改 terms.json 必须同步修改 version.json 且版本号必须提升。

用法：
    python scripts/validate_terms.py
    python scripts/validate_terms.py --changed-files list.txt --base-sha <sha>
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

REQUIRED_FIELDS = (
    "english_name",
    "chinese_name",
    "category",
    "difficulty",
    "short_description",
    "detail_description",
    "application",
    "related_terms",
)
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
VALID_DIFFICULTY = {1, 2, 3}


def load_json(path: Path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AI Terms Database")
    parser.add_argument("--repo", default=".", help="repository root directory")
    parser.add_argument("--changed-files", default=None, help="file containing changed file paths (one per line)")
    parser.add_argument("--base-sha", default=None, help="base commit SHA for version-bump check")
    args = parser.parse_args()

    repo = Path(args.repo)
    errors: list[str] = []
    warnings: list[str] = []

    version_path = repo / "version.json"
    terms_path = repo / "terms.json"

    try:
        version = load_json(version_path)
        terms = load_json(terms_path)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: 无法解析 JSON 文件: {exc}")
        return 1

    # ---------- version.json ----------
    for key in ("version", "update_time", "description", "terms_count"):
        if key not in version:
            errors.append(f"version.json 缺少字段: {key}")

    version_str = str(version.get("version", ""))
    if not VERSION_RE.match(version_str):
        errors.append(f"version 格式应为 x.y.z（当前: {version_str!r}）")

    if not isinstance(version.get("terms_count"), int):
        errors.append(f"terms_count 必须是整数（当前: {version.get('terms_count')!r}）")
    elif version.get("terms_count") != len(terms):
        errors.append(
            f"terms_count={version.get('terms_count')} 与 terms.json 实际数量 {len(terms)} 不一致"
        )

    # ---------- terms.json ----------
    if not isinstance(terms, list):
        errors.append("terms.json 必须是 JSON 数组")
        _print_report(version, terms, errors, warnings)
        return 1

    seen_names: dict[str, str] = {}
    category_counter: Counter[str] = Counter()

    for index, term in enumerate(terms):
        label = f"第 {index + 1} 条"
        if not isinstance(term, dict):
            errors.append(f"{label}: 词条必须是 JSON 对象")
            continue

        english_name = term.get("english_name")
        missing = [k for k in REQUIRED_FIELDS if k not in term]
        if missing:
            errors.append(f"{label}（english_name={english_name!r}）: 缺少字段 {missing}")

        if not isinstance(english_name, str) or not english_name.strip():
            errors.append(f"{label}: english_name 必须是非空字符串")
            continue

        name_key = english_name.strip().lower()
        if name_key in seen_names:
            errors.append(
                f"english_name 重复（不区分大小写）: {english_name!r} 与 {seen_names[name_key]!r}"
            )
        else:
            seen_names[name_key] = english_name.strip()

        if not isinstance(term.get("chinese_name"), str) or not term["chinese_name"].strip():
            errors.append(f"{label}（{english_name}）: chinese_name 必须是非空字符串")

        if not isinstance(term.get("category"), str) or not term["category"].strip():
            errors.append(f"{label}（{english_name}）: category 必须是非空字符串")
        else:
            category_counter[term["category"]] += 1

        difficulty = term.get("difficulty")
        if isinstance(difficulty, str) and difficulty.isdigit():
            difficulty = int(difficulty)
        if not isinstance(difficulty, int) or difficulty not in VALID_DIFFICULTY:
            errors.append(f"{label}（{english_name}）: difficulty 必须为 1/2/3（当前: {difficulty!r}）")

        if not isinstance(term.get("short_description"), str) or len(term["short_description"].strip()) < 5:
            errors.append(f"{label}（{english_name}）: short_description 必须是非空字符串（建议 1~2 句）")

        if not isinstance(term.get("detail_description"), str) or len(term["detail_description"].strip()) < 20:
            errors.append(f"{label}（{english_name}）: detail_description 必须是非空字符串（建议 3~5 句）")

        for field in ("application", "related_terms"):
            value = term.get(field)
            if not isinstance(value, list) or len(value) < 1:
                errors.append(f"{label}（{english_name}）: {field} 必须是非空字符串数组")
            elif not all(isinstance(item, str) and item.strip() for item in value):
                errors.append(f"{label}（{english_name}）: {field} 中的每一项都必须是非空字符串")

    # 全部词条扫描完成后，再检查 related_terms 引用是否收录（避免把数组靠后的词条误判为缺失）
    if isinstance(terms, list):
        for index, term in enumerate(terms):
            if not isinstance(term, dict):
                continue
            english_name = str(term.get("english_name", "")).strip()
            related = term.get("related_terms")
            if not isinstance(related, list):
                continue
            for item in related:
                if isinstance(item, str) and item.strip().lower() not in seen_names:
                    warnings.append(
                        f"第 {index + 1} 条（{english_name}）: related_terms 中的 {item!r} 暂未收录在词库中"
                    )

    # ---------- PR 增量检查 ----------
    if args.changed_files:
        changed_path = Path(args.changed_files)
        changed = set()
        if changed_path.exists():
            changed = {
                line.strip().lstrip("\ufeff").replace("\\", "/")
                for line in changed_path.read_text(encoding="utf-8").splitlines()
                if line.strip().lstrip("\ufeff")
            }

        terms_changed = "terms.json" in changed
        version_changed = "version.json" in changed
        if terms_changed and not version_changed:
            errors.append(
                "修改了 terms.json 但未修改 version.json：必须同步提升 version，并更新 update_time / terms_count"
            )
        if version_changed and args.base_sha:
            result = subprocess.run(
                ["git", "show", f"{args.base_sha}:version.json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=str(repo),
            )
            if result.returncode == 0:
                try:
                    base_version = json.loads(result.stdout).get("version")
                    if base_version == version.get("version"):
                        errors.append(
                            f"version.json 的 version 未变化（仍为 {base_version}）：每次发布必须提升版本号"
                        )
                except json.JSONDecodeError:
                    warnings.append("无法解析基线 version.json，跳过版本提升检查")
            else:
                warnings.append("无法读取基线 version.json，跳过版本提升检查")

    # ---------- 报告 ----------
    _print_report(version, terms, errors, warnings, category_counter)
    return 0 if not errors else 1


def _print_report(
    version: dict,
    terms: list,
    errors: list[str],
    warnings: list[str],
    category_counter: Counter | None = None,
) -> None:
    print("=" * 48)
    print("AI Terms Database 校验报告")
    print("=" * 48)
    if isinstance(version, dict):
        print(f"version       : {version.get('version', 'N/A')}")
        print(f"update_time   : {version.get('update_time', 'N/A')}")
        print(f"terms_count   : {version.get('terms_count', 'N/A')}")
    print(f"实际词条数量 : {len(terms) if isinstance(terms, list) else 'N/A'}")
    if category_counter:
        print(f"分类数量     : {len(category_counter)}")
        for category, count in category_counter.most_common():
            print(f"  - {category}: {count}")
    if warnings:
        print(f"\n警告（{len(warnings)}）:")
        for warning in warnings[:50]:
            print(f"  ! {warning}")
        if len(warnings) > 50:
            print(f"  …（其余 {len(warnings) - 50} 条警告省略）")
    if errors:
        print(f"\n错误（{len(errors)}）:")
        for error in errors:
            print(f"  x {error}")
        print("\n校验未通过")
    else:
        print("\n校验通过")


if __name__ == "__main__":
    sys.exit(main())
