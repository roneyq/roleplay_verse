import streamlit as st
import sys
import os
import re
import time
import random

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

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Roleplay Verse", page_icon="🔮", layout="wide")

# --- CSS AVANÇADO (VISUAL APP) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    /* GERAL */
    .stApp { background-color: #000000; color: #e0e0e0; font-family: 'Inter', sans-serif; }
    #MainMenu, footer, header { visibility: hidden; }

    /* BOTÕES GERAIS */
    div.stButton > button {
        background: linear-gradient(90deg, #8A2387, #E94057, #F27121);
        color: white; border: none; border-radius: 25px;
        padding: 10px 24px; font-weight: 600; width: 100%;
        transition: transform 0.2s;
        box-shadow: 0 4px 10px rgba(233, 64, 87, 0.3);
    }
    div.stButton > button:hover { transform: scale(1.02); color: white; }

    /* BOTÃO DE MENU (NAVEGAÇÃO) - ESTILO ABA */
    .nav-btn-selected > button {
        background: #ffffff !important;
        color: #000000 !important;
        border: 2px solid #ffffff !important;
    }
    .nav-btn-unselected > button {
        background: transparent !important;
        color: #666666 !important;
        border: 1px solid #333 !important;
    }

    /* CARDS */
    .char-card {
        background-color: #1a1a1a; border-radius: 15px; padding: 15px;
        border: 1px solid #333; margin-bottom: 20px; text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); position: relative;
    }
    .char-card img {
        border-radius: 10px; width: 100%; height: 200px; object-fit: cover; margin-bottom: 10px;
    }
    .char-name { font-size: 1.1rem; font-weight: 800; color: #fff; margin-bottom: 5px; }
    .char-desc { font-size: 0.8rem; color: #888; height: 35px; overflow: hidden; margin-bottom: 10px;}

    /* CHAT BUBBLES */
    .bubble-user {
        background-color: #2b2b2b; color: #fff; padding: 12px 18px;
        border-radius: 18px 18px 0 18px; align-self: flex-end;
        max-width: 85%; margin-left: auto; border: 1px solid #444; margin-bottom: 10px;
    }
    .bubble-ai {
        background: linear-gradient(135deg, #2a0845 0%, #6441A5 100%);
        color: #fff; padding: 12px 18px; border-radius: 18px 18px 18px 0;
        align-self: flex-start; max-width: 85%; margin-bottom: 10px;
    }

    /* INPUT FIXO EMBAIXO (Simulação) */
    .stTextInput > div > div > input {
        background-color: #1a1a1a; color: white; border: 1px solid #333; border-radius: 20px;
    }
</style>
""", unsafe_allow_html=True)


# --- FUNÇÕES AUXILIARES ---
def get_avatar_url(arquetipo, seed):
    arq = arquetipo.lower()
    base = "https://api.dicebear.com/7.x/adventurer/svg"
    bg = "b6e3f4"
    if "detetive" in arq: bg = "c0aede"
    if "mago" in arq: bg = "ffdfbf"
    return f"{base}?seed={seed}&backgroundColor={bg}"


def navegar_para(aba):
    st.session_state['aba_ativa'] = aba
    st.rerun()


# --- ESTADO INICIAL ---
if 'aba_ativa' not in st.session_state: st.session_state['aba_ativa'] = 'explorar'
if 'char_atual' not in st.session_state: st.session_state['char_atual'] = None
if 'perfil_visualizar' not in st.session_state: st.session_state['perfil_visualizar'] = None

# --- BARRA DE NAVEGAÇÃO CUSTOMIZADA (TOPO) ---
# Isso substitui o st.tabs e permite controle total
c_nav1, c_nav2, c_nav3 = st.columns(3)

# Botão Explorar
classe_btn1 = "nav-btn-selected" if st.session_state['aba_ativa'] == 'explorar' else "nav-btn-unselected"
with c_nav1:
    st.markdown(f'<div class="{classe_btn1}">', unsafe_allow_html=True)
    if st.button("🔥 Explorar", key="nav_explorar", use_container_width=True):
        navegar_para('explorar')
    st.markdown('</div>', unsafe_allow_html=True)

# Botão Chat
classe_btn2 = "nav-btn-selected" if st.session_state['aba_ativa'] == 'chat' else "nav-btn-unselected"
with c_nav2:
    st.markdown(f'<div class="{classe_btn2}">', unsafe_allow_html=True)
    if st.button("💬 Chat", key="nav_chat", use_container_width=True):
        navegar_para('chat')
    st.markdown('</div>', unsafe_allow_html=True)

# Botão Eu
classe_btn3 = "nav-btn-selected" if st.session_state['aba_ativa'] == 'eu' else "nav-btn-unselected"
with c_nav3:
    st.markdown(f'<div class="{classe_btn3}">', unsafe_allow_html=True)
    if st.button("👤 Eu", key="nav_eu", use_container_width=True):
        navegar_para('eu')
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# =========================================================
# LÓGICA DE EXIBIÇÃO DAS TELAS
# =========================================================

# --- TELA 1: EXPLORAR ---
if st.session_state['aba_ativa'] == 'explorar':

    # Se estiver vendo um perfil específico
    if st.session_state['perfil_visualizar']:
        nome_char = st.session_state['perfil_visualizar']
        p = carregar_personagem(f"{nome_char}.json")
        avatar = get_avatar_url(p['arquetipo'], p['nome'])

        if st.button("⬅️ Voltar"):
            st.session_state['perfil_visualizar'] = None
            st.rerun()

        col_img, col_info = st.columns([1, 2])
        with col_img:
            st.image(avatar, use_container_width=True)
        with col_info:
            st.title(p['nome'])
            st.caption(p['arquetipo'])
            st.info(f"Objective: {p.get('objetivo_atual', '...')}")

            # AQUI ESTÁ A CORREÇÃO MÁGICA
            # Ao clicar em Chat, mudamos a aba ativa para 'chat' manualmente
            if st.button("💬 Iniciar Conversa Agora", key="btn_start_chat_profile"):
                st.session_state['char_atual'] = nome_char
                st.session_state['perfil_visualizar'] = None
                navegar_para('chat')  # <--- FORÇA A IDA PARA O CHAT

        st.markdown("#### 📸 Fotos Privadas")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.image("https://placehold.co/150/2a0845/FFF?text=Open", caption="Pública")
        with c2:
            st.image("https://placehold.co/150/000/333?text=Locked", caption="🔒 Premium")
        with c3:
            st.image("https://placehold.co/150/000/333?text=Locked", caption="🔒 Nível 10")

    else:
        # Feed Principal
        st.subheader("Quem você quer conhecer?")
        arquivos = listar_personagens()
        cols = st.columns(2)

        for i, arquivo in enumerate(arquivos):
            p = carregar_personagem(arquivo)
            nome_limpo = arquivo.replace(".json", "")
            avatar = get_avatar_url(p['arquetipo'], p['nome'])

            with cols[i % 2]:
                # Card HTML
                st.markdown(f"""
                <div class="char-card">
                    <img src="{avatar}">
                    <div class="char-name">{p['nome']}</div>
                    <div class="char-desc">{p['arquetipo']}</div>
                </div>
                """, unsafe_allow_html=True)

                c_a, c_b = st.columns(2)
                with c_a:
                    if st.button("👤 Perfil", key=f"btn_perf_{i}"):
                        st.session_state['perfil_visualizar'] = nome_limpo
                        st.rerun()
                with c_b:
                    # BOTÃO CHAT NO FEED
                    if st.button("💬 Chat", key=f"btn_chat_feed_{i}"):
                        st.session_state['char_atual'] = nome_limpo
                        navegar_para('chat')  # <--- FORÇA A MUDANÇA DE TELA

# --- TELA 2: CHAT ---
elif st.session_state['aba_ativa'] == 'chat':

    char_selecionado = st.session_state.get('char_atual')

    if not char_selecionado:
        st.info("👈 Ninguém selecionado. Vá em 'Explorar' primeiro.")
        st.markdown("#### Histórico Recente")
        # Lista de recentes para facilitar
        arquivos = listar_personagens()
        for arquivo in arquivos:
            nome = arquivo.replace(".json", "")
            if st.button(f"➡️ Retomar com {nome}", key=f"retomar_{nome}"):
                st.session_state['char_atual'] = nome
                st.rerun()
    else:
        # Chat Ativo
        p_atual = carregar_personagem(f"{char_selecionado}.json")
        msgs = carregar_mensagens_salvas(f"{char_selecionado}.json")

        # Header do Chat
        c_voltar, c_tit, c_menu = st.columns([1, 4, 1])
        with c_voltar:
            if st.button("⬅️"):
                st.session_state['char_atual'] = None
                navegar_para('explorar')
        with c_tit:
            st.markdown(f"<h3 style='text-align: center; margin: 0;'>{p_atual['nome']}</h3>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; color: gray; margin: 0;'>{p_atual['arquetipo']}</p>",
                        unsafe_allow_html=True)
        with c_menu:
            if st.button("🗑️"):
                limpar_historico_visual(f"{char_selecionado}.json")
                st.rerun()

        st.markdown("---")

        # Área de Mensagens (Com Scroll automático pelo container)
        chat_container = st.container(height=500)
        with chat_container:
            if not msgs:
                st.caption(f"Inicie a conversa com {p_atual['nome']}...")

            for msg in msgs:
                classe = "bubble-user" if msg["role"] == "user" else "bubble-ai"
                st.markdown(f"<div class='{classe}'>{msg['content']}</div>", unsafe_allow_html=True)

        # Input de Texto
        if prompt := st.chat_input("Digite sua mensagem..."):
            salvar_mensagem_no_historico(f"{char_selecionado}.json", "user", prompt)
            st.rerun()  # Atualiza rápido para mostrar msg do user

        # Processamento IA (Pós-render)
        if msgs and msgs[-1]["role"] == "user":
            with st.spinner(f"{p_atual['nome']} está digitando..."):
                resp = responder_usuario(msgs[-1]["content"], p_atual, f"{char_selecionado}.json")
                # Limpa tags para o chat visual
                texto_limpo = re.sub(r'\[.*?\]', '', resp).strip() or resp
                salvar_mensagem_no_historico(f"{char_selecionado}.json", "assistant", texto_limpo)
                st.rerun()

# --- TELA 3: EU (CONFIGS) ---
elif st.session_state['aba_ativa'] == 'eu':
    st.header("👤 Meu Perfil")

    with st.expander("⚙️ Configurações"):
        st.toggle("Notificações", True)
        st.selectbox("Idioma", ["Português", "English"])

    with st.expander("🛠️ Criar Personagem"):
        with st.form("criar_p"):
            nome = st.text_input("Nome")
            arq = st.text_input("Arquétipo")
            hist = st.text_area("História")
            if st.form_submit_button("Criar"):
                criar_personagem_avancado(nome, arq, "Normal", "Nenhum", "Conversar", "Casual", "Médio", "Nenhum", hist)
                st.success("Criado!")
                time.sleep(1)
                st.rerun()

    with st.expander("📚 Upload de PDF (Mundo)"):
        pdf = st.file_uploader("Enviar", type="pdf")
        if pdf:
            res = processar_conhecimento_mundo(pdf)
            st.success(res)