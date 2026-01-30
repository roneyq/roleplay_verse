import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# Importação de memória compatível com LangChain 1.x
try:
    from langchain.memory import VectorStoreRetrieverMemory
except ImportError:
    from langchain_community.memory import VectorStoreRetrieverMemory

from langchain_core.prompts import PromptTemplate
from langchain_classic.chains import ConversationChain

# Inicialização Global
load_dotenv()

# Inicialização Global
load_dotenv()

# --- DIAGNÓSTICO (Adicione isto) ---
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("❌ ERRO CRÍTICO: Chave API não encontrada! Verifique o arquivo .env")
elif api_key.startswith("gsk_"):
    print(f"✅ Chave carregada: {api_key[:4]}...{api_key[-4:]}")
else:
    print("⚠️ AVISO: A chave não parece ser uma chave Groq válida (deve começar com gsk_)")
# -----------------------------------

# Carregamos o modelo de Embeddings UMA VEZ só (para economizar tempo)
print("Carregando modelo de Embeddings...")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def carregar_personagem(nome_arquivo):
    """Lê o JSON do personagem selecionado"""
    caminho = os.path.join("personagens", nome_arquivo)
    with open(caminho, 'r', encoding='utf-8') as f:
        return json.load(f)


def listar_personagens():
    """Devolve uma lista com os nomes dos arquivos .json na pasta"""
    if not os.path.exists("personagens"):
        os.makedirs("personagens")
    arquivos = [f for f in os.listdir("personagens") if f.endswith(".json")]
    return arquivos


def criar_personagem_avancado(nome, arquetipo, tracos, valores, objetivo, estilo, maleabilidade, segredo, historia):
    """Cria um JSON com a estrutura psicológica avançada"""

    # Transforma strings separadas por vírgula em listas
    lista_tracos = [t.strip() for t in tracos.split(',')]
    lista_valores = [v.strip() for v in valores.split(',')]
    lista_estilo = [e.strip() for e in estilo.split(',')]

    dados = {
        "nome": nome,
        "arquetipo": arquetipo,
        "tracos_personalidade": lista_tracos,
        "valores_inagociaveis": lista_valores,
        "objetivo_atual": objetivo,
        "estilo_fala": lista_estilo,
        "nivel_maleabilidade": maleabilidade,
        "segredo_obscuro": segredo,
        "lore": historia
    }

    # Sanitiza nome do arquivo
    nome_arquivo = "".join([c for c in nome if c.isalpha() or c.isdigit() or c == ' ']).rstrip() + ".json"

    if not os.path.exists("personagens"):
        os.makedirs("personagens")

    caminho = os.path.join("personagens", nome_arquivo)
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)
    return nome_arquivo


# No topo do arquivo, adicione estas importações novas:
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, \
    MessagesPlaceholder


# ... (o resto das funções carregar/criar continua igual) ...

def responder_usuario(texto, dados_personagem, nome_arquivo_personagem):
    # 1. Define pasta de memória
    nome_limpo = nome_arquivo_personagem.replace('.json', '')
    pasta_memoria = f"./memorias/memoria_{nome_limpo}"

    # 2. Conecta ao banco (Chroma)
    vectorstore = Chroma(persist_directory=pasta_memoria, embedding_function=embeddings)

    # AJUSTE: Buscamos apenas 1 ou 2 memórias passadas para não poluir
    retriever = vectorstore.as_retriever(search_kwargs=dict(k=2))
    memory = VectorStoreRetrieverMemory(retriever=retriever)

    # 3. Prompt Blindado (ChatPromptTemplate)
    # Aqui separamos explicitamente o "Sistema" do "Humano"

    texto_sistema = f"""
    VOCÊ ESTÁ INCORPORANDO: {dados_personagem['nome']}
    ---
    ARQUÉTIPO: {dados_personagem.get('arquetipo', 'Indefinido')}
    PERSONALIDADE: {", ".join(dados_personagem.get('tracos_personalidade', []))}
    OBJETIVO: {dados_personagem.get('objetivo_atual', 'Nenhum')}
    ESTILO DE FALA: {", ".join(dados_personagem.get('estilo_fala', []))}
    VALORES: {", ".join(dados_personagem.get('valores_inagociaveis', []))}
    MALEABILIDADE: {dados_personagem.get('nivel_maleabilidade', 'Médio')}
    SEGREDO: {dados_personagem.get('segredo_obscuro', '')}
    LORE: {dados_personagem.get('lore', '')}
    ---

    INSTRUÇÕES DE PENSAMENTO (Oculto):
    1. Antes de responder, gere um pensamento interno na tag [PENSAMENTO].
    2. Avalie a intenção do usuário e se ela fere seus valores.
    3. Depois, gere sua resposta na tag [FALA].
    4. JAMAIS saia do personagem.

    LEMBRANÇAS RELEVANTES DO PASSADO:
    {{history}}
    """

    # Montagem do Chat
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(texto_sistema),
        HumanMessagePromptTemplate.from_template("{input}")
    ])

    # 4. LLM Llama 3.1
    llm = ChatGroq(
        model_name="llama-3.1-8b-instant",
        temperature=0.6,  # Diminuí um pouco a temperatura para ele alucinar menos
        groq_api_key=os.getenv("GROQ_API_KEY")
    )

    # 5. Gera resposta
    chain = ConversationChain(llm=llm, prompt=prompt_template, memory=memory)
    return chain.predict(input=texto)


    PROMPT = PromptTemplate(input_variables=["history", "input"], template=template)


# --- NOVAS FUNÇÕES: GERENCIAMENTO DE HISTÓRICO VISUAL (WHATSAPP STYLE) ---

def carregar_mensagens_salvas(nome_arquivo_personagem):
    """Lê o histórico de chat (JSON) para a interface"""
    # Cria pasta se não existir
    if not os.path.exists("historicos"):
        os.makedirs("historicos")

    nome_chat = nome_arquivo_personagem.replace(".json", "_chat.json")
    caminho = os.path.join("historicos", nome_chat)

    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    return []  # Retorna lista vazia se não houver histórico


def salvar_mensagem_no_historico(nome_arquivo_personagem, role, content):
    """Salva uma nova mensagem no arquivo JSON de histórico"""
    mensagens = carregar_mensagens_salvas(nome_arquivo_personagem)

    # Adiciona a nova mensagem com timestamp (opcional, mas bom para o futuro)
    mensagens.append({"role": role, "content": content})

    nome_chat = nome_arquivo_personagem.replace(".json", "_chat.json")
    caminho = os.path.join("historicos", nome_chat)

    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(mensagens, f, ensure_ascii=False, indent=4)


def limpar_historico_visual(nome_arquivo_personagem):
    """Apaga apenas o histórico visual, mantendo a memória da IA"""
    nome_chat = nome_arquivo_personagem.replace(".json", "_chat.json")
    caminho = os.path.join("historicos", nome_chat)
    if os.path.exists(caminho):
        os.remove(caminho)

