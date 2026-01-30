import os
import tempfile
from langchain_groq import ChatGroq
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from dotenv import load_dotenv

# --- SISTEMA HÍBRIDO DE IMPORTAÇÃO (PC vs NUVEM) ---
try:
    from langchain_classic.memory import VectorStoreRetrieverMemory
except ImportError:
    try:
        from langchain.memory import VectorStoreRetrieverMemory
    except ImportError:
        from langchain_community.memory import VectorStoreRetrieverMemory

try:
    from langchain_classic.chains import ConversationChain
except ImportError:
    from langchain.chains import ConversationChain

try:
    from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate, \
        HumanMessagePromptTemplate, MessagesPlaceholder
except ImportError:
    from langchain.prompts import PromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate, \
        HumanMessagePromptTemplate, MessagesPlaceholder

load_dotenv()

# --- CONFIGURAÇÕES GLOBAIS ---
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def carregar_personagem(arquivo):
    import json
    with open(f"personagens/{arquivo}", "r", encoding="utf-8") as f:
        return json.load(f)


def listar_personagens():
    if not os.path.exists("personagens"):
        os.makedirs("personagens")
        # Cria um personagem padrão se não existir
        padrao = {
            "nome": "Aria", "arquetipo": "Ladra", "tracos_personalidade": ["Cinica"],
            "objetivo_atual": "Sobreviver", "estilo_fala": ["Girias"],
            "valores_inagociaveis": ["Nao trair"], "nivel_maleabilidade": "Baixo",
            "segredo_obscuro": "Roubou o pai", "lore": "Uma ladra das ruas."
        }
        with open("personagens/Aria.json", "w", encoding="utf-8") as f:
            json.dump(padrao, f)
    return [f for f in os.listdir("personagens") if f.endswith(".json")]


def criar_personagem_avancado(nome, arquetipo, tracos, valores, objetivo, estilo, maleabilidade, segredo, historia):
    import json
    dados = {
        "nome": nome,
        "arquetipo": arquetipo,
        "tracos_personalidade": [t.strip() for t in tracos.split(',')],
        "valores_inagociaveis": [v.strip() for v in valores.split(',')],
        "objetivo_atual": objetivo,
        "estilo_fala": [e.strip() for e in estilo.split(',')],
        "nivel_maleabilidade": maleabilidade,
        "segredo_obscuro": segredo,
        "lore": historia
    }
    with open(f"personagens/{nome}.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)


# --- FUNÇÕES DE HISTÓRICO VISUAL (WHATSAPP) ---
def carregar_mensagens_salvas(nome_arquivo):
    import json
    if not os.path.exists("historicos"): os.makedirs("historicos")
    caminho = f"historicos/{nome_arquivo.replace('.json', '_chat.json')}"
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f: return json.load(f)
    return []


def salvar_mensagem_no_historico(nome_arquivo, role, content):
    import json
    msgs = carregar_mensagens_salvas(nome_arquivo)
    msgs.append({"role": role, "content": content})
    caminho = f"historicos/{nome_arquivo.replace('.json', '_chat.json')}"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(msgs, f, ensure_ascii=False, indent=4)


def limpar_historico_visual(nome_arquivo):
    caminho = f"historicos/{nome_arquivo.replace('.json', '_chat.json')}"
    if os.path.exists(caminho): os.remove(caminho)


# --- NOVA FUNÇÃO: PROCESSAR O PDF DO MUNDO ---
def processar_conhecimento_mundo(arquivo_pdf_bytes):
    """Lê um PDF e salva no banco vetorial de 'Conhecimento Geral'"""
    # 1. Salva o PDF temporariamente para o Loader ler
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(arquivo_pdf_bytes.read())
        tmp_path = tmp_file.name

    # 2. Carrega e fatia o PDF
    loader = PyPDFLoader(tmp_path)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)

    # 3. Salva na pasta 'memoria_mundo' (separado da conversa)
    pasta_mundo = "./memorias/mundo_conhecimento"
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=pasta_mundo
    )

    # Limpa arquivo temporário
    os.remove(tmp_path)
    return f"Conhecimento absorvido! {len(chunks)} fragmentos lidos."


# --- CÉREBRO PRINCIPAL (COM RAG) ---
def responder_usuario(texto_usuario, dados_personagem, nome_arquivo_personagem):
    # 1. Configura Memória de Conversa (Quem eu sou + O que falamos)
    nome_limpo = nome_arquivo_personagem.replace('.json', '')
    pasta_memoria = f"./memorias/memoria_{nome_limpo}"

    # 2. Configura Memória de Mundo (O que eu sei dos livros)
    pasta_mundo = "./memorias/mundo_conhecimento"
    contexto_extra = ""

    # Se existe conhecimento de mundo, busca informações relevantes
    if os.path.exists(pasta_mundo) and os.listdir(pasta_mundo):
        try:
            db_mundo = Chroma(persist_directory=pasta_mundo, embedding_function=embeddings)
            # Busca os 2 trechos mais parecidos com a pergunta do usuário
            docs = db_mundo.similarity_search(texto_usuario, k=2)
            contexto_extra = "\n".join([doc.page_content for doc in docs])
        except Exception as e:
            print(f"Erro ao ler mundo: {e}")

    # 3. Prepara a memória da conversa
    vectorstore = Chroma(persist_directory=pasta_memoria, embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs=dict(k=3))
    memory = VectorStoreRetrieverMemory(retriever=retriever)

    # 4. Prompt Turbinado (Identidade + Mundo + Conversa)
    texto_sistema = f"""
    VOCÊ É: {dados_personagem['nome']}
    ARQUÉTIPO: {dados_personagem.get('arquetipo', 'Desconhecido')}
    PERSONALIDADE: {", ".join(dados_personagem.get('tracos_personalidade', []))}
    OBJETIVO: {dados_personagem.get('objetivo_atual', 'Nenhum')}

    📚 CONHECIMENTO DO MUNDO (Use isso para responder perguntas sobre lore/história):
    {contexto_extra}

    ⚠️ INSTRUÇÕES:
    1. Responda como o personagem.
    2. Se a informação estiver no 'CONHECIMENTO DO MUNDO', use-a.
    3. Pense antes de responder na tag [PENSAMENTO].
    4. Responda na tag [FALA].

    HISTÓRICO DA CONVERSA:
    {{history}}
    """

    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(texto_sistema),
        HumanMessagePromptTemplate.from_template("{input}")
    ])

    llm = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0.7)

    chain = ConversationChain(llm=llm, prompt=prompt_template, memory=memory)
    return chain.predict(input=texto_usuario)