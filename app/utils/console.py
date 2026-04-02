"""Terminal compatibility helpers with an optional rich dependency."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

try:
    from rich.console import Console as RichConsole
    from rich.panel import Panel as RichPanel
    from rich.table import Table as RichTable
    from rich.tree import Tree as RichTree

    Console = RichConsole
    Panel = RichPanel
    Table = RichTable
    Tree = RichTree
except ModuleNotFoundError:
    @dataclass
    class Panel:
        renderable: Any
        title: str = ""
        border_style: str = ""

        def __str__(self) -> str:
            header = f"[{self.title}]\n" if self.title else ""
            return f"{header}{self.renderable}"


    @dataclass
    class Table:
        title: str = ""
        columns: list[str] = field(default_factory=list)
        rows: list[list[str]] = field(default_factory=list)

        def add_column(self, name: str, justify: str = "left") -> None:
            _ = justify
            self.columns.append(name)

        def add_row(self, *values: object) -> None:
            self.rows.append([str(value) for value in values])

        def __str__(self) -> str:
            lines: list[str] = []
            if self.title:
                lines.append(f"[{self.title}]")
            if self.columns:
                lines.append(" | ".join(self.columns))
                lines.append("-+-".join("-" * len(column) for column in self.columns))
            for row in self.rows:
                lines.append(" | ".join(row))
            return "\n".join(lines)


    class Tree:
        def __init__(self, label: str) -> None:
            self.label = str(label)
            self.children: list[Tree] = []

        def add(self, label: object) -> "Tree":
            child = Tree(str(label))
            self.children.append(child)
            return child

        def _render(self, depth: int = 0) -> list[str]:
            prefix = "  " * depth
            lines = [f"{prefix}{self.label}"]
            for child in self.children:
                lines.extend(child._render(depth + 1))
            return lines

        def __str__(self) -> str:
            return "\n".join(self._render())


    class Console:
        def print(self, *objects: object, sep: str = " ", end: str = "\n") -> None:
            if not objects:
                print(end=end)
                return
            text = sep.join(str(item) for item in objects)
            print(text, end=end)

        def print_json(self, text: str) -> None:
            try:
                print(json.dumps(json.loads(text), indent=2, ensure_ascii=False))
            except json.JSONDecodeError:
                print(text)

        def rule(self, title: str = "") -> None:
            banner = f" {title} " if title else ""
            print(f"{'-' * 12}{banner}{'-' * 12}")
