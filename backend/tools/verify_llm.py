"""
LLM 配置验证 CLI 工具

用法：
    # 读取 .env 验证
    python tools/verify_llm.py

    # 手动指定 key/base_url 验证
    python tools/verify_llm.py --chat-key acu_xxx --chat-url https://api.ltzy.top/v1
    python tools/verify_llm.py --emb-key acu_yyy --emb-url https://api.ltzy.top/v1
"""
from __future__ import annotations

import argparse
import os
import sys

# 将项目根目录加入 sys.path，确保能导入 app 包
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv

from app.llm_adapter import (
    find_working_chat_config,
    find_working_embedding_config,
)


def _print_section(title: str) -> None:
    print(f"\n{'=' * 50}")
    print(title)
    print("=" * 50)


def _mask_key(key: str) -> str:
    if not key or len(key) <= 12:
        return key or "<未配置>"
    return f"{key[:8]}...{key[-4:]}"


def main() -> int:
    parser = argparse.ArgumentParser(description="验证 LLM 与 Embedding API 配置")
    parser.add_argument("--chat-key", help="对话 API Key（覆盖 .env）")
    parser.add_argument("--chat-url", help="对话 API Base URL（覆盖 .env）")
    parser.add_argument("--chat-model", help="优先尝试的对话模型（覆盖 .env）")
    parser.add_argument("--emb-key", help="Embedding API Key（覆盖 .env）")
    parser.add_argument("--emb-url", help="Embedding API Base URL（覆盖 .env）")
    parser.add_argument("--emb-model", help="优先尝试的 Embedding 模型（覆盖 .env）")
    args = parser.parse_args()

    # 加载 .env（若存在）
    env_path = os.path.join(project_root, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)

    chat_key = args.chat_key or os.getenv("QWEN_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    chat_url = args.chat_url or os.getenv("QWEN_BASE_URL") or os.getenv("OPENAI_BASE_URL") or ""
    chat_model = args.chat_model or os.getenv("QWEN_MODEL") or os.getenv("OPENAI_MODEL") or ""

    emb_key = args.emb_key or os.getenv("EMBEDDING_API_KEY") or chat_key or ""
    emb_url = args.emb_url or os.getenv("EMBEDDING_BASE_URL") or chat_url or ""
    emb_model = args.emb_model or os.getenv("EMBEDDING_MODEL") or ""

    exit_code = 0

    # 验证对话 API
    _print_section("对话 / Agent LLM 配置验证")
    print(f"Base URL: {chat_url or '<未配置>'}")
    print(f"API Key:  {_mask_key(chat_key)}")
    print(f"首选模型: {chat_model or '<未配置>'}")

    if not chat_url or not chat_key:
        print("\n[SKIP] 对话 API Key 或 Base URL 未配置，跳过验证。")
    else:
        preferred = [chat_model] if chat_model else []
        result = find_working_chat_config(chat_url, chat_key, preferred_models=preferred)
        if result["success"]:
            print(f"\n[OK] 可用模型: {result['model']}")
            print(f"     测试回复: {result['error'][:80]}")
            if result["model"] != chat_model:
                print(f"\n[TIP] 你配置的模型 '{chat_model}' 不可用，")
                print(f"      建议将 QWEN_MODEL 改为: {result['model']}")
        else:
            print(f"\n[FAIL] {result['error']}")
            exit_code = 1

    # 验证 Embedding API
    _print_section("Embedding / RAG 向量配置验证")
    print(f"Base URL: {emb_url or '<未配置>'}")
    print(f"API Key:  {_mask_key(emb_key)}")
    print(f"首选模型: {emb_model or '<未配置>'}")

    if not emb_url or not emb_key:
        print("\n[SKIP] Embedding API Key 或 Base URL 未配置，跳过验证。")
    else:
        preferred = [emb_model] if emb_model else []
        result = find_working_embedding_config(emb_url, emb_key, preferred_models=preferred)
        if result["success"]:
            print(f"\n[OK] 可用模型: {result['model']}")
            print(f"     向量维度: {result['error']}")
            if result["model"] != emb_model:
                print(f"\n[TIP] 你配置的模型 '{emb_model}' 不可用，")
                print(f"      建议将 EMBEDDING_MODEL 改为: {result['model']}")
        else:
            print(f"\n[FAIL] {result['error']}")
            exit_code = 1

    _print_section("验证完成")
    if exit_code == 0:
        print("所有已配置 API 均可用。")
    else:
        print("部分 API 验证失败，请根据上方提示修改 .env 后重试。")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
