import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

async def test():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.sarvam.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {SARVAM_API_KEY}"},
            json={
                "model": "sarvam-120b",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": False
            }
        )
        print("120b:", resp.status_code, resp.text)
        
        resp = await client.post(
            "https://api.sarvam.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {SARVAM_API_KEY}"},
            json={
                "model": "sarvam-30b",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": False,
                "reasoning_effort": None,
                "tools": [{"type": "function", "function": {"name": "test", "description": "t"}}]
            }
        )
        print("30b:", resp.status_code, resp.text)

asyncio.run(test())
