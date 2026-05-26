# coding=utf-8
"""
AI 客户端模块

统一 AI 模型接口
当前仅支持 agy CLI（本地 Runner 模式）
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List


def _to_bool(value: Any, default: bool = False) -> bool:
    """将环境变量/配置值转换为布尔值。"""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in ("1", "true", "yes", "on"):
        return True
    if normalized in ("0", "false", "no", "off"):
        return False
    return default


def _to_int(value: Any, default: int) -> int:
    """将环境变量/配置值转换为整数。"""
    try:
        if value is None or str(value).strip() == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


class AIClient:
    """统一的 AI 客户端（仅支持 agy）。"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 AI 客户端

        Args:
            config: AI 配置字典
                - PROVIDER: 后端类型（当前仅支持 agy）
                - TIMEOUT: 请求超时时间（秒）
                - AGY_BIN: agy 可执行文件路径（PROVIDER=agy 时生效）
                - AGY_DANGEROUSLY_SKIP_PERMISSIONS: agy 是否附带危险权限参数
                - AGY_TIMEOUT: agy 调用超时时间（秒）
                - AGY_OUTPUT_FILE: agy 输出文件路径（可选）
        """
        self.provider = (config.get("PROVIDER") or os.environ.get("AI_PROVIDER", "agy")).strip().lower()
        self.timeout = _to_int(config.get("TIMEOUT"), 120)

        # agy 配置
        self.agy_bin = config.get("AGY_BIN") or os.environ.get("AGY_BIN", "/home/arthur/.local/bin/agy")
        self.agy_skip_permissions = _to_bool(
            config.get("AGY_DANGEROUSLY_SKIP_PERMISSIONS", os.environ.get("AGY_DANGEROUSLY_SKIP_PERMISSIONS", "true")),
            default=True,
        )
        self.agy_timeout = _to_int(config.get("AGY_TIMEOUT", os.environ.get("AGY_TIMEOUT")), default=self.timeout)
        self.agy_output_file = config.get("AGY_OUTPUT_FILE") or os.environ.get("AGY_OUTPUT_FILE", "")

    def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        调用 AI 模型进行对话

        Args:
            messages: 消息列表，格式: [{"role": "system/user/assistant", "content": "..."}]
            **kwargs: 额外参数，会覆盖默认配置

        Returns:
            str: AI 响应内容

        Raises:
            Exception: API 调用失败时抛出异常
        """
        if self.provider != "agy":
            raise ValueError("当前版本仅支持 AI_PROVIDER=agy，API 旧实现已移除")

        return self._chat_with_agy(messages, **kwargs)

    def _chat_with_agy(
        self,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> str:
        """通过 agy CLI 调用模型。"""
        output_path = self.agy_output_file
        is_temp_output = False
        if not output_path:
            fd, output_path = tempfile.mkstemp(prefix="trendradar-agy-", suffix=".md")
            os.close(fd)
            os.unlink(output_path)
            is_temp_output = True

        try:
            prompt = self._build_agy_prompt(messages, output_path)
            cmd = [self.agy_bin]
            if self.agy_skip_permissions:
                cmd.append("--dangerously-skip-permissions")
            cmd.extend(["-p", prompt])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=_to_int(kwargs.get("timeout"), self.agy_timeout),
                check=False,
            )

            # 优先读取约定输出文件，避免 stdout 混入日志。
            if output_path and Path(output_path).exists():
                content = Path(output_path).read_text(encoding="utf-8", errors="replace").strip()
                if content:
                    return content

            stdout_text = (result.stdout or "").strip()
            stderr_text = (result.stderr or "").strip()

            if result.returncode != 0:
                details = stderr_text or stdout_text
                if len(details) > 500:
                    details = details[:500] + "..."
                raise RuntimeError(f"agy 调用失败 (exit={result.returncode}): {details}")

            if stdout_text:
                return stdout_text

            raise RuntimeError("agy 调用完成但未返回任何内容")
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"agy 调用超时 ({exc.timeout}s)") from exc
        finally:
            if is_temp_output and output_path and Path(output_path).exists():
                Path(output_path).unlink(missing_ok=True)

    def _build_agy_prompt(self, messages: List[Dict[str, str]], output_path: str) -> str:
        """将 chat 消息拼装为 agy prompt。"""
        role_map = {
            "system": "系统指令",
            "user": "用户输入",
            "assistant": "历史回答",
        }
        sections = []
        for msg in messages:
            role = role_map.get(str(msg.get("role", "user")).lower(), "上下文")
            content = str(msg.get("content", "")).strip()
            if not content:
                continue
            sections.append(f"## {role}\n{content}")

        merged_context = "\n\n".join(sections) if sections else "(empty messages)"
        return (
            "你是 TrendRadar 的 AI 后端执行器。\n"
            "请基于下方上下文直接生成最终结果。\n"
            "输出要求：\n"
            "1. 不要输出解释过程。\n"
            "2. 不要使用 markdown 代码块围栏。\n"
            f"3. 将最终结果完整写入文件：{output_path}\n"
            "4. 文件中只保留最终内容，不加前后缀。\n\n"
            f"{merged_context}\n"
        )

    def validate_config(self) -> tuple[bool, str]:
        """
        验证配置是否有效

        Returns:
            tuple: (是否有效, 错误信息)
        """
        if self.provider != "agy":
            return False, "当前版本仅支持 AI_PROVIDER=agy，API 旧实现已移除"

        if not self.agy_bin:
            return False, "AI_PROVIDER=agy 时未配置 AGY_BIN"
        if not os.path.exists(self.agy_bin):
            return False, f"AI_PROVIDER=agy 但未找到可执行文件: {self.agy_bin}"
        if not os.access(self.agy_bin, os.X_OK):
            return False, f"AI_PROVIDER=agy 但文件不可执行: {self.agy_bin}"
        return True, ""
