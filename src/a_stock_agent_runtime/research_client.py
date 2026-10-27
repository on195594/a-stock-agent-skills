"""Small research-v1 HTTP client; never opens the investment-state database."""

import argparse
import json
import re
import sys
from urllib.parse import urlsplit

import requests

from a_stock_agent_runtime import paths


def endpoint_url(value: str) -> str:
    parsed = urlsplit(value)
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if (
        not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or (parsed.scheme != "https" and not (parsed.scheme == "http" and local))
    ):
        raise ValueError(
            "Research URL 须为 HTTPS（本机允许 HTTP），不能包含凭据、查询或片段"
        )
    return value.rstrip("/")


def _code(value: str) -> str:
    if not re.fullmatch(r"[0-9]{6}", value):
        raise argparse.ArgumentTypeError("股票代码须为六位数字")
    return value


def _positive_id(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("编号须为正整数")
    return number


def configure_parser(parser: argparse.ArgumentParser) -> None:
    actions = parser.add_subparsers(dest="action", required=True)
    reports = actions.add_parser("reports", help="读取公司历史报告目录")
    reports.add_argument("code", type=_code)
    for name, label in (("report", "读取报告及原文证据"), ("status", "读取任务状态")):
        action = actions.add_parser(name, help=label)
        action.add_argument("id", type=_positive_id)
    start = actions.add_parser("start", help="发起研究或关联追问，返回任务编号")
    start.add_argument("code", type=_code)
    start.add_argument("--question", required=True)
    start.add_argument("--parent-report-id", type=_positive_id)
    feedback = actions.add_parser("feedback", help="针对报告段落发起核查，保留原报告")
    feedback.add_argument("id", type=_positive_id)
    feedback.add_argument("--location", required=True)
    feedback.add_argument("--text", required=True)
    for action in (start, feedback):
        action.add_argument(
            "--request-id", required=True, help="同一请求重试沿用同一编号"
        )


def cmd_research(argv: list[str]) -> int:
    """通过 Research 服务复用报告、研究、追问及纠错；不修改账户或评分。"""
    parser = argparse.ArgumentParser(prog="a-stock-cache research")
    configure_parser(parser)
    args = parser.parse_args(argv)
    try:
        base, token = paths.research_connection()
        if not base or not token:
            raise ValueError(
                "请配置 A_STOCK_RESEARCH_URL 和 A_STOCK_RESEARCH_TOKEN；不会自动读取其他项目的凭据"
            )
        base = endpoint_url(base)
        body, params = None, None
        if args.action == "reports":
            path, params = "/api/reports", {"code": args.code}
        elif args.action == "report":
            path = f"/api/reports/{args.id}"
        elif args.action == "status":
            path = f"/api/runs/{args.id}"
        elif args.action == "start":
            path = "/api/research"
            body = {
                "code": args.code,
                "question": args.question,
                "request_id": args.request_id,
            }
            if args.parent_report_id is not None:
                body["parent_report_id"] = args.parent_report_id
        else:
            path = f"/api/reports/{args.id}/feedback"
            body = {
                "request_id": args.request_id,
                "location": args.location,
                "text": args.text,
            }
        response = requests.request(
            "POST" if body is not None else "GET",
            base + path,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Research-Version": "research-v1",
            },
            params=params,
            json=body,
            timeout=(10, 30),
            allow_redirects=False,
        )
        if response.status_code == 401:
            raise ValueError(
                "Research HTTP 401：研究凭据无效、已撤销或临时令牌已过期；"
                "请由 Research owner 更新 A_STOCK_RESEARCH_TOKEN，检查环境变量是否覆盖 runtime.env。"
                "更新前不要重试；更新后沿用原 request-id，不要重复创建任务"
            )
        if not 200 <= response.status_code < 300:
            raise ValueError(
                f"Research HTTP {response.status_code}；检查配置/请求，用原 request-id 查询或重试，勿重复创建任务"
            )
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("version") != "research-v1":
            raise ValueError("Research 响应版本不兼容")
    except requests.RequestException as exc:
        print(
            f"Research 连接失败：{type(exc).__name__}；提交结果可能未知，请沿用 request-id",
            file=sys.stderr,
        )
        return 1
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(payload, ensure_ascii=False))
    return 0
