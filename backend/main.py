from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent, Runner, RunResultStreaming, ItemHelpers
from typing import AsyncGenerator, AsyncIterator
import os
from dotenv import load_dotenv
import logging
import json
from pydantic import BaseModel
from typing import List
from fastapi import HTTPException
from fastapi.responses import JSONResponse
import traceback
import uvicorn

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

agent = Agent(
    name="Coder",
    instructions="You are a helpful coding assistant. Explain code clearly.",
    model="gpt-4o-mini",
)

# --------------------------
# OpenAI-Compatible Payload Model
# --------------------------

class OpenAIMessage(BaseModel):
    role: str
    content: str

class OpenAIRequest(BaseModel):
    model: str
    messages: List[OpenAIMessage]
    stream: bool = True

# --------------------------
# Stream Handler
# --------------------------

import uuid

class StreamHandler:
    def __init__(self, result: RunResultStreaming):
        self.result = result

    async def stream_events(self) -> AsyncIterator[str]:
        async for event in self.result.stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                content_piece = event.data.delta
                chunk = {
                    "choices": [{
                        "delta": {"content": content_piece},
                        "index": 0
                    }]
                }
                # logger.info(f"Yielding token: {content_piece}")
                yield f"data: {json.dumps(chunk)}\n\n"

        yield "data: [DONE]\n\n"



@app.get("/")
async def root():
    return {"message": "OpenAI Agent backend is up!"}

@app.post("/chat/completions")
async def chat_completions(payload: OpenAIRequest):
    try:
        # 👇 pass all prior messages as context
        message_context = [
            f"{m.role}: {m.content}" for m in payload.messages if m.role in ("user", "assistant")
        ]
        last_user_message = next(
            (msg.content for msg in reversed(payload.messages) if msg.role == "user"),
            None
        )

        if not last_user_message:
            raise HTTPException(status_code=400, detail="No user message found")

        logger.info(f"User prompt: {last_user_message}")

        # 👇 Combine context with current prompt
        full_prompt = "\n".join(message_context)

        result = Runner.run_streamed(agent, input=full_prompt)
        stream_handler = StreamHandler(result)

        return StreamingResponse(
            stream_handler.stream_events(),
            media_type="text/event-stream",
            headers={'x-vercel-ai-data-stream': 'v1'}
        )

    except Exception as e:
        logging.error("Chat completion error: %s", traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})





# --------------------------
# Run the server
# --------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
