from groq import Groq
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """Você é um assistente especializado em análise de dados de processos jurídicos do Tribunal de Justiça de Pernambuco (TJPE). 
Você tem acesso aos dados de processos em tempo real.

Suas respostas devem ser:
- Claras e objetivas
- Baseadas APENAS nos dados fornecidos
- Em português brasileiro
- Quando necessário, inclua números e estatísticas dos dados

Se não souber a resposta com base nos dados, diga que não tem informação suficiente."""


def chat(messages: list, context: str):
    system_message = {
        "role": "system",
        "content": f"{SYSTEM_PROMPT}\n\nContexto dos dados:\n{context}"
    }
    
    full_messages = [system_message] + messages
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=full_messages,
        temperature=0.7,
        max_tokens=1024,
    )
    
    return response.choices[0].message.content
