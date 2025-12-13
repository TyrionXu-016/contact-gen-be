from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import os
import openai
from dotenv import load_dotenv #用于加载env文件
from pathlib import Path # 使用 pathlib 处理路径
from pydantic import BaseModel # 用于更规范的请求体定义
from .knowledge_retriever import retrieve_knowledge_from_kb

#用来暴露给后端的接口
app = FastAPI()

#配置豆包AI客户端
load_dotenv()
api_key = os.getenv("VITE_HUOSHAN_API_KEY")
client = openai.OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=api_key,
)
model_name = "doubao-seed-1-6-251015"

#提前加载系统 prompt 的内容
base_dir = Path(__file__).parent.parent # 获取主目录
system_prompt_path = base_dir / "promptContract.txt"
system_prompt_content = ""
try:
    with open(system_prompt_path, 'r', encoding='utf-8') as f:
        system_prompt_content = f.read()
except FileNotFoundError:
    print(f"Error: System prompt file not found at {system_prompt_path}")
    system_prompt_content = "你是一个合同生成助手。请按正式合同格式、条款编号清晰地输出完整合同文本。" # Fallback
except Exception as e:
    print(f"Error reading system prompt file: {e}")
    system_prompt_content = "你是一个合同生成助手。请按正式合同格式、条款编号清晰地输出完整合同文本。" # Fallback

# 用户请求体规范
class GenerateRequest(BaseModel):
    prompt: str
    contract_type: str = None
    max_new_tokens: int = 5000
    temperature: float = 0.7
    use_new_knowledge_base: bool = True

@app.post("/generate-contract")
async def generate_contract(request: GenerateRequest):
    async def generate_chunks():
        try:
            messages=[
                {"role": "system", "content": system_prompt_content},
            ]
            #加入知识库检索内容
            retrieved_knowledge = []
            if request.use_new_knowledge_base:
                retrieved_knowledge = await retrieve_knowledge_from_kb(
                    query=request.prompt,
                    contract_type=request.contract_type,
                )

            knowledge_context = ""
            if retrieved_knowledge["latest_laws"]:
                    knowledge_context += "以下是相关领域最新法律法规：" + "\n".join(retrieved_knowledge["latest_laws"])
            if retrieved_knowledge["case_studies"]:
                    knowledge_context += "\n以下是相关领域典型案例：" + "\n".join(retrieved_knowledge["case_studies"])
            if retrieved_knowledge["standards"]:
                    knowledge_context += "\n以下是相关领域相关标准：" + "\n".join(retrieved_knowledge["standards"])
            if retrieved_knowledge["templates"]:
                    knowledge_context += "\n以下是相关领域合同模板：" + "\n".join(retrieved_knowledge["templates"])
            if knowledge_context:
                messages.append({"role": "user", "content": f"根据以下内容生成合同：\n{knowledge_context}\n请基于以上内容，结合我的需求生成合同文本：{request.prompt}"})
            else:
                messages.append({"role": "user", "content": request.prompt})

            # 开启流式输出
            stream_response = client.chat.completions.create(
                model = model_name,
                messages=messages,
                max_tokens=request.max_new_tokens,
                temperature=request.temperature,
                stream=True, # 关键：开启流
            )

            for chunk in stream_response:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    # 返回每个生成的文本块
                    yield chunk.choices[0].delta.content
        except Exception as e:
            print(f"Error during streaming generation: {e}")
            yield f"Error: Failed to generate contract via streaming: {str(e)}"

    return StreamingResponse(generate_chunks(), media_type="text/event-stream")