import tempfile
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from aristotle.graph.parser.parser_settings import ParserSettings

from ..aristotle import project_config
from ..aristotle.agent import AristotleAgent, docs_db, graph_db
from ..aristotle.graph.parser import CodebaseParser
from .request_types import *

app = FastAPI(
    debug=True,
    title="aristotle-server",
    description="Back end server for interacting with the Aristotle AI agent",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("[INFO] Initializing agent...")
agent = AristotleAgent()


async def startup_event():
    print("[INFO] Server is starting up...")
    print(f"[INFO] LLM model for agent: {project_config.ollama_llm_main_model}")
    await graph_db.setup()


async def shutdown_event():
    print("[INFO] Server is shutting down...")
    await graph_db.stop()


app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)


@app.get("/")
async def index():
    return HTMLResponse(
        content="""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aristotle Server Index Page</title>
</head>
<body>
    <h1>Hello from Aristotle, your server is working!</h1>
</body>
</html>
"""
    )


def log_response(payload: Dict[str, Any], status_code: int = 200) -> None:
    print(f"[RESPONSE {status_code}] {payload}")


@app.post("/chat")
async def chat(chat_request: ChatRequest) -> JSONResponse:
    print(f"[INFO] Received: '{chat_request}'")

    response, error_message = await agent.chat(
        chat_request.message, chat_request.history, chat_request.files
    )

    if error_message is not None or response is None:
        payload = {"error": error_message}
        log_response(payload, 500)
        raise HTTPException(status_code=500, detail=error_message)

    payload = {
        "response": response.response,
        "references": response.references,
    }
    log_response(payload, 200)
    return JSONResponse(content=payload, status_code=200)


@app.post("/load")
async def load_file(load_request: LoadFileRequest) -> JSONResponse:
    try:
        with tempfile.NamedTemporaryFile(mode="w") as file:
            file.write(load_request.file_content)
            file.seek(0)
            if file.name.endswith(".py"):
                parser = CodebaseParser(
                    load_request.codebase_name,
                    ParserSettings(include_private_members=True),
                )
                parser.parse_file(
                    file.path,
                    load_request.file_path,
                    load_request.file_path,
                )
                await graph_db.insert_parser_results(parser)
            elif file.name.endswith(".md"):
                docs_db.load_file(file.path, load_request.codebase_name)

        payload = {
            "message": f"File {load_request.file_path} loaded successfully",
            "data": None,
        }
        log_response(payload, 200)
        return JSONResponse(content=payload, status_code=200)
    except Exception as e:
        payload = {"error": str(e)}
        log_response(payload, 500)
        raise HTTPException(status_code=500, detail=str(e))
