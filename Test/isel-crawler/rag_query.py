"""
RAG Query (AI-ISEL) — precisão melhorada
- Retriever com MMR + filtros por tipo de página (curso / plano_estudos) quando faz sentido
- Prompt anti-alucinação (responder só do contexto, senão dizer que não há dados)
- Fallback de modelos: Ollama -> (outro Ollama) -> OpenAI (se OPENAI_API_KEY)
"""

import os
import sys
import traceback
from typing import List, Dict

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# (Opcional) OpenAI se tiveres chave
USE_OPENAI = bool(os.getenv("OPENAI_API_KEY"))
if USE_OPENAI:
    try:
        from langchain_openai import ChatOpenAI
    except Exception:
        USE_OPENAI = False

CHROMA_PATH = "db"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

# Ordem de preferência de modelos Ollama (leves -> médios)
OLLAMA_CANDIDATES = [
    os.getenv("OLLAMA_MODEL", "mistral:latest"),
    "phi3:mini",
    "mistral:7b-instruct-q4_K_M",
]

# OpenAI por defeito (se houver API key)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

PROMPT_TEMPLATE = """
És o **assistente oficial do ISEL**.

Responde **apenas com base no contexto** abaixo. Se a resposta **não estiver claramente** no contexto, responde exatamente:
> “Essa informação não se encontra disponível nos registos atuais do ISEL.”

Estilo:
- Português europeu, conciso, em Markdown.
- Estrutura em secções e listas quando adequado.
- Usa emojis 🎓💶🕓📍 quando fizer sentido.
- Se a pergunta for sobre cursos, organiza por:
  - 🎓 Licenciaturas (1.º ciclo)
  - 📘 Mestrados (2.º ciclo)
  - 📗 Pós-graduações / Especialização
- Inclui duração/ECTS **só** se constar no contexto.

---
📚 **Contexto:**
{context}

❓ **Pergunta:**
{question}

💬 **Resposta factual (apenas do contexto):**
"""

prompt = PromptTemplate.from_template(PROMPT_TEMPLATE)


def load_db():
    embedding_fn = OllamaEmbeddings(model=EMBEDDING_MODEL)
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_fn)
    return db


def pick_llm():
    # 1) OpenAI se disponível
    if USE_OPENAI:
        try:
            return ChatOpenAI(model=OPENAI_MODEL, temperature=0.2), "openai"
        except Exception:
            pass

    # 2) Ollama local
    last_err = None
    for name in OLLAMA_CANDIDATES:
        try:
            llm = OllamaLLM(model=name, options={"num_gpu": 0})
            return llm, f"ollama:{name}"
        except Exception as e:
            last_err = e
            continue
    if last_err:
        print(f"⚠️ Falha ao selecionar LLM Ollama: {last_err}")
    return None, "none"


def intent_filter(query: str):
    """Escolhe filtro por tipo de página com base na pergunta."""
    q = query.lower()
    if any(k in q for k in ["licenciatura", "licenciaturas", "cursos", "curso", "mestrado", "pós-graduação", "plano de estudos", "plano de estudo"]):
        return {"type": {"$in": ["curso", "plano_estudos"]}}
    if any(k in q for k in ["propinas", "candidaturas", "calendário", "ingresso"]):
        return {"type": {"$in": ["admissao", "institucional"]}}
    return None


def retrieve(db: Chroma, query: str, k: int = 8) -> List:
    filter_meta = intent_filter(query)
    docs = []
    try:
        docs = db.similarity_search(
            query,
            k=k,
            filter=filter_meta,
            search_type="mmr",
            search_kwargs={"k": k, "fetch_k": max(20, 5 * k), "lambda_mult": 0.3},
        )
    except TypeError:
        docs = db.similarity_search(query, k=k, filter=filter_meta)
    if not docs:
        try:
            docs = db.similarity_search(
                query,
                k=k,
                search_type="mmr",
                search_kwargs={"k": k, "fetch_k": max(20, 5 * k), "lambda_mult": 0.3},
            )
        except TypeError:
            docs = db.similarity_search(query, k=k)
    return docs


def build_context(docs: List, query: str) -> Dict[str, str]:
    """Junta chunks e adiciona fallback manual para perguntas de cursos."""
    if not docs:
        return {"context": "", "sources": []}

    seen, sources, parts = set(), [], []
    total_chars, MAX_CHARS = 0, 6000

    for d in docs:
        url = d.metadata.get("url", "")
        title = d.metadata.get("title", "") or d.metadata.get("curso_nome", "") or ""
        if url and url not in seen:
            seen.add(url)
            sources.append({"url": url, "title": title})
        chunk = d.page_content.strip()
        if not chunk:
            continue
        if total_chars + len(chunk) > MAX_CHARS:
            chunk = chunk[: (MAX_CHARS - total_chars)]
        parts.append(chunk)
        total_chars += len(chunk)
        if total_chars >= MAX_CHARS:
            break

    context = "\n\n---\n\n".join(parts)

    # 🔹 Fallback automático se a query falar de cursos
    if any(k in query.lower() for k in ["curso", "licenciatura", "mestrado"]):
        context += "\n\n---\n\n" + """
        🏛️ O ISEL integra o Instituto Politécnico de Lisboa (IPL),
sendo uma instituição pública de ensino superior com autonomia
administrativa e científica. O IPL inclui ainda as escolas ESCS, ESELx,
ESML, ESD, ESTC e ESTeSL.

🎓 **Licenciaturas oferecidas no ISEL:**
- Engenharia Civil
- Engenharia Eletrónica e Telecomunicações e de Computadores
- Engenharia Informática e de Computadores
- Engenharia Informática, Redes e Telecomunicações
- Engenharia Mecânica
- Engenharia Química e Biológica
- Engenharia de Energia e Ambiente
- Matemática Aplicada à Tecnologia e à Empresa
- Engenharia Física Aplicada

📘 **Mestrados:**
- Engenharia Civil
- Engenharia Eletrotécnica e de Computadores
- Engenharia Informática
- Engenharia Mecânica
- Engenharia Química e Biológica
- Engenharia de Energia e Ambiente
- Matemática Aplicada à Indústria
"""

    return {"context": context, "sources": sources}


def answer(llm, question: str, ctx: str) -> str:
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"context": ctx, "question": question}).strip()


def print_sources(sources: List[Dict[str, str]]):
    if not sources:
        return
    print("\n🔗 **Fontes oficiais:**")
    for s in sources:
        url = s.get("url", "")
        title = s.get("title", "") or url
        print(f" - [{title}]({url})")


def main():
    print("🔍 A carregar base vetorial e embeddings...")
    db = load_db()
    llm, llm_name = pick_llm()
    if not llm:
        print("❌ Não foi possível inicializar nenhum LLM (Ollama/OpenAI).")
        sys.exit(1)

    print(f"\n🤖 AI-ISEL RAG iniciado! (LLM: {llm_name}) — Escreve a tua pergunta (ou 'sair'):\n")
    while True:
        try:
            query = input("❓ Pergunta: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 A sair...")
            break

        if query.lower() in {"sair", "exit", "quit"}:
            print("👋 A sair...")
            break

        print("\n💭 A pensar...\n")
        try:
            docs = retrieve(db, query, k=8)
            pack = build_context(docs, query)
            if not pack["context"]:
                print("> “Essa informação não se encontra disponível nos registos atuais do ISEL.”")
                continue

            resp = answer(llm, query, pack["context"])
            print("\n🧠 Resposta:\n")
            print(resp)
            print_sources(pack["sources"])
            print("\n" + "-" * 80)

        except Exception as e:
            print(f"⚠️ Erro: {e}\n")
            traceback.print_exc()
            print("\n" + "-" * 80)


if __name__ == "__main__":
    main()
