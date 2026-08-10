import base64
import os
import requests
import sqlite3

from dotenv import load_dotenv
import streamlit as st

from langchain.agents import create_agent
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langgraph.checkpoint.sqlite import SqliteSaver

# Mapeamento do diretório base do script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuração da página Streamlit
st.set_page_config(page_title="Assistente Técnico NASA", page_icon="🚀", layout="wide")


def imagem_base64(caminho: str) -> str:
    """Converte imagem local para string Base64."""
    with open(caminho, "rb") as arquivo:
        return base64.b64encode(arquivo.read()).decode("utf-8")


# Carregamento do banner em Base64 usando caminho dinâmico
caminho_banner = os.path.join(BASE_DIR, "Imagens", "Imagem Nasa Artemis.jpg")
banner_base64 = imagem_base64(caminho_banner)

# Estilização CSS customizada
st.markdown(
    f"""
    <style>
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main {{
        background-color: #0b132b !important;
        color: #ffffff !important;
    }}

    .block-container {{
        max-width: 100% !important;
        padding-top: 0 !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        padding-bottom: 100px !important;
    }}

    .banner-nasa {{
        width: 100%;
        height: 380px;
        position: relative;
        overflow: hidden;
        background-size: cover;
        background-position: center center;
        background-repeat: no-repeat;
        background-image: url('data:image/jpeg;base64,{banner_base64}');
    }}

    .banner-nasa::after {{
        content: "";
        position: absolute;
        left: 0;
        right: 0;
        bottom: 0;
        height: 160px;
        background: linear-gradient(to bottom, rgba(11, 19, 43, 0), #0b132b);
    }}

    .cabecalho-nasa {{
        width: 100%;
        padding-top: 10px;
        padding-bottom: 10px;
    }}

    .cabecalho-nasa h1 {{
        color: #ffffff !important;
        font-size: 52px !important;
        font-weight: 700 !important;
        margin-top: 0 !important;
        margin-bottom: 8px !important;
        letter-spacing: -0.5px;
    }}

    .cabecalho-nasa p {{
        color: #aab4c8 !important;
        font-size: 20px !important;
        margin: 0 !important;
    }}

    .logo-nasa-container img {{
        width: 120px !important;
        height: auto !important;
        object-fit: contain !important;
    }}

    .divisoria-nasa {{
        width: 89.6%;
        height: 1px;
        margin: 15px auto 30px auto;
        background-color: #1c2947;
    }}

    /* Estilização das mensagens do chat com texto em branco */
    [data-testid="stChatMessage"] {{
        margin-left: 5.2% !important;
        margin-right: 5.2% !important;
        background-color: #111d38 !important;
        border: 1px solid #263858 !important;
        border-radius: 12px !important;
    }}

    [data-testid="stChatMessage"] * {{
        color: #ffffff !important;
    }}

    [data-testid="stBottomBlockContainer"] {{
        background-color: #0b132b !important;
        border-top: 1px solid #172542 !important;
        padding-top: 10px !important;
    }}

    [data-testid="stBottomBlockContainer"] > div {{
        background-color: #0b132b !important;
    }}

    [data-testid="stChatInput"] {{
        background-color: #17233d !important;
        border: 1px solid #31466b !important;
        border-radius: 14px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.30) !important;
    }}

    [data-testid="stChatInput"] > div {{
        background-color: #17233d !important;
        border: none !important;
        border-radius: 14px !important;
    }}

    [data-testid="stChatInput"] textarea {{
        background-color: #17233d !important;
        color: #ffffff !important;
        border: none !important;
        font-size: 16px !important;
    }}

    [data-testid="stChatInput"] textarea::placeholder {{
        color: #8d9ab2 !important;
        opacity: 1 !important;
    }}

    [data-testid="stChatInput"] button {{
        background-color: #263858 !important;
        color: #ffffff !important;
        border-radius: 10px !important;
    }}

    header[data-testid="stHeader"], footer {{
        background-color: #0b132b !important;
    }}

    ::-webkit-scrollbar {{
        width: 8px;
    }}

    ::-webkit-scrollbar-track {{
        background: #0b132b;
    }}

    ::-webkit-scrollbar-thumb {{
        background: #263858;
        border-radius: 10px;
    }}

    @media (max-width: 768px) {{
        .banner-nasa {{ height: 250px; }}
        .cabecalho-nasa h1 {{ font-size: 32px !important; }}
        .cabecalho-nasa p {{ font-size: 16px !important; }}
        .logo-nasa-container img {{ width: 90px !important; }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Renderização do Banner
st.markdown('<div class="banner-nasa"></div>', unsafe_allow_html=True)

# Cabeçalho com proporção refinada [1, 4.2, 0.8]
col_esq, col_titulo, col_logo = st.columns([1, 4.2, 0.8], gap="medium")

with col_esq:
    st.write("")

with col_titulo:
    st.markdown(
        """
        <div class="cabecalho-nasa">
            <h1>Assistente Técnico NASA</h1>
            <p>Agente especialista em exploração lunar e Programa Artemis.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_logo:
    st.markdown(
        '<div class="logo-nasa-container" style="display: flex; justify-content: flex-end; align-items: center; height: 100%;">',
        unsafe_allow_html=True,
    )
    caminho_logo = os.path.join(BASE_DIR, "Imagens", "nasa-seeklogo.png")
    st.image(caminho_logo, width=120)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="divisoria-nasa"></div>', unsafe_allow_html=True)

# Carregamento do .env
caminho_env = os.path.join(BASE_DIR, ".env")
load_dotenv(caminho_env, override=True)


@st.cache_resource
def carregar_recursos():
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    caminho_faiss = os.path.join(BASE_DIR, "faiss_index")
    vectorstore = FAISS.load_local(
        caminho_faiss, embeddings, allow_dangerous_deserialization=True
    )
    api_key = os.getenv("GROQ_API_KEY")

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2, api_key=api_key)
    return vectorstore, llm


try:
    vectorstore, llm = carregar_recursos()
except Exception as e:
    st.error(f"Erro ao carregar o banco vetorial ou a API Key da Groq: {e}")
    st.stop()


# Ferramenta RAG otimizada para consumir menos tokens
@tool
def pega_contexto_artemis_lunar(query: str) -> str:
    """Busca contexto técnico sobre o Programa Artemis, naves e missões na Lua nos PDFs da NASA."""
    retriever = vectorstore.as_retriever(search_kwargs={"k": 1})
    resultado = retriever.invoke(query)
    texto_formatado = []

    for doc in resultado:
        fonte = doc.metadata.get("source", "NASA").split("/")[-1]
        pagina = doc.metadata.get("page", 0) + 1
        conteudo_limitado = doc.page_content[:1500]
        texto_formatado.append(
            f"[Documento: '{fonte}', Página {pagina}]\n{conteudo_limitado}"
        )

    return "\n\n---\n\n".join(texto_formatado)


# Ferramenta para consulta de imagens e projetos na API pública da NASA
@tool
def consulta_api_nasa(query: str) -> str:
    """Consulta a API de imagens da NASA para dúvidas gerais não contidas nos PDFs."""
    try:
        url = "https://images-api.nasa.gov/search"
        response = requests.get(
            url, params={"q": query, "media_type": "image"}, timeout=5
        )
        if response.status_code == 200:
            items = response.json().get("collection", {}).get("items", [])
            if items:
                desc = items[0]["data"][0].get("description", "")
                return f"[Fonte: API da NASA]\n{desc[:300]}"
    except Exception:
        pass
    return "Nenhum dado retornado da API da NASA."


tools = [pega_contexto_artemis_lunar, consulta_api_nasa]

# Prompt do Sistema
system_prompt = """
Você é um assistente técnico especialista da NASA.
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

# Configuração de memória local via SQLite
caminho_db = os.path.join(BASE_DIR, "memoria_agente.db")
conn = sqlite3.connect(caminho_db, check_same_thread=False)
memoria = SqliteSaver(conn)
memoria.setup()

# Criação do agente com LangGraph
agente_nasa = create_agent(
    model=llm, tools=tools, system_prompt=system_prompt, checkpointer=memoria
)

# Inicialização e renderização do histórico no Streamlit
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    st.chat_message(msg["role"]).write(msg["content"])

# Execução do chat
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
