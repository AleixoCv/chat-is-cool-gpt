from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # 👈 IMPORTANTE
from pydantic import BaseModel
from typing import List, Optional
import os

from google import genai
from google.genai import types

# Modelo default do Gemini (pode trocar por outro suportado pelo free tier)
GEMINI_MODEL_DEFAULT = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY não configurada. Defina a variável de ambiente.")

# Cria o cliente do Gemini
client = genai.Client(api_key=GEMINI_API_KEY)


class Message(BaseModel):
    role: str  # "system" | "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str


app = FastAPI(
    title="IsCool GPT API (Gemini)",
    description="Assistente de estudos em Cloud usando Google Gemini API",
    version="1.0.0",
)

# ========= CORS CONFIG =========
# Origens que podem acessar a API via navegador
origins = [
    "http://localhost:5173",  # front em dev (Vite)
    # Quando o front estiver no S3, adicione o endpoint aqui, por exemplo:
    # "http://iscool-gpt-frontend-855035880603.s3-website-us-east-1.amazonaws.com",
    # ou o domínio/CloudFront que você usar.
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # pode ser ["*"] em ambiente de teste, se quiser liberar geral
    allow_credentials=True,
    allow_methods=["*"],         # GET, POST, OPTIONS, etc.
    allow_headers=["*"],         # Content-Type, Authorization, etc.
)
# ========= FIM CORS CONFIG =========


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Adaptação do endpoint /chat para usar Google Gemini.

    - Junta mensagens 'system' em uma system_instruction.
    - Converte mensagens 'user'/'assistant' em Contents com role 'user'/'model'.
    - Chama client.models.generate_content() e retorna response.text.
    """
    try:
        model_name = req.model or GEMINI_MODEL_DEFAULT

        # 1) Separamos as mensagens de sistema (system_instruction)
        system_messages = [m.content for m in req.messages if m.role == "system"]
        system_instruction = "\n".join(system_messages) if system_messages else None

        # 2) Construímos o "histórico" em termos de Content/Part do Gemini
        contents: List[types.Content] = []

        for m in req.messages:
            if m.role == "system":
                # já tratadas na system_instruction
                continue

            # Gemini usa roles "user" e "model".
            if m.role == "user":
                role = "user"
            elif m.role == "assistant":
                role = "model"
            else:
                # fallback seguro
                role = "user"

            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=m.content)],
                )
            )

        # 3) Monta config, incluindo system_instruction se existir
        config = None
        if system_instruction:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction
            )

        # 4) Chama o modelo Gemini
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )

        # .text já concatena o texto principal da resposta
        reply_text = response.text or ""
        return ChatResponse(reply=reply_text)

    except Exception as e:
        # Em produção, você poderia logar o erro em vez de expor o detalhe
        raise HTTPException(status_code=500, detail=str(e))
