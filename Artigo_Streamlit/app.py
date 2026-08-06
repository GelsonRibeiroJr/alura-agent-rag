import os
import sqlite3
import requests
import streamlit as st
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Assistente Técnico NASA", page_icon="🚀", layout="centered"
)

st.title("🚀 Assistente Técnico da NASA")
st.caption(
    "Agente RAG especialista em exploração lunar e Programa Artemis com memória e citações de fontes."
)


# --- CARREGAMENTO DO BANCO VETORIAL & LLM ---
load_dotenv(override=True)


@st.cache_resource
def carregar_recursos():
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    vectorstore = FAISS.load_local(
        "faiss_index", embeddings, allow_dangerous_deserialization=True
    )

    api_key = os.getenv("GROQ_API_KEY")

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2, api_key=api_key)
    return vectorstore, llm


try:
    vectorstore, llm = carregar_recursos()
except Exception as e:
    st.error(f"Erro ao carregar o banco vetorial ou a API Key da Groq: {e}")
    st.stop()


# --- DEFINIÇÃO DAS FERRAMENTAS ---
@tool
def pega_contexto_artemis_lunar(query: str) -> str:
    """Busca contexto técnico sobre o Programa Artemis, naves, rotas e missões na Lua nos PDFs oficiais da NASA."""
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
    resultado = retriever.invoke(query)

    texto_formatado = []
    for doc in resultado:
        fonte = doc.metadata.get("source", "NASA").split("/")[-1]
        pagina = doc.metadata.get("page", 0) + 1
        texto_formatado.append(
            f"[Documento: '{fonte}', Página {pagina}]\n{doc.page_content}"
        )

    return "\n\n---\n\n".join(texto_formatado)


@tool
def consulta_api_nasa(query: str) -> str:
    """Consulta a API da NASA para dúvidas sobre projetos gerais, telescópios ou espaço que não estão nos PDFs."""
    try:
        url = f"https://images-api.nasa.gov/search?q={query}&media_type=image"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            items = response.json().get("collection", {}).get("items", [])
            if items:
                desc = items[0]["data"][0].get("description", "")
                return f"[Fonte: API da NASA]\n{desc[:500]}"
    except Exception:
        pass
    return "Nenhum dado retornado da API da NASA."


tools = [pega_contexto_artemis_lunar, consulta_api_nasa]

# --- PROMPT DO AGENTE ---
system_prompt = """Você é um assistente técnico especialista da NASA.
Responda à pergunta do usuário de forma DIRETA, OBJETIVA e em Português do Brasil.
Não faça justificativas, introduções ou explicações sobre a busca.

REGRA OBRIGATÓRIA DE CITAÇÃO DE FONTE (NÃO IGNORE):
Toda resposta baseada em ferramentas DEVE seguir o formato de saída abaixo.

- A ferramenta 'pega_contexto_artemis_lunar' retorna o texto com a tag [Documento: 'NOME', Página X]. Você DEVE copiar essa informação exata para a última linha.
- A ferramenta 'consulta_api_nasa' retorna a tag [Fonte: API da NASA].

FORMATO DE SAÍDA OBRIGATÓRIO:
[Sua resposta direta e objetiva aqui]

Fonte: [Insira a citação exata aqui]

REGRA DE FORA DE ESCOPO (MUITO IMPORTANTE):
Se o usuário fizer perguntas que NÃO tenham relação com espaço, astronomia ou NASA (exemplo: esportes, culinária, política, etc.), NÃO USE NENHUMA FERRAMENTA. Responda APENAS:
"Sou um agente especialista em responder perguntas sobre a exploração lunar e sobre a NASA. Sua pergunta está fora do meu escopo de conhecimento."
"""

# --- INICIALIZAÇÃO DO AGENTE COM SQLITE ---
conn = sqlite3.connect("memoria_agente.db", check_same_thread=False)
memoria = SqliteSaver(conn)
memoria.setup()

agente_nasa = create_agent(
    model=llm, tools=tools, system_prompt=system_prompt, checkpointer=memoria
)

# --- INTERFACE STREAMLIT ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Pergunte sobre as missões Artemis ou a NASA..."):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Buscando informações e analisando dados..."):
            config = {"configurable": {"thread_id": "sessao_web"}}
            resposta = agente_nasa.invoke({"messages": [("user", prompt)]}, config)
            conteudo_resposta = resposta["messages"][-1].content

            st.write(conteudo_resposta)
            st.session_state["messages"].append(
                {"role": "assistant", "content": conteudo_resposta}
            )
