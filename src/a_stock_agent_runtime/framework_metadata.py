#!/usr/bin/env python3
"""框架元数据：FrameworkMetadata dataclass + FrameworkRegistry 容器。

本模块是 checklist.py 框架配置的唯一数据来源，对 checklist.py/cache.py 零依赖——
不 import 任何会触发循环 import 的模块。checklist.py 在自己模块加载时把 6 个框架
的 FrameworkMetadata 实例逐个写进这里的 FRAMEWORK_REGISTRY 完成注册；cache.py 直接
读 FRAMEWORK_REGISTRY，不需要为了拿框架配置去 import checklist.py。

ChecklistDefinition/ChecklistItem 仍定义在 checklist.py，这里只在 TYPE_CHECKING
块里引用它们的名字做类型注解，运行时从不 import checklist——配合
`from __future__ import annotations`，注解本身是字符串，不会在模块加载时触发
真正的 import，因此不会形成循环。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from checklist import ChecklistDefinition, ChecklistItem


@dataclass(frozen=True)
class SkippedChecklistItem:
    label: str
    reason: str


@dataclass(frozen=True)
class FrameworkMetadata:
    key: str
    checklist_name: str
    subjective_items: list[str]
    skipped_items: list[SkippedChecklistItem]
    checklist_definitions: list["ChecklistDefinition"]
    custom_builder: Callable[[dict], "ChecklistItem"] | None = None
    # 持仓止损路径整合（计划二）字段：cache.py 的 infer_framework()/
    # get_stop_loss_pct() 读这3个字段做行业归类和止损系数查表，是真实
    # 生产数据源——改这里会直接影响 add-holding/portfolio-risk 的止损线。
    portfolio_label: str | None = None
    industry_keywords: tuple[str, ...] = ()
    stop_loss_pct: tuple[float, float] | None = None


FrameworkRegistry = dict[str, FrameworkMetadata]

FRAMEWORK_REGISTRY: FrameworkRegistry = {}
