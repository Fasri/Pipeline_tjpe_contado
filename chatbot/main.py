from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from chatbot.services import google_sheets, groq_client as ai_client, supabase_loader

load_dotenv()

app = FastAPI(title="Chatbot TJPE")

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

DATA_CONTEXT = None


class ChatRequest(BaseModel):
    message: str
    history: list


def get_data_context():
    global DATA_CONTEXT
    if DATA_CONTEXT is None:
        print("Carregando dados das planilhas e Supabase...")
        try:
            # Pegar dados de múltiplas fontes
            sheets_context = google_sheets.get_context_for_llm()
            supabase_context = supabase_loader.get_context_for_llm()
            
            DATA_CONTEXT = f"{sheets_context}\n\n{supabase_context}"
            print("Dados carregados com sucesso!")
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")
            DATA_CONTEXT = "Dados não disponíveis no momento."
    return DATA_CONTEXT


@app.get("/", response_class=HTMLResponse)
async def get_chat(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        context = get_data_context()
        
        history = request.history
        history.append({"role": "user", "content": request.message})
        
        response = ai_client.chat(history, context)
        
        history.append({"role": "assistant", "content": response})
        
        return {"response": response, "history": history}
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


@app.post("/refresh-data")
async def refresh_data():
    global DATA_CONTEXT
    DATA_CONTEXT = google_sheets.get_context_for_llm()
    return {"status": "Dados atualizados com sucesso!"}


if __name__ == "__main__":
    import uvicorn
    from pathlib import Path
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
