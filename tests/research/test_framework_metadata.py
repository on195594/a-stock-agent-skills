"""framework_metadata.py 单元测试：纯数据结构，不依赖 checklist.py/cache.py。"""

import sys
from pathlib import Path

import pytest

from a_stock_agent_runtime import framework_metadata


def test_framework_registry_starts_empty_without_checklist_import():
    """framework_metadata.py本身不预置任何框架数据——registry是由checklist.py
    在自己加载时填充的。必须用子进程隔离验证，不能直接断言当前进程里的
    framework_metadata.FRAMEWORK_REGISTRY：同一个pytest进程会话里只要任何
    其他测试文件import了checklist（test_checklist.py就会），sys.modules缓存
    会让本文件看到的也是同一个已被填充过的模块级字典，不是"刚加载"的状态。"""
    import subprocess

    script = "from a_stock_agent_runtime import framework_metadata; assert framework_metadata.FRAMEWORK_REGISTRY == {}"
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(Path(__file__).resolve().parent.parent),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_skipped_checklist_item_holds_label_and_reason():
    item = framework_metadata.SkippedChecklistItem(label="测试项", reason="测试原因")
    assert item.label == "测试项"
    assert item.reason == "测试原因"


def test_framework_metadata_required_fields_and_defaults():
    metadata = framework_metadata.FrameworkMetadata(
        key="A",
        checklist_name="测试框架",
        subjective_items=["护城河"],
        skipped_items=[],
        checklist_definitions=[],
    )
    assert metadata.key == "A"
    assert metadata.custom_builder is None
    assert metadata.portfolio_label is None
    assert metadata.industry_keywords == ()
    assert metadata.stop_loss_pct is None


def test_framework_metadata_is_frozen():
    """frozen=True 只冻结字段绑定（不能重新赋值），不冻结 list 内容——
    这个测试只验证字段绑定层面的不可变，避免后续有人误以为整个对象深度不可变。"""
    metadata = framework_metadata.FrameworkMetadata(
        key="A",
        checklist_name="测试框架",
        subjective_items=[],
        skipped_items=[],
        checklist_definitions=[],
    )
    with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
        metadata.key = "B"
