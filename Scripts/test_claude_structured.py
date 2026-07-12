#!/usr/bin/env python
"""Test Claude structured output with bxcv.store"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

class TestResult(BaseModel):
    intent: str = 'test'

API_KEY = os.getenv("LLM_API_KEY")
BASE_URL = os.getenv("LLM_BASE_URL", "https://bxcv.store/v1")

if not API_KEY:
    raise SystemExit("请先设置 LLM_API_KEY 后再运行该测试脚本。")

llm = ChatOpenAI(
    model='claude-opus-4-8',
    api_key=API_KEY,
    base_url=BASE_URL
)

msg = [HumanMessage(content='Say hi in one word')]

print('Testing json_mode...')
try:
    structured = llm.with_structured_output(TestResult, method='json_mode')
    result = structured.invoke(msg)
    print(f'json_mode OK: {result}')
except Exception as e:
    print(f'json_mode FAIL: {type(e).__name__}: {str(e)[:300]}')

print()
print('Testing function_calling...')
try:
    structured2 = llm.with_structured_output(TestResult, method='function_calling')
    result2 = structured2.invoke(msg)
    print(f'function_calling OK: {result2}')
except Exception as e:
    print(f'function_calling FAIL: {type(e).__name__}: {str(e)[:300]}')
