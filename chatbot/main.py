from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from chatbot.services import google_sheets, groq_client
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Chatbot TJPE")

BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

DATA_CONTEXT = None


class ChatRequest(BaseModel):
    message: str
    history: list


@app.on_event("startup")
async def startup_event():
    global DATA_CONTEXT
    print("Carregando dados das planilhas...")
    DATA_CONTEXT = google_sheets.get_context_for_llm()
    print("Dados carregados com sucesso!")


@app.get("/", response_class=HTMLResponse)
async def get_chat(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/chat")
async def chat(request: ChatRequest):
    global DATA_CONTEXT
    
    history = request.history
    history.append({"role": "user", "content": request.message})
    
    response = groq_client.chat(history, DATA_CONTEXT)
    
    history.append({"role": "assistant", "content": response})
    
    return {"response": response, "history": history}


@app.post("/refresh-data")
async def refresh_data():
    global DATA_CONTEXT
    DATA_CONTEXT = google_sheets.get_context_for_llm()
    return {"status": "Dados atualizados com sucesso!"}


if __name__ == "__main__":
    import uvicorn
    from pathlib import Path
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
