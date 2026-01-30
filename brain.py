import os
import json
import hashlib
import tempfile
from langchain_groq import ChatGroq
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain.memory import ConversationBufferMemory  # Fallback simples e robusto
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURAÇÕES GLOBAIS ---
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


# --- SISTEMA DE USUÁRIOS E SEGURANÇA ---
def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()


def carregar_usuarios():
    if not os.path.exists("usuarios.json"):
        # Cria o Admin padrão se não existir
        admin_padrao = {
            "admin": {
                "senha": hash_senha("admin123"),  # Senha inicial
                "role": "admin",
                "chars_criados": 0
            }
        }
        with open("usuarios.json", "w") as f: json.dump(admin_padrao, f)

    with open("usuarios.json", "r") as f: return json.load(f)


def salvar_usuarios(dados):
    with open("usuarios.json", "w") as f: json.dump(dados, f, indent=4)


def verificar_login(usuario, senha):
    users = carregar_usuarios()
    if usuario in users and users[usuario]["senha"] == hash_senha(senha):
        return users[usuario]["role"]
    return None


def criar_novo_usuario(usuario, senha):
    users = carregar_usuarios()
    if usuario in users: return False  # Já existe
    users[usuario] = {
        "senha": hash_senha(senha),
        "role": "player",
        "chars_criados": 0
    }
    salvar_usuarios(users)
    return True


# --- GERENCIAMENTO DE PERSONAGENS COM PERMISSÃO ---
def listar_personagens(usuario_logado, is_admin):
    if not os.path.exists("personagens"): os.makedirs("personagens")
    todos_arquivos = [f for f in os.listdir("personagens") if f.endswith(".json")]

    permitidos = []
    for arquivo in todos_arquivos:
        try:
            with open(f"personagens/{arquivo}", "r", encoding="utf-8") as f:
                dados = json.load(f)

            # REGRAS DE VISIBILIDADE:
            # 1. Admin vê tudo.
            # 2. Personagem é Público (Global).
            # 3. Personagem é Privado mas fui eu (usuário) que criei.
            dono = dados.get("owner", "admin")  # Se não tiver dono, assume admin (legado)
            visibilidade = dados.get("visibility", "public")

            if is_admin:
                permitidos.append(arquivo)
            elif visibilidade == "public":
                permitidos.append(arquivo)
            elif dono == usuario_logado:
                permitidos.append(arquivo)
        except:
            continue

    return permitidos


def carregar_personagem(arquivo):
    with open(f"personagens/{arquivo}", "r", encoding="utf-8") as f:
        return json.load(f)


def contar_meus_personagens(usuario_logado):
    if not os.path.exists("personagens"): return 0
    count = 0
    for arquivo in os.listdir("personagens"):
        if arquivo.endswith(".json"):
            with open(f"personagens/{arquivo}", "r", encoding="utf-8") as f:
                d = json.load(f)
                if d.get("owner") == usuario_logado:
                    count += 1
    return count


def criar_personagem_avancado(nome, arquetipo, tracos, valores, objetivo, estilo, maleabilidade, segredo, historia,
                              dono, visibilidade="private"):
    dados = {
        "nome": nome,
        "arquetipo": arquetipo,
        "tracos_personalidade": [t.strip() for t in tracos.split(',')],
        "valores_inagociaveis": [v.strip() for v in valores.split(',')],
        "objetivo_atual": objetivo,
        "estilo_fala": [e.strip() for e in estilo.split(',')],
        "nivel_maleabilidade": maleabilidade,
        "segredo_obscuro": segredo,
        "lore": historia,
        "owner": dono,  # NOVO: Quem criou
        "visibility": visibilidade  # NOVO: public (todos) ou private (só dono)
    }

    if not os.path.exists("personagens"): os.makedirs("personagens")
    with open(f"personagens/{nome}.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)


# --- HISTÓRICO ISOLADO POR USUÁRIO ---
def carregar_mensagens_salvas(nome_personagem_arquivo, usuario_logado):
    # O arquivo de histórico agora tem o NOME DO USUÁRIO no nome
    # Ex: Aria_admin_chat.json ou Aria_jogador1_chat.json
    nome_limpo = nome_personagem_arquivo.replace('.json', '')
    arquivo_hist = f"historicos/{nome_limpo}_{usuario_logado}_chat.json"

    if not os.path.exists("historicos"): os.makedirs("historicos")

    if os.path.exists(arquivo_hist):
        with open(arquivo_hist, "r", encoding="utf-8") as f: return json.load(f)
    return []


def salvar_mensagem_no_historico(nome_personagem_arquivo, usuario_logado, role, content):
    msgs = carregar_mensagens_salvas(nome_personagem_arquivo, usuario_logado)
    msgs.append({"role": role, "content": content})

    nome_limpo = nome_personagem_arquivo.replace('.json', '')
    arquivo_hist = f"historicos/{nome_limpo}_{usuario_logado}_chat.json"

    with open(arquivo_hist, "w", encoding="utf-8") as f:
        json.dump(msgs, f, ensure_ascii=False, indent=4)


def limpar_historico_visual(nome_personagem_arquivo, usuario_logado):
    nome_limpo = nome_personagem_arquivo.replace('.json', '')
    arquivo_hist = f"historicos/{nome_limpo}_{usuario_logado}_chat.json"
    if os.path.exists(arquivo_hist): os.remove(arquivo_hist)


# --- RAG / PDF (Mantido Igual) ---
def processar_conhecimento_mundo(arquivo_pdf_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(arquivo_pdf_bytes.read())
        tmp_path = tmp_file.name

    loader = PyPDFLoader(tmp_path)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)

    pasta_mundo = "./memorias/mundo_conhecimento"
    Chroma.from_documents(documents=chunks, embedding=embeddings, persist_directory=pasta_mundo)
    os.remove(tmp_path)
    return f"Conhecimento absorvido! {len(chunks)} fragmentos lidos."


# --- CÉREBRO LLM ---
def responder_usuario(texto_usuario, dados_personagem, nome_arquivo_personagem, usuario_logado):
    # Memória Específica do Usuário + Personagem
    nome_limpo = nome_arquivo_personagem.replace('.json', '')
    pasta_memoria = f"./memorias/memoria_{nome_limpo}_{usuario_logado}"  # Pasta única para cada user

    # RAG de Mundo
    pasta_mundo = "./memorias/mundo_conhecimento"
    contexto_extra = ""
    if os.path.exists(pasta_mundo) and os.listdir(pasta_mundo):
        try:
            db_mundo = Chroma(persist_directory=pasta_mundo, embedding_function=embeddings)
            docs = db_mundo.similarity_search(texto_usuario, k=2)
            contexto_extra = "\n".join([doc.page_content for doc in docs])
        except:
            pass

    # Memória Conversacional (Simples para garantir funcionamento)
    memory = ConversationBufferMemory()
    # (Nota: Em produção, usaríamos VectorStoreMemory persistente, mas buffer é mais seguro para testes rápidos)

    texto_sistema = f"""
    VOCÊ É: {dados_personagem['nome']}
    ARQUÉTIPO: {dados_personagem.get('arquetipo', 'Desconhecido')}
    PERSONALIDADE: {", ".join(dados_personagem.get('tracos_personalidade', []))}
    OBJETIVO: {dados_personagem.get('objetivo_atual', 'Nenhum')}

    📚 CONHECIMENTO DO MUNDO:
    {contexto_extra}

    ⚠️ INSTRUÇÕES:
    1. Responda APENAS como o personagem.
    2. Use tags [PENSAMENTO] e [FALA].

    HISTÓRICO RECENTE:
    {{history}}
    """

    prompt_template = PromptTemplate(input_variables=["history", "input"],
                                     template=texto_sistema + "\nUsuário: {input}\nIA:")
    llm = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0.7)
    chain = ConversationChain(llm=llm, prompt=prompt_template, memory=memory)

    return chain.predict(input=texto_usuario)