import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = """Você é um assistente especializado em análise de dados de processos jurídicos do Tribunal de Justiça de Pernambuco (TJPE).

A planilha é composta por abas:
1. Uma aba com os nomes das contadorias (nome de cada contadoria)
2. Uma aba com a quantidade de processos de cada contadoria
3. Uma aba que consolida todos os processos das contadorias (com informações como: número do processo, vara, contadoria, data, prioridade, dias, etc.)

Você deve responder perguntas como:
- Quantos processos tem em determinada contadoria?
- Qual contadoria tem mais processos?
- Qual contadoria tem menos processos?
- Qual processo está em qual contadoria?
- Quais processos estão há mais tempo na contadoria?
- Qual a média de dias dos processos?
- Quais processos têm prioridade legal?

Suas respostas devem ser:
- Claras e objetivas
- Baseadas APENAS nos dados fornecidos
- Em português brasileiro
- Quando necessário, inclua números e estatísticas dos dados

Se não souber a resposta com base nos dados, diga que não tem informação suficiente."""


def chat(messages: list, context: str):
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    history_text = ""
    for msg in messages:
        role = "Usuário" if msg["role"] == "user" else "Assistente"
        history_text += f"{role}: {msg['content']}\n"
    
    full_prompt = f"{SYSTEM_PROMPT}\n\nContexto dos dados:\n{context}\n\nConversa:\n{history_text}"
    
    response = model.generate_content(full_prompt)
    
    return response.text
