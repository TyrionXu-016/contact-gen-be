import json
import os
from pathlib import Path
from typing import Dict, Generator, Iterable

from asgiref.sync import async_to_sync
from dotenv import load_dotenv
from openai import OpenAI

from model_api.knowledge_retriever import retrieve_knowledge_from_kb

load_dotenv()

DEFAULT_MODEL_NAME = "doubao-seed-1-6-251015"
DEFAULT_PROMPT_TEMPLATE = (
    "你是一个合同生成助手。请按正式合同格式、条款编号清晰地输出完整合同文本。"
)

PROMPT_PATH = Path(__file__).resolve().parent.parent / "promptContract.txt"
if PROMPT_PATH.exists():
    SYSTEM_PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")
else:
    SYSTEM_PROMPT_TEMPLATE = DEFAULT_PROMPT_TEMPLATE


def _get_openai_client() -> OpenAI:
    api_key = os.getenv("VITE_HUOSHAN_API_KEY")
    if not api_key:
        raise RuntimeError("缺少 VITE_HUOSHAN_API_KEY，无法调用豆包模型")

    base_url = os.getenv(
        "HUOSHAN_API_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"
    )
    return OpenAI(base_url=base_url, api_key=api_key)


def _get_model_name() -> str:
    return os.getenv("HUOSHAN_MODEL_NAME", DEFAULT_MODEL_NAME)


async def _build_system_prompt_async(payload: Dict) -> str:
    template = SYSTEM_PROMPT_TEMPLATE

    default_values = {
        "latest_laws": "暂无检索到最新法律法规",
        "case_studies": "暂无检索到相关典型案例",
        "standards": "暂无检索到相关国标行规",
        "templates": "暂无检索到相关合同范本",
    }

    laws_str = default_values["latest_laws"]
    cases_str = default_values["case_studies"]
    standards_str = default_values["standards"]
    templates_str = default_values["templates"]

    if payload.get("use_new_knowledge_base", True):
        knowledge = await retrieve_knowledge_from_kb(
            payload.get("prompt", ""),
            payload.get("contract_type"),
            payload.get("cooperation_purpose"),
            payload.get("Core_scenario"),
        )
        if knowledge:
            laws_str = " ".join(knowledge.get("latest_laws", [])) or laws_str
            cases_str = " ".join(knowledge.get("case_studies", [])) or cases_str
            standards_str = " ".join(knowledge.get("standards", [])) or standards_str
            templates_str = " ".join(knowledge.get("templates", [])) or templates_str

    template = template.replace("{最新法律法规}", laws_str)
    template = template.replace("{最新合同纠纷案}", cases_str)
    template = template.replace("{最新国标行规}", standards_str)
    template = template.replace("{最新合同范本}", templates_str)

    return template.format(
        合同类型=payload.get("contract_type"),
        甲方=payload.get("first_party"),
        乙方=payload.get("second_party"),
        合作目的=payload.get("cooperation_purpose") or "",
        合同核心场景=payload.get("Core_scenario") or "",
    )


build_system_prompt = async_to_sync(_build_system_prompt_async)


def generate_contract_stream(payload: Dict) -> Iterable[str]:
    client = _get_openai_client()
    model_name = _get_model_name()
    system_prompt = build_system_prompt(payload)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": payload.get("prompt", "")},
    ]

    def _stream() -> Generator[str, None, None]:
        try:
            stream_response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=payload.get("max_new_tokens", 5000),
                temperature=payload.get("temperature", 0.7),
                stream=True,
            )

            for chunk in stream_response:
                delta = chunk.choices[0].delta if chunk.choices else None
                content = getattr(delta, "content", None) if delta else None
                if content:
                    yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
        except Exception as exc:  # pragma: no cover - 错误路径
            error_payload = {"error": str(exc)}
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"

    return _stream()
