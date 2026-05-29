# coding=utf-8
"""
报告生成模块

提供报告数据准备和 HTML 生成功能：
- prepare_report_data: 准备报告数据
- generate_html_report: 生成 HTML 报告
"""

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from trendradar.utils.time import get_configured_time


def _safe_int(value: Any, default: int = 0) -> int:
    """安全转换为整数，失败时返回默认值。"""
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


SECTION_TITLES = {
    "core_trends": "核心热点态势",
    "sentiment_controversy": "舆论风向争议",
    "signals": "异动与弱信号",
    "rss_insights": "RSS 深度洞察",
    "outlook_strategy": "研判策略建议",
}


def _safe_text(value: Any) -> str:
    """安全转换为字符串并去除首尾空白。"""
    return str(value).strip() if value is not None else ""


def _build_reference(
    channel: str,
    source: str,
    title: str,
    url: str = "",
    time_display: str = "",
) -> Optional[Dict[str, str]]:
    """构建单条引用记录。"""
    title_text = _safe_text(title)
    if not title_text:
        return None

    source_text = _safe_text(source) or "未知来源"
    url_text = _safe_text(url)
    time_text = _safe_text(time_display)
    raw_key = f"{channel}|{source_text}|{title_text}|{url_text}"
    ref_key = hashlib.sha1(raw_key.encode("utf-8")).hexdigest()[:12]

    return {
        "ref_key": ref_key,
        "channel": channel,
        "source": source_text,
        "title": title_text,
        "url": url_text,
        "time_display": time_text,
    }


def _dedupe_references(references: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """按 ref_key 去重并稳定排序。"""
    deduped: Dict[str, Dict[str, str]] = {}
    for reference in references:
        ref_key = reference.get("ref_key", "")
        if ref_key and ref_key not in deduped:
            deduped[ref_key] = reference

    return sorted(
        deduped.values(),
        key=lambda item: (
            item.get("source", ""),
            item.get("title", ""),
            item.get("url", ""),
            item.get("channel", ""),
            item.get("time_display", ""),
        ),
    )


def _collect_trend_references(stats: List[Dict]) -> List[Dict[str, str]]:
    """收集趋势看点引用。"""
    references: List[Dict[str, str]] = []
    for stat in (stats or [])[:8]:
        for title in (stat.get("titles") or [])[:3]:
            if not isinstance(title, dict):
                continue
            reference = _build_reference(
                channel="趋势看点",
                source=title.get("source_name", "未知来源"),
                title=title.get("title", ""),
                url=title.get("url", "") or title.get("mobile_url", ""),
                time_display=title.get("time_display", ""),
            )
            if reference:
                references.append(reference)
    return _dedupe_references(references)


def _collect_rss_references(rss_items: Optional[List[Dict]]) -> List[Dict[str, str]]:
    """收集 RSS 引用。"""
    references: List[Dict[str, str]] = []
    for group in (rss_items or [])[:8]:
        if not isinstance(group, dict):
            continue
        group_word = _safe_text(group.get("word", ""))
        for title in (group.get("titles") or [])[:3]:
            if not isinstance(title, dict):
                continue
            source_name = title.get("source_name") or title.get("feed_name") or group_word or "未知来源"
            reference = _build_reference(
                channel="RSS订阅",
                source=source_name,
                title=title.get("title", ""),
                url=title.get("url", "") or title.get("mobile_url", ""),
                time_display=title.get("time_display", ""),
            )
            if reference:
                references.append(reference)
    return _dedupe_references(references)


def _collect_hot_references(standalone_data: Optional[Dict]) -> List[Dict[str, str]]:
    """收集平台热点引用。"""
    if not isinstance(standalone_data, dict):
        return []

    references: List[Dict[str, str]] = []

    for platform in (standalone_data.get("platforms") or [])[:8]:
        if not isinstance(platform, dict):
            continue
        source_name = _safe_text(platform.get("name", platform.get("id", ""))) or "平台热点"
        for item in (platform.get("items") or [])[:8]:
            if not isinstance(item, dict):
                continue
            reference = _build_reference(
                channel="平台热点",
                source=source_name,
                title=item.get("title", ""),
                url=item.get("url", ""),
                time_display=item.get("time_display", "") or item.get("published_at", ""),
            )
            if reference:
                references.append(reference)

    for feed in (standalone_data.get("rss_feeds") or [])[:8]:
        if not isinstance(feed, dict):
            continue
        source_name = _safe_text(feed.get("name", feed.get("id", ""))) or "RSS源"
        for item in (feed.get("items") or [])[:8]:
            if not isinstance(item, dict):
                continue
            reference = _build_reference(
                channel="平台热点",
                source=source_name,
                title=item.get("title", ""),
                url=item.get("url", ""),
                time_display=item.get("time_display", "") or item.get("published_at", ""),
            )
            if reference:
                references.append(reference)

    return _dedupe_references(references)


def _collect_section_references(
    stats: List[Dict],
    rss_items: Optional[List[Dict]],
    standalone_data: Optional[Dict],
) -> Dict[str, List[Dict[str, str]]]:
    """按板块收集引用候选。"""
    trend_refs = _collect_trend_references(stats)
    rss_refs = _collect_rss_references(rss_items)
    hot_refs = _collect_hot_references(standalone_data)

    def _merge_refs(*groups: List[Dict[str, str]]) -> List[Dict[str, str]]:
        merged: List[Dict[str, str]] = []
        for group in groups:
            merged.extend(group)
        return _dedupe_references(merged)

    return {
        "core_trends": _merge_refs(trend_refs[:8], hot_refs[:3]),
        "sentiment_controversy": _merge_refs(trend_refs[:8]),
        "signals": _merge_refs(trend_refs[:6], hot_refs[:6]),
        "rss_insights": _merge_refs(rss_refs[:10], trend_refs[:2]),
        "outlook_strategy": _merge_refs(trend_refs[:5], rss_refs[:5], hot_refs[:4]),
    }


def _split_paragraphs(content: str) -> List[str]:
    """将板块文本稳定拆分为段落。"""
    normalized = _safe_text(content).replace("\r\n", "\n")
    if not normalized:
        return []

    blocks = [part.strip() for part in normalized.split("\n\n") if part.strip()]
    if blocks:
        return blocks

    lines = [line.strip() for line in normalized.split("\n") if line.strip()]
    return lines if lines else [normalized]


def _build_section_block(
    section_id: str,
    title: str,
    content: str,
    references: List[Dict[str, str]],
) -> Dict[str, Any]:
    """构建单个板块的结构化数据。"""
    citations: List[Dict[str, Any]] = []
    for index, reference in enumerate(_dedupe_references(references), start=1):
        citations.append(
            {
                "citation_id": f"{section_id}__{reference['ref_key']}",
                "citation_no": index,
                "anchor_id": f"{section_id}-ref-{index:03d}",
                "channel": reference.get("channel", ""),
                "source": reference.get("source", "未知来源"),
                "title": reference.get("title", ""),
                "url": reference.get("url", ""),
                "time_display": reference.get("time_display", ""),
            }
        )

    paragraphs: List[Dict[str, Any]] = []
    for index, paragraph_text in enumerate(_split_paragraphs(content), start=1):
        paragraphs.append(
            {
                "paragraph_id": f"{section_id}__p{index:02d}",
                "anchor_id": f"{section_id}-p-{index:02d}",
                "text": paragraph_text,
                "citation_nos": [],
                "citation_ids": [],
            }
        )

    return {
        "section_id": section_id,
        "title": title,
        "content": _safe_text(content),
        "paragraphs": paragraphs,
        "citations": citations,
    }


def _serialize_ai_report(
    ai_analysis: Optional[Any],
    stats: Optional[List[Dict]] = None,
    rss_items: Optional[List[Dict]] = None,
    standalone_data: Optional[Dict] = None,
) -> Optional[Dict]:
    """将 AIAnalysisResult 转为可 JSON 序列化字典。"""
    if ai_analysis is None:
        return None

    # 兼容调用方直接传入 dict 的场景
    if isinstance(ai_analysis, dict):
        return ai_analysis

    section_texts = {
        "core_trends": str(getattr(ai_analysis, "core_trends", "") or "").strip(),
        "sentiment_controversy": str(getattr(ai_analysis, "sentiment_controversy", "") or "").strip(),
        "signals": str(getattr(ai_analysis, "signals", "") or "").strip(),
        "rss_insights": str(getattr(ai_analysis, "rss_insights", "") or "").strip(),
        "outlook_strategy": str(getattr(ai_analysis, "outlook_strategy", "") or "").strip(),
    }

    section_references = _collect_section_references(
        stats=stats or [],
        rss_items=rss_items,
        standalone_data=standalone_data,
    )
    sections = {
        section_id: _build_section_block(
            section_id=section_id,
            title=title,
            content=section_texts.get(section_id, ""),
            references=section_references.get(section_id, []),
        )
        for section_id, title in SECTION_TITLES.items()
    }

    standalone_summaries = getattr(ai_analysis, "standalone_summaries", {})
    if not isinstance(standalone_summaries, dict):
        standalone_summaries = {}

    has_content = any(
        _safe_text(section.get("content", "")) for section in sections.values()
    ) or any(v for v in standalone_summaries.values())

    return {
        "source": "agy",
        "success": bool(getattr(ai_analysis, "success", False)),
        "skipped": bool(getattr(ai_analysis, "skipped", False)),
        "error": str(getattr(ai_analysis, "error", "") or "").strip(),
        "mode": str(getattr(ai_analysis, "ai_mode", "") or "").strip(),
        "total_news": _safe_int(getattr(ai_analysis, "total_news", 0)),
        "analyzed_news": _safe_int(getattr(ai_analysis, "analyzed_news", 0)),
        "max_news_limit": _safe_int(getattr(ai_analysis, "max_news_limit", 0)),
        "hotlist_count": _safe_int(getattr(ai_analysis, "hotlist_count", 0)),
        "rss_count": _safe_int(getattr(ai_analysis, "rss_count", 0)),
        "sections": sections,
        "sections_text": section_texts,
        "standalone_summaries": {
            str(k): str(v) for k, v in standalone_summaries.items() if v is not None
        },
        "has_content": has_content,
    }


def prepare_report_data(
    stats: List[Dict],
    failed_ids: Optional[List] = None,
    new_titles: Optional[Dict] = None,
    id_to_name: Optional[Dict] = None,
    mode: str = "daily",
    rank_threshold: int = 3,
    matches_word_groups_func: Optional[Callable] = None,
    load_frequency_words_func: Optional[Callable] = None,
    show_new_section: bool = True,
    rss_items: Optional[List[Dict]] = None,
    standalone_data: Optional[Dict] = None,
    ai_analysis: Optional[Any] = None,
) -> Dict:
    """
    准备报告数据

    Args:
        stats: 统计结果列表
        failed_ids: 失败的 ID 列表
        new_titles: 新增标题
        id_to_name: ID 到名称的映射
        mode: 报告模式 (daily/incremental/current)
        rank_threshold: 排名阈值
        matches_word_groups_func: 词组匹配函数
        load_frequency_words_func: 加载频率词函数
        show_new_section: 是否显示新增热点区域

    Returns:
        Dict: 准备好的报告数据
    """
    processed_new_titles = []

    # 在增量模式下或配置关闭时隐藏新增新闻区域
    hide_new_section = mode == "incremental" or not show_new_section

    # 只有在非隐藏模式下才处理新增新闻部分
    if not hide_new_section:
        filtered_new_titles = {}
        if new_titles and id_to_name:
            # 如果提供了匹配函数，使用它过滤
            if matches_word_groups_func and load_frequency_words_func:
                word_groups, filter_words, global_filters = load_frequency_words_func()
                for source_id, titles_data in new_titles.items():
                    filtered_titles = {}
                    for title, title_data in titles_data.items():
                        if matches_word_groups_func(title, word_groups, filter_words, global_filters):
                            filtered_titles[title] = title_data
                    if filtered_titles:
                        filtered_new_titles[source_id] = filtered_titles
            else:
                # 没有匹配函数时，使用全部
                filtered_new_titles = new_titles

            # 打印过滤后的新增热点数（与推送显示一致）
            original_new_count = sum(len(titles) for titles in new_titles.values()) if new_titles else 0
            filtered_new_count = sum(len(titles) for titles in filtered_new_titles.values()) if filtered_new_titles else 0
            if original_new_count > 0:
                print(f"频率词过滤后：{filtered_new_count} 条新增热点匹配（原始 {original_new_count} 条）")

        if filtered_new_titles and id_to_name:
            for source_id, titles_data in filtered_new_titles.items():
                source_name = id_to_name.get(source_id, source_id)
                source_titles = []

                for title, title_data in titles_data.items():
                    url = title_data.get("url", "")
                    mobile_url = title_data.get("mobileUrl", "")
                    ranks = title_data.get("ranks", [])

                    processed_title = {
                        "title": title,
                        "source_name": source_name,
                        "time_display": "",
                        "count": 1,
                        "ranks": ranks,
                        "rank_threshold": rank_threshold,
                        "url": url,
                        "mobile_url": mobile_url,
                        "is_new": True,
                    }
                    source_titles.append(processed_title)

                if source_titles:
                    processed_new_titles.append(
                        {
                            "source_id": source_id,
                            "source_name": source_name,
                            "titles": source_titles,
                        }
                    )

    processed_stats = []
    for stat in stats:
        if stat["count"] <= 0:
            continue

        processed_titles = []
        for title_data in stat["titles"]:
            processed_title = {
                "title": title_data["title"],
                "source_name": title_data["source_name"],
                "time_display": title_data["time_display"],
                "count": title_data["count"],
                "ranks": title_data["ranks"],
                "rank_threshold": title_data["rank_threshold"],
                "url": title_data.get("url", ""),
                "mobile_url": title_data.get("mobileUrl", ""),
                "is_new": title_data.get("is_new", False),
            }
            processed_titles.append(processed_title)

        processed_stats.append(
            {
                "word": stat["word"],
                "count": stat["count"],
                "percentage": stat.get("percentage", 0),
                "titles": processed_titles,
            }
        )

    return {
        "stats": processed_stats,
        "new_titles": processed_new_titles,
        "failed_ids": failed_ids or [],
        "total_new_count": sum(
            len(source["titles"]) for source in processed_new_titles
        ),
        "generated_at": get_configured_time().isoformat(),
        "rss_items": rss_items or [],
        "standalone_data": standalone_data,
        "ai_report": _serialize_ai_report(ai_analysis, processed_stats, rss_items, standalone_data),
    }


def generate_html_report(
    stats: List[Dict],
    total_titles: int,
    failed_ids: Optional[List] = None,
    new_titles: Optional[Dict] = None,
    id_to_name: Optional[Dict] = None,
    mode: str = "daily",
    update_info: Optional[Dict] = None,
    rank_threshold: int = 3,
    output_dir: str = "output",
    date_folder: str = "",
    time_filename: str = "",
    render_html_func: Optional[Callable] = None,
    matches_word_groups_func: Optional[Callable] = None,
    load_frequency_words_func: Optional[Callable] = None,
) -> str:
    """
    生成 HTML 报告

    每次生成 HTML 后会：
    1. 保存时间戳快照到 output/html/日期/时间.html（历史记录）
    2. 复制到 output/html/latest/{mode}.html（最新报告）
    3. 复制到 output/index.html 和根目录 index.html（入口）

    Args:
        stats: 统计结果列表
        total_titles: 总标题数
        failed_ids: 失败的 ID 列表
        new_titles: 新增标题
        id_to_name: ID 到名称的映射
        mode: 报告模式 (daily/incremental/current)
        update_info: 更新信息
        rank_threshold: 排名阈值
        output_dir: 输出目录
        date_folder: 日期文件夹名称
        time_filename: 时间文件名
        render_html_func: HTML 渲染函数
        matches_word_groups_func: 词组匹配函数
        load_frequency_words_func: 加载频率词函数

    Returns:
        str: 生成的 HTML 文件路径（时间戳快照路径）
    """
    # 时间戳快照文件名
    snapshot_filename = f"{time_filename}.html"

    # 构建输出路径（扁平化结构：output/html/日期/）
    snapshot_path = Path(output_dir) / "html" / date_folder
    snapshot_path.mkdir(parents=True, exist_ok=True)
    snapshot_file = str(snapshot_path / snapshot_filename)

    # 准备报告数据
    report_data = prepare_report_data(
        stats,
        failed_ids,
        new_titles,
        id_to_name,
        mode,
        rank_threshold,
        matches_word_groups_func,
        load_frequency_words_func,
    )

    # 渲染 HTML 内容
    if render_html_func:
        html_content = render_html_func(
            report_data, total_titles, mode, update_info
        )
    else:
        # 默认简单 HTML
        html_content = f"<html><body><h1>Report</h1><pre>{report_data}</pre></body></html>"

    # 1. 保存时间戳快照（历史记录）
    with open(snapshot_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    # 2. 复制到 html/latest/{mode}.html（最新报告）
    latest_dir = Path(output_dir) / "html" / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    latest_file = latest_dir / f"{mode}.html"
    with open(latest_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    # 3. 复制到 index.html（入口）
    # output/index.html（供 Docker Volume 挂载访问）
    output_index = Path(output_dir) / "index.html"
    with open(output_index, "w", encoding="utf-8") as f:
        f.write(html_content)

    # 根目录 index.html（供 GitHub Pages 访问）
    root_index = Path("index.html")
    with open(root_index, "w", encoding="utf-8") as f:
        f.write(html_content)

    return snapshot_file
