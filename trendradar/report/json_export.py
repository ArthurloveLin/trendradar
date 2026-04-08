# coding=utf-8
"""
JSON 报告导出模块
"""

import json
from typing import Dict


def generate_json_report(report_data: Dict) -> str:
    """
    将报告数据转换为 JSON 字符串

    Args:
        report_data: 由 prepare_report_data 生成的数据字典

    Returns:
        str: JSON 字符串
    """
    # 使用 ensure_ascii=False 以支持中文，separators 压缩体积
    return json.dumps(report_data, ensure_ascii=False, separators=(",", ":"))
