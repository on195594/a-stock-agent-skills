#!/usr/bin/env python3
"""框架客观指标核对清单。

本模块只展示客观指标达标情况，不计算也不输出加总总分。
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from a_stock_agent_runtime import cache
from a_stock_agent_runtime import framework_metadata
from a_stock_agent_runtime.framework_metadata import FrameworkMetadata, SkippedChecklistItem


@dataclass(frozen=True)
class ChecklistItem:
    key: str
    label: str
    raw_value: float | None
    unit: str
    direction: str  # 'higher_better' 或 'lower_better'
    excellent_threshold: float | None
    pass_threshold: float | None
    result: str  # '达优'/'达格'/'未达'/'数据缺失'
    data_status: str  # '完整'/'简化判定（不判断趋势/连续性）'/'缺失'
    note: str | None = None


@dataclass(frozen=True)
class ChecklistDefinition:
    key: str
    label: str
    unit: str
    direction: str
    excellent_threshold: float | None
    pass_threshold: float | None
    note: str | None = None
    trend_unverified: bool = False


class ChecklistError(Exception):
    """Checklist 构建失败的基类异常。"""


class UnsupportedFrameworkError(ChecklistError, ValueError):
    """请求了当前 checklist 工具尚未支持的框架。"""


class FundamentalsCacheMissingError(ChecklistError, LookupError):
    """指定股票没有可用的基本面缓存。"""


def _to_float_or_none(value: object) -> float | None:
    if value is None or value == '':
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    try:
        parsed = float(value)
    except (ValueError, OverflowError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _evaluate_result(
    value: float,
    direction: str,
    excellent_threshold: float | None,
    pass_threshold: float | None,
) -> str:
    if excellent_threshold is None and pass_threshold is None:
        raise ValueError('excellent_threshold/pass_threshold 不能同时为空')

    if direction == 'higher_better':
        if excellent_threshold is not None and value >= excellent_threshold:
            return '达优'
        if pass_threshold is not None and value >= pass_threshold:
            return '达格'
        return '未达'

    if direction == 'lower_better':
        if excellent_threshold is not None and value <= excellent_threshold:
            return '达优'
        if pass_threshold is not None and value <= pass_threshold:
            return '达格'
        return '未达'

    raise ValueError(f'未知 direction: {direction!r}')


def _build_item(definition: ChecklistDefinition, value: object) -> ChecklistItem:
    raw_value = _to_float_or_none(value)
    if raw_value is None:
        return ChecklistItem(
            key=definition.key,
            label=definition.label,
            raw_value=None,
            unit=definition.unit,
            direction=definition.direction,
            excellent_threshold=definition.excellent_threshold,
            pass_threshold=definition.pass_threshold,
            result='数据缺失',
            data_status='缺失',
            note=definition.note,
        )

    data_status = '简化判定（不判断趋势/连续性）' if definition.trend_unverified else '完整'
    return ChecklistItem(
        key=definition.key,
        label=definition.label,
        raw_value=raw_value,
        unit=definition.unit,
        direction=definition.direction,
        excellent_threshold=definition.excellent_threshold,
        pass_threshold=definition.pass_threshold,
        result=_evaluate_result(
            raw_value,
            definition.direction,
            definition.excellent_threshold,
            definition.pass_threshold,
        ),
        data_status=data_status,
        note=definition.note,
    )


def _build_f_operating_cf_quality_item(fundamentals: dict) -> ChecklistItem:
    operating_cf_per_share = _to_float_or_none(fundamentals.get('operating_cf_per_share'))
    eps = _to_float_or_none(fundamentals.get('eps'))
    note = '优档需要FCF（经营现金流-资本支出）连续多年数据，cache未采集，代码仅用经营现金流/EPS近似核对格档（经营CF/净利润>0.8）；净利润为负或零时该比值方法不适用（两个负数相除会反转符号），直接判数据缺失'
    if operating_cf_per_share is None or eps is None or eps <= 0:
        return ChecklistItem(
            key='operating_cf_to_net_profit',
            label='经营现金流质量（经营CF/净利润）',
            raw_value=None,
            unit='倍',
            direction='higher_better',
            excellent_threshold=None,
            pass_threshold=0.8,
            result='数据缺失',
            data_status='缺失',
            note=note,
        )

    ratio = operating_cf_per_share / eps
    return ChecklistItem(
        key='operating_cf_to_net_profit',
        label='经营现金流质量（经营CF/净利润）',
        raw_value=ratio,
        unit='倍',
        direction='higher_better',
        excellent_threshold=None,
        pass_threshold=0.8,
        result=_evaluate_result(ratio, 'higher_better', None, 0.8),
        data_status='简化判定（不判断趋势/连续性）',
        note=note,
    )


def _build_c_payout_ratio_item(fundamentals: dict) -> ChecklistItem:
    dps = _to_float_or_none(fundamentals.get('dps'))
    eps = _to_float_or_none(fundamentals.get('eps'))
    note = '派息率<40%时C框架股息率主估值轴不适用（利润主要再投资而非分配）：须改用 frameworks/C.md「成长型资源股分支」——基本面前瞻股息率15分→5分并新增产量·储量成长兑现度10分，择时主估值轴改用PB历史分位；≥40%时沿用成熟资源股原权重。eps≤0时派息率无经济意义，按成熟分支处理。判据要求 dps 与 eps 同为最近完整财年口径'
    # dps<0 只可能来自 cache.py set 手工写入的 JSON（系统边界）；fetcher 侧
    # compute_dividend_yield 已过滤非正派息，恒产出正值。负派息率会算出负比率
    # 并因 <40% 被误路由进成长型分支，故一并按数据缺失处理。
    if dps is None or eps is None or eps <= 0 or dps < 0:
        return ChecklistItem(
            key='payout_ratio',
            label='派息率（≥40%=成熟分支 / <40%=成长分支）',
            raw_value=None,
            unit='%',
            direction='higher_better',
            excellent_threshold=None,
            pass_threshold=40,
            result='数据缺失',
            data_status='缺失',
            note=note,
        )

    ratio = dps / eps * 100
    return ChecklistItem(
        key='payout_ratio',
        label='派息率（≥40%=成熟分支 / <40%=成长分支）',
        raw_value=ratio,
        unit='%',
        direction='higher_better',
        excellent_threshold=None,
        pass_threshold=40,
        result=_evaluate_result(ratio, 'higher_better', None, 40),
        data_status='完整',
        note=note,
    )


def _register(metadata: FrameworkMetadata) -> FrameworkMetadata:
    """把框架元数据写进 framework_metadata.FRAMEWORK_REGISTRY，并原样返回——
    返回值赋给下面的 _FRAMEWORK_X 变量只是为了让构造意图在代码里看得清楚，
    真正被其他代码读取的数据来源始终是 FRAMEWORK_REGISTRY 本身。"""
    framework_metadata.FRAMEWORK_REGISTRY[metadata.key] = metadata
    return metadata


_FRAMEWORK_A = _register(FrameworkMetadata(
    key='A',
    checklist_name='A通用框架',
    subjective_items=['护城河', '行业地位'],
    skipped_items=[],
    checklist_definitions=[
        ChecklistDefinition('roe_3y_avg', 'ROE近3年均值', '%', 'higher_better', 15, 10),
        ChecklistDefinition('net_profit_growth', '净利润增速近3年', '%', 'higher_better', 15, 8),
        ChecklistDefinition('debt_ratio', '资产负债率', '%', 'lower_better', 40, 60),
        ChecklistDefinition(
            'gross_margin',
            '毛利率',
            '%',
            'higher_better',
            30,
            None,
            '达优档要求的"稳定"/格档"无明显下滑"代码不做验证，仅核对当期数值是否过线，趋势需人工结合历史数据复核；'
            '格档本身无数值线（"无明显下滑"是质性判断），"未达"只代表未过30%优档线，不代表完全不及格',
            True,
        ),
    ],
    portfolio_label='A通用',
))

_FRAMEWORK_B = _register(FrameworkMetadata(
    key='B',
    checklist_name='银行框架',
    subjective_items=['护城河', '行业地位'],
    skipped_items=[
        SkippedChecklistItem(
            label='净息差趋势',
            reason='数据缺口：该字段无AKShare API，需人工检索公开来源后手动写入缓存'
            '（fetcher.py FIELDS注册表标注来源为web），核验对象与核验来源同源，不构成独立校验；'
            '权重不变，仍需结合公开来源人工评分',
        ),
        SkippedChecklistItem(
            label='不良贷款率',
            reason='数据缺口：该字段无AKShare API，需人工检索公开来源后手动写入缓存'
            '（fetcher.py FIELDS注册表标注来源为web），核验对象与核验来源同源，不构成独立校验；'
            '权重不变，仍需结合公开来源人工评分',
        ),
        SkippedChecklistItem(
            label='拨备覆盖率',
            reason='数据缺口：该字段无AKShare API，需人工检索公开来源后手动写入缓存'
            '（fetcher.py FIELDS注册表标注来源为web），核验对象与核验来源同源，不构成独立校验；'
            '权重不变，仍需结合公开来源人工评分',
        ),
    ],
    checklist_definitions=[
        ChecklistDefinition('roe_3y_avg', 'ROE加权年化', '%', 'higher_better', 13, 9),
    ],
    portfolio_label='B银行',
    industry_keywords=('银行',),
    stop_loss_pct=(0.88, 0.82),
))

_FRAMEWORK_C = _register(FrameworkMetadata(
    key='C',
    checklist_name='能源/资源框架',
    subjective_items=['储量竞争力', '行业地位'],
    skipped_items=[
        SkippedChecklistItem(
            label='前瞻股息率（压力测试后）',
            reason='数据缺口：分红压力测试所需历史派息率/利润情景假设数据未采集，checklist工具无法核验；'
            'C.md已定义人工压力测试流程，权重不变，仍需按框架文档人工评分',
        ),
    ],
    checklist_definitions=[
        ChecklistDefinition('roe_3y_avg', 'ROE近3年均值', '%', 'higher_better', 12, 8),
        ChecklistDefinition(
            'eps',
            '净利润增长趋势',
            '元',
            'higher_better',
            None,
            0,
            '格档判定用EPS是否非负（即是否亏损），不用净利润增速字段（增速为负不代表亏损）；优档需结合商品价格走势人工判断',
        ),
        ChecklistDefinition('debt_ratio', '资产负债率', '%', 'lower_better', 45, 65),
    ],
    custom_builder=_build_c_payout_ratio_item,
    portfolio_label='C资源',
    industry_keywords=('煤炭', '石油', '天然气', '有色金属', '铜', '钢铁', '采矿'),
    stop_loss_pct=(0.82, 0.75),
))

_FRAMEWORK_D = _register(FrameworkMetadata(
    key='D',
    checklist_name='水电/公用事业框架',
    subjective_items=['特许经营稀缺性', '行业地位'],
    skipped_items=[
        SkippedChecklistItem(
            label='ROE行业相对',
            reason='数据缺口：fetcher.py仅采集ROE绝对值（roe_3y_avg），未做同行业分位排名，'
            'checklist工具无法核验是否处于行业前30%/50%分位；权重不变，仍需结合同业对比人工评分',
        ),
        SkippedChecklistItem(
            label='业务量增长',
            reason='数据缺口：业务量（如发电量/售电量）由实物量驱动，fetcher.py仅采集财务报表字段，'
            '未采集业务量数据，checklist工具无法核验；权重不变，仍需按框架文档人工评分',
        ),
        SkippedChecklistItem(
            label='前瞻股息率（压力测试后）',
            reason='数据缺口：分红压力测试所需历史派息率/利润情景假设数据未采集，checklist工具无法核验；'
            'D.md已定义人工压力测试流程，权重不变，仍需按框架文档人工评分',
        ),
    ],
    checklist_definitions=[
        ChecklistDefinition('debt_ratio', '资产负债率', '%', 'lower_better', 55, 70),
    ],
    portfolio_label='D公用',
    industry_keywords=('水电', '水力发电', '电网', '水务', '燃气', '高速', '公用事业'),
    stop_loss_pct=(0.88, 0.82),
))

_FRAMEWORK_E = _register(FrameworkMetadata(
    key='E',
    checklist_name='消费框架',
    subjective_items=['品牌/渠道', '行业地位'],
    skipped_items=[
        SkippedChecklistItem(
            label='存货周转天数',
            reason='数据缺口：fetcher.py未采集存货周转天数字段，checklist工具无法核验；'
            '该字段公开财报可查，权重不变，仍需按框架文档人工评分',
        ),
    ],
    checklist_definitions=[
        ChecklistDefinition('roe_3y_avg', 'ROE近3年均值', '%', 'higher_better', 20, 12),
        ChecklistDefinition('net_profit_growth', '净利润增速', '%', 'higher_better', 15, 8),
        ChecklistDefinition('gross_margin', '毛利率', '%', 'higher_better', 50, 30),
    ],
    portfolio_label='E消费',
    industry_keywords=('白酒', '消费', '食品', '零售', '饮料'),
))

_FRAMEWORK_F = _register(FrameworkMetadata(
    key='F',
    checklist_name='科技/互联网框架',
    subjective_items=['订单能见度/客户留存', '行业地位'],
    skipped_items=[
        SkippedChecklistItem(
            label='研发投入强度（R&D/收入）',
            reason='数据缺口：fetcher.py未采集研发投入字段，checklist工具无法核验；'
            '该字段公开财报可查，权重不变，仍需按框架文档人工评分',
        ),
    ],
    checklist_definitions=[
        ChecklistDefinition('revenue_growth_3y', '收入增速近3年均值', '%', 'higher_better', 30, 15),
        ChecklistDefinition(
            'gross_margin',
            '毛利率及趋势',
            '%',
            'higher_better',
            50,
            30,
            '达优/达格档要求的"不下滑"/"趋势平稳"代码不做验证，仅核对当期数值是否过线，趋势需人工结合历史数据复核',
            True,
        ),
    ],
    custom_builder=_build_f_operating_cf_quality_item,
    portfolio_label='F科技',
    industry_keywords=('互联网', '软件', '科技', '半导体', '游戏', '通信'),
    stop_loss_pct=(0.80, 0.72),
))


def build_checklist(code: str, framework: str, cycle_stage: str | None = None) -> list[ChecklistItem]:
    """基于缓存数据构建框架客观指标核对清单。

    cycle_stage 为后续周期判断预留；当前暂不使用。
    """
    del cycle_stage

    normalized_framework = framework.upper()
    metadata = framework_metadata.FRAMEWORK_REGISTRY.get(normalized_framework)
    if metadata is None:
        raise UnsupportedFrameworkError(
            f"暂不支持框架 {framework!r} 的 checklist；当前仅支持 'A'/'B'/'C'/'D'/'E'/'F'"
        )

    fundamentals = cache.get_fundamentals(code)
    if fundamentals is None:
        raise FundamentalsCacheMissingError(f"未找到 {code} 的有效基本面缓存")

    items = [
        _build_item(definition, fundamentals.get(definition.key))
        for definition in metadata.checklist_definitions
    ]
    if metadata.custom_builder is not None:
        items.append(metadata.custom_builder(fundamentals))
    return items


def format_checklist(
    items: list[ChecklistItem],
    framework: str,
    code: str,
    subjective: list[str],
    skipped: list[dict] | None = None,
) -> str:
    """生成人类可读的 checklist 文本报告。"""
    normalized_framework = framework.upper()
    metadata = framework_metadata.FRAMEWORK_REGISTRY.get(normalized_framework)
    framework_name = metadata.checklist_name if metadata else f'{normalized_framework}框架'

    lines = [
        f"框架客观指标核对清单：{framework_name} {code}",
        "────────────────────────────────",
    ]
    for item in items:
        line = (
            f"{item.label}: {_format_value(item.raw_value, item.unit)} | "
            f"{_format_thresholds(item)} | "
            f"结果:{item.result} | 数据:{item.data_status}"
        )
        if item.note:
            line += f" | 备注:{item.note}"
        lines.append(line)

    if subjective:
        lines.extend([
            "",
            f"需人工主观判断（不参与代码核对）：{'、'.join(subjective)}",
        ])

    if skipped:
        lines.extend([
            "",
            "checklist工具无法核验（仍需按框架文档人工评分，权重不变）：",
        ])
        for skipped_item in skipped:
            lines.append(f"- {skipped_item['label']}：{skipped_item['reason']}")

    return '\n'.join(lines)


def _format_value(value: float | None, unit: str) -> str:
    if value is None:
        return '数据缺失'
    return f'{value:.1f}{unit}'


def _format_thresholds(item: ChecklistItem) -> str:
    excellent = _format_threshold('优线', item.direction, item.excellent_threshold, item.unit)
    if item.pass_threshold is None:
        return excellent
    passing = _format_threshold('格线', item.direction, item.pass_threshold, item.unit)
    return f'{excellent} {passing}'


def _format_threshold(label: str, direction: str, threshold: float | None, unit: str) -> str:
    if threshold is None:
        return f'{label}未设'
    op = '≥' if direction == 'higher_better' else '≤'
    return f'{label}{op}{_format_number(threshold)}{unit}'


def _format_number(value: float) -> str:
    return str(int(value)) if value == int(value) else str(value)
