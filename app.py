import streamlit as st
import sys
import os
import re
import time
import base64

# --- HACK DO BANCO DE DADOS (Para Nuvem) ---
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

# --- IMPORTS DO CÉREBRO ---
from brain import (
    responder_usuario,
    listar_personagens,
    carregar_personagem,
    criar_personagem_avancado,
    carregar_mensagens_salvas,
    salvar_mensagem_no_historico,
    limpar_historico_visual,
    processar_conhecimento_mundo
)

# --- CONFIGURAÇÃO DA PÁGINA (MOBILE FIRST) ---
st.set_page_config(page_title="Roleplay Verse", page_icon="🔮", layout="wide")

# --- CSS AVANÇADO (ESTILO APP NATIVO) ---
st.markdown("""
<style>
    /* 1. Fundo e Fontes - Estilo Dark Premium */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    .stApp {
        background-color: #000000; /* Preto absoluto como nos prints */
        color: #e0e0e0;
        font-family: 'Inter', sans-serif;
    }

    /* 2. Esconder Elementos Padrão do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 3. Estilização dos Botões (Gradiente Roxo/Rosa) */
    .stButton > button {
        background: linear-gradient(90deg, #8A2387, #E94057, #F27121);
        color: white;
        border: none;
        border-radius: 25px; /* Bem redondo */
        padding: 10px 24px;
        font-weight: 600;
        width: 100%;
        transition: transform 0.2s;
    }
    .stButton > button:hover {
        transform: scale(1.02);
        color: white;
    }

    /* 4. Cartões de Personagem (Feed) */
    .char-card {
        background-color: #1a1a1a;
        border-radius: 15px;
        padding: 15px;
        border: 1px solid #333;
        margin-bottom: 20px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .char-card img {
        border-radius: 10px;
        width: 100%;
        height: 200px;
        object-fit: cover;
        margin-bottom: 10px;
    }
    .char-name {
        font-size: 1.2rem;
        font-weight: 800;
        margin-bottom: 5px;
        color: #fff;
    }
    .char-desc {
        font-size: 0.85rem;
        color: #888;
        margin-bottom: 15px;
        height: 40px;
        overflow: hidden;
    }

    /* 5. Chat Bubbles (Estilo WhatsApp/Messenger) */
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 15px;
        padding-bottom: 100px;
    }
    .bubble-user {
        background-color: #2b2b2b;
        color: #fff;
        padding: 12px 18px;
        border-radius: 18px 18px 0 18px;
        align-self: flex-end;
        max-width: 85%;
        margin-left: auto;
        border: 1px solid #444;
    }
    .bubble-ai {
        background: linear-gradient(135deg, #2a0845 0%, #6441A5 100%); /* Roxo escuro */
        color: #fff;
        padding: 12px 18px;
        border-radius: 18px 18px 18px 0;
        align-self: flex-start;
        max-width: 85%;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    .thought-bubble {
        font-size: 0.8em;
        color: #aaa;
        font-style: italic;
        margin-bottom: 5px;
        border-left: 2px solid #E94057;
        padding-left: 8px;
    }

    /* 6. Tabs Customizadas (Parecer Menu de App) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #0e0e0e;
        padding: 10px;
        border-radius: 20px;
        position: sticky;
        top: 0;
        z-index: 999;
        justify-content: center;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 20px;
        color: #888;
        font-size: 1.2rem; /* Ícones grandes */
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #333;
        color: #fff;
    }

</style>
""", unsafe_allow_html=True)


# --- FUNÇÕES DE AUXÍLIO ---
def separar_pensamento_fala(texto_bruto):
    pensamento = None
    fala = texto_bruto
    if "ESTRUTURA DE PERSONAGEM" in texto_bruto: texto_bruto = texto_bruto.split("ESTRUTURA DE PERSONAGEM")[0]
    padrao = r'\[PENSAMENTO\]:?\s*(.*?)\[FALA\]:?\s*(.*)'
    match = re.search(padrao, texto_bruto, re.DOTALL | re.IGNORECASE)
    if match:
        pensamento = match.group(1).strip()
        fala = match.group(2).strip()
    else:
        fala = re.sub(r'\[PENSAMENTO\]:?|\[FALA\]:?', '', texto_bruto, flags=re.IGNORECASE).strip()
    return pensamento, fala


def get_avatar_url(arquetipo):
    # Simula avatares baseados no arquétipo (pode ser substituído por upload real depois)
    arq = arquetipo.lower()
    if "ladra" in arq or "assassina" in arq: return "https://api.dicebear.com/7.x/adventurer/svg?seed=Aria&backgroundColor=b6e3f4"
    if "detetive" in arq or "policial" in arq: return "https://api.dicebear.com/7.x/adventurer/svg?seed=Marcus&backgroundColor=c0aede"
    if "mago" in arq or "bruxa" in arq: return "https://api.dicebear.com/7.x/adventurer/svg?seed=Mage&backgroundColor=ffdfbf"
    return f"https://api.dicebear.com/7.x/adventurer/svg?seed={arquetipo}"


# --- NAVEGAÇÃO PRINCIPAL (ESTILO TABS DE APP) ---
# Usamos Tabs para simular a barra de baixo/cima do app
tab_explorar, tab_conversas, tab_perfil = st.tabs(["🔥 Explorar", "💬 Conversas", "👤 Perfil"])

# --- 1. ABA EXPLORAR (FEED DE PERSONAGENS) ---
with tab_explorar:
    st.markdown("### ✨ Descobrir Personagens")

    arquivos = listar_personagens()

    # Layout em Grid Responsivo (2 colunas no mobile, 4 no PC)
    cols = st.columns(2) if st.sidebar else st.columns(2)  # Ajuste automático

    for i, arquivo in enumerate(arquivos):
        p = carregar_personagem(arquivo)
        nome = p['nome']
        arq = p['arquetipo']
        desc = p.get('objetivo_atual', 'Sem descrição definida.')
        avatar = get_avatar_url(arq)

        # Distribui os cards nas colunas
        with cols[i % 2]:
            # HTML Card Customizado
            st.markdown(f"""
            <div class="char-card">
                <img src="{avatar}" alt="{nome}">
                <div class="char-name">{nome}</div>
                <div class="char-desc">{desc[:60]}...</div>
            </div>
            """, unsafe_allow_html=True)

            # Botão Streamlit (Funcionalidade)
            if st.button(f"Conversar", key=f"btn_{nome}"):
                st.session_state['aba_ativa'] = 'conversas'
                st.session_state['char_atual'] = arquivo.replace(".json", "")
                st.rerun()

# --- 2. ABA CONVERSAS (CHAT) ---
with tab_conversas:
    # Verifica se tem um chat selecionado
    char_selecionado = st.session_state.get('char_atual')

    if not char_selecionado:
        st.info("👈 Escolha alguém na aba 'Explorar' para começar!")

        # Lista de conversas recentes (Estilo WhatsApp)
        st.markdown("### 🕒 Recentes")
        arquivos = listar_personagens()
        for arquivo in arquivos:
            nome_limpo = arquivo.replace(".json", "")
            if st.button(f"📂 Abrir chat com {nome_limpo}", key=f"hist_{nome_limpo}"):
                st.session_state['char_atual'] = nome_limpo
                st.rerun()

    else:
        # --- INTERFACE DE CHAT ATIVA ---
        p_atual = carregar_personagem(f"{char_selecionado}.json")
        msgs = carregar_mensagens_salvas(f"{char_selecionado}.json")
        avatar_url = get_avatar_url(p_atual['arquetipo'])

        # Cabeçalho do Chat (Botão Voltar + Info)
        col_voltar, col_info = st.columns([1, 4])
        with col_voltar:
            if st.button("⬅️"):
                st.session_state['char_atual'] = None
                st.rerun()
        with col_info:
            st.markdown(f"**{p_atual['nome']}** | *{p_atual['arquetipo']}*")
            if st.button("🗑️ Limpar", key="clean_chat", help="Apagar histórico"):
                limpar_historico_visual(f"{char_selecionado}.json")
                st.rerun()

        st.markdown("---")

        # Container de Mensagens
        chat_container = st.container()
        with chat_container:
            # Renderiza mensagens anteriores
            if "chat_history" not in st.session_state or st.session_state.get("last_char") != char_selecionado:
                st.session_state.chat_history = msgs
                st.session_state.last_char = char_selecionado

            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(f'<div class="bubble-user">{msg["content"]}</div>', unsafe_allow_html=True)
                else:
                    # Tenta separar pensamento se houver, mas no visual final mostramos limpo ou formatado
                    st.markdown(f'<div class="bubble-ai">{msg["content"]}</div>', unsafe_allow_html=True)

        # Input Fixo no Fundo (Simulado)
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form(key="chat_form", clear_on_submit=True):
            cols_input = st.columns([4, 1])
            with cols_input[0]:
                user_input = st.text_input("Mensagem", placeholder="Digite aqui...", label_visibility="collapsed")
            with cols_input[1]:
                enviar = st.form_submit_button("➤")

            if enviar and user_input:
                # 1. Adiciona msg do usuario
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                salvar_mensagem_no_historico(f"{char_selecionado}.json", "user", user_input)

                # 2. Resposta da IA
                with st.spinner(f"{p_atual['nome']} está digitando..."):
                    resposta_full = responder_usuario(user_input, p_atual, f"{char_selecionado}.json")
                    pensamento, fala = separar_pensamento_fala(resposta_full)

                    # Se tiver pensamento, podemos mostrar de forma sutil
                    texto_final = fala
                    if pensamento:
                        texto_final = f"<span class='thought-bubble'>💭 {pensamento}</span><br>{fala}"

                    st.session_state.chat_history.append({"role": "assistant", "content": texto_final})
                    salvar_mensagem_no_historico(f"{char_selecionado}.json", "assistant", texto_final)
                st.rerun()

# --- 3. ABA PERFIL (CONFIG E CRIAÇÃO) ---
with tab_perfil:
    st.header("👤 Meu Perfil")

    with st.expander("🛠️ Criar Novo Personagem", expanded=True):
        st.caption("Dê vida a uma nova IA")
        with st.form("new_char"):
            nome = st.text_input("Nome do Personagem")
            arquetipo = st.text_input("Papel/Profissão (ex: Detetive)")
            # Upload de Foto (Decorativo por enquanto, usamos DiceBear no código)
            foto = st.file_uploader("Foto de Perfil (Opcional)", type=["jpg", "png"])

            historia = st.text_area("História / Personalidade")

            # Campos avançados escondidos para simplificar visual mobile
            if st.checkbox("Mostrar Opções Avançadas"):
                tracos = st.text_input("Traços (separados por vírgula)")
                valores = st.text_input("Valores Inegociáveis")
                objetivo = st.text_input("Objetivo")
                estilo = st.text_input("Estilo de Fala")
            else:
                tracos, valores, objetivo, estilo = "Normal", "Nenhum", "Conversar", "Casual"

            if st.form_submit_button("✨ Criar Personagem"):
                criar_personagem_avancado(nome, arquetipo, tracos, valores, objetivo, estilo, "Racional", "Nenhum",
                                          historia)
                st.success("Criado!")
                time.sleep(1)
                st.rerun()

    with st.expander("📚 Injetar Conhecimento (PDF)"):
        pdf = st.file_uploader("Regras do Mundo / Lore", type="pdf")
        if pdf:
            msg = processar_conhecimento_mundo(pdf)
            st.success(msg)