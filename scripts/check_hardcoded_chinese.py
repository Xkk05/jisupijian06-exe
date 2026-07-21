#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
扫描运行时代码中的中文字面量（AST级别）。

默认模式仅输出报告并返回 0；
传入 --strict 时，发现问题将返回 1。
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


HAN_RE = re.compile(r"[\u4e00-\u9fff]")


@dataclass
class Finding:
    path: Path
    lineno: int
    text: str


UI_METHODS = {
    "setText",
    "setWindowTitle",
    "setPlaceholderText",
    "setToolTip",
    "setStatusTip",
    "setTabText",
    "setTitle",
    "setSuffix",
    "addItem",
    "addItems",
}
MESSAGE_BOX_METHODS = {"information", "warning", "critical", "question", "about", "error"}
WIDGET_TEXT_CTORS = {
    "QLabel",
    "QPushButton",
    "QCheckBox",
    "QRadioButton",
    "QGroupBox",
    "QAction",
    "QMenu",
    "QLineEdit",
    "ModernButton",
    "ModernCard",
}
I18N_HELPERS = {"t", "translate_source_text", "enum_label"}
NON_UI_CALLS = {"print", "debug", "info", "warning", "error", "exception"}


def _iter_python_files(root: Path) -> Iterable[Path]:
    include_paths = [
        root / "ui",
        root / "processor",
        root / "config",
        root / "utils",
        root / "launch_application.py",
    ]
    for item in include_paths:
        if item.is_file() and item.suffix == ".py":
            yield item
            continue
        if item.is_dir():
            for file in item.rglob("*.py"):
                # 语言包/测试/备份目录不计入运行时代码检查
                rel = file.relative_to(root).as_posix()
                if rel.startswith("ui/i18n/"):
                    continue
                if "/tests/" in f"/{rel}/":
                    continue
                if "backup" in rel.lower():
                    continue
                yield file


def _call_name(call: ast.Call) -> Tuple[str, Optional[str]]:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id, None
    if isinstance(func, ast.Attribute):
        base = func.value.id if isinstance(func.value, ast.Name) else None
        return func.attr, base
    return "", None


def _build_parent_map(tree: ast.AST) -> Dict[ast.AST, ast.AST]:
    parents: Dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def _is_docstring(node: ast.Constant, parents: Dict[ast.AST, ast.AST]) -> bool:
    parent = parents.get(node)
    if not isinstance(parent, ast.Expr) or parent.value is not node:
        return False
    owner = parents.get(parent)
    if not isinstance(owner, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    return bool(owner.body) and owner.body[0] is parent


def _nearest_call(node: ast.AST, parents: Dict[ast.AST, ast.AST]) -> Optional[ast.Call]:
    cur = parents.get(node)
    while cur is not None:
        if isinstance(cur, ast.Call):
            return cur
        cur = parents.get(cur)
    return None


def _is_ui_visible_call(call: ast.Call) -> bool:
    name, base = _call_name(call)
    if name in I18N_HELPERS:
        return False
    if name in NON_UI_CALLS:
        return False
    if name in UI_METHODS:
        return True
    if name in MESSAGE_BOX_METHODS and base in {"QMessageBox", "ModernMessageBox"}:
        return True
    if name in WIDGET_TEXT_CTORS:
        return True
    return False


def _scan_file(path: Path, ui_only: bool = True) -> List[Finding]:
    findings: List[Finding] = []
    try:
        source = path.read_text(encoding="utf-8")
    except Exception:
        return findings

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return findings

    parents = _build_parent_map(tree)

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value.strip()
            if not value:
                continue
            if not HAN_RE.search(value):
                continue
            if _is_docstring(node, parents):
                continue

            if ui_only:
                call = _nearest_call(node, parents)
                if not call or not _is_ui_visible_call(call):
                    continue

            findings.append(
                Finding(
                    path=path,
                    lineno=getattr(node, "lineno", 0),
                    text=value.replace("\n", "\\n"),
                )
            )
    return findings


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strict",
        action="store_true",
        help="发现硬编码中文时返回非0",
    )
    parser.add_argument(
        "--all-literals",
        action="store_true",
        help="扫描所有字符串字面量（默认只检查可能用户可见的UI调用）。",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    findings: List[Finding] = []
    for file in _iter_python_files(root):
        findings.extend(_scan_file(file, ui_only=not args.all_literals))

    if findings:
        print(f"[check_hardcoded_chinese] found {len(findings)} entries:")
        for item in findings[:300]:
            rel = item.path.relative_to(root).as_posix()
            text = item.text
            if len(text) > 80:
                text = text[:77] + "..."
            print(f"  - {rel}:{item.lineno}: {text}")
        if len(findings) > 300:
            print(f"  ... truncated {len(findings) - 300} more")
    else:
        print("[check_hardcoded_chinese] no hardcoded Chinese literals found.")

    if args.strict and findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
