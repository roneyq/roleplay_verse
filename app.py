import streamlit as st
import sys
import os
import re
import time

# --- CONFIGURAÇÃO INICIAL (DEVE SER A PRIMEIRA LINHA) ---
st.set_page_config(page_title="Roleplay Verse", page_icon="🔮", layout="wide")

# --- HACK DO BANCO DE DADOS (Para Nuvem) ---
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

# --- IMPORTS ---
from brain import *

# --- CSS AVANÇADO ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp { background-color: #000000; color: #e0e0e0; font-family: 'Inter', sans-serif; }
    #MainMenu, footer, header { visibility: hidden; }

    /* Login Box */
    .login-box {
        padding: 2rem; border-radius: 15px; background: #1a1a1a;
        border: 1px solid #333; max-width: 400px; margin: auto;
    }

    div.stButton > button {
        background: linear-gradient(90deg, #8A2387, #E94057, #F27121);
        color: white; border: none; border-radius: 25px;
        padding: 10px 24px; font-weight: 600; width: 100%;
        transition: transform 0.2s;
    }
    div.stButton > button:hover { transform: scale(1.02); color: white; }

    /* Cards e Chats (Igual anterior) */
    .char-card { background-color: #1a1a1a; border-radius: 15px; padding: 15px; border: 1px solid #333; margin-bottom: 20px; text-align: center; }
    .char-card img { border-radius: 10px; width: 100%; height: 200px; object-fit: cover; }
    .bubble-user { background-color: #2b2b2b; color: #fff; padding: 12px 18px; border-radius: 18px 18px 0 18px; align-self: flex-end; max-width: 85%; margin-left: auto; border: 1px solid #444; margin-bottom: 10px; }
    .bubble-ai { background: linear-gradient(135deg, #2a0845 0%, #6441A5 100%); color: #fff; padding: 12px 18px; border-radius: 18px 18px 18px 0; align-self: flex-start; max-width: 85%; margin-bottom: 10px; }

    /* Menu Navegação */
    .nav-btn-selected > button { background: #ffffff !important; color: #000000 !important; border: 2px solid #ffffff !important; }
    .nav-btn-unselected > button { background: transparent !important; color: #666666 !important; border: 1px solid #333 !important; }
</style>
""", unsafe_allow_html=True)


# --- FUNÇÕES DE NAVEGAÇÃO E AVATAR ---
def get_avatar_url(arquetipo, seed):
    arq = arquetipo.lower()
    bg = "b6e3f4"
    if "detetive" in arq: bg = "c0aede"
    return f"https://api.dicebear.com/7.x/adventurer/svg?seed={seed}&backgroundColor={bg}"


def navegar_para(aba):
    st.session_state['aba_ativa'] = aba
    st.rerun()


# --- ESTADO DE SESSÃO ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = None
if 'role' not in st.session_state: st.session_state['role'] = None
if 'aba_ativa' not in st.session_state: st.session_state['aba_ativa'] = 'explorar'
if 'char_atual' not in st.session_state: st.session_state['char_atual'] = None
if 'perfil_visualizar' not in st.session_state: st.session_state['perfil_visualizar'] = None

# =========================================================
# TELA 0: LOGIN E REGISTRO
# =========================================================
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align: center'>🔐 Roleplay Verse</h1>", unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["Entrar", "Criar Conta"])

        with tab_login:
            user = st.text_input("Usuário")
            pwd = st.text_input("Senha", type="password")
            if st.button("LOGIN", key="btn_login"):
                role = verificar_login(user, pwd)
                if role:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = user
                    st.session_state['role'] = role
                    st.success(f"Bem-vindo, {user}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

        with tab_register:
            new_user = st.text_input("Novo Usuário")
            new_pwd = st.text_input("Nova Senha", type="password")
            if st.button("CRIAR CONTA"):
                if criar_novo_usuario(new_user, new_pwd):
                    st.success("Conta criada! Faça login.")
                else:
                    st.error("Usuário já existe.")

        st.info("💡 **Admin Login:** user: `admin` | pass: `admin123`")

else:
    # =========================================================
    # APLICAÇÃO PRINCIPAL (SÓ CARREGA SE LOGADO)
    # =========================================================

    # Header com Logout
    c_head1, c_head2 = st.columns([8, 1])
    with c_head2:
        if st.button("Sair 🚪"):
            st.session_state['logged_in'] = False
            st.session_state['username'] = None
            st.rerun()

    # --- BARRA DE NAVEGAÇÃO ---
    c_nav1, c_nav2, c_nav3 = st.columns(3)
    aba = st.session_state['aba_ativa']

    with c_nav1:
        cls = "nav-btn-selected" if aba == 'explorar' else "nav-btn-unselected"
        st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
        if st.button("🔥 Explorar", use_container_width=True): navegar_para('explorar')
        st.markdown('</div>', unsafe_allow_html=True)
    with c_nav2:
        cls = "nav-btn-selected" if aba == 'chat' else "nav-btn-unselected"
        st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
        if st.button("💬 Chat", use_container_width=True): navegar_para('chat')
        st.markdown('</div>', unsafe_allow_html=True)
    with c_nav3:
        cls = "nav-btn-selected" if aba == 'eu' else "nav-btn-unselected"
        st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
        if st.button("👤 Eu", use_container_width=True): navegar_para('eu')
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    usuario_atual = st.session_state['username']
    is_admin = st.session_state['role'] == 'admin'

    # --- TELA 1: EXPLORAR ---
    if aba == 'explorar':
        if st.session_state['perfil_visualizar']:
            # ... (Lógica de Perfil Detalhado) ...
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
                visib = "🌎 Global" if p.get("visibility") == "public" else "🔒 Privado"
                st.caption(f"{p['arquetipo']} | {visib}")
                st.info(f"Objetivo: {p.get('objetivo_atual', '...')}")

                if st.button("💬 Iniciar Conversa", key="start_chat"):
                    st.session_state['char_atual'] = nome_char
                    st.session_state['perfil_visualizar'] = None
                    navegar_para('chat')

        else:
            # FEED (FILTRADO POR USUÁRIO)
            st.subheader(f"Olá, {usuario_atual}!")
            # Passamos o usuario e o admin flag para filtrar
            arquivos = listar_personagens(usuario_atual, is_admin)

            if not arquivos:
                st.warning("Nenhum personagem disponível. Crie um na aba 'Eu'.")

            cols = st.columns(2)
            for i, arquivo in enumerate(arquivos):
                p = carregar_personagem(arquivo)
                nome_limpo = arquivo.replace(".json", "")
                avatar = get_avatar_url(p['arquetipo'], p['nome'])

                with cols[i % 2]:
                    # Indicador Visual de Privado/Público
                    icon = "🌎" if p.get("visibility") == "public" else "🔒"
                    st.markdown(f"""
                    <div class="char-card">
                        <div style="position:absolute; top:10px; right:10px; background:black; padding:5px; border-radius:50%;">{icon}</div>
                        <img src="{avatar}">
                        <div class="char-name">{p['nome']}</div>
                        <div class="char-desc">{p['arquetipo']}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("👤 Ver", key=f"p_{i}"):
                            st.session_state['perfil_visualizar'] = nome_limpo
                            st.rerun()
                    with c2:
                        if st.button("💬 Chat", key=f"c_{i}"):
                            st.session_state['char_atual'] = nome_limpo
                            navegar_para('chat')

    # --- TELA 2: CHAT ---
    elif aba == 'chat':
        char_sel = st.session_state.get('char_atual')
        if not char_sel:
            st.info("Escolha alguém no Explorar.")
        else:
            # AGORA PASSAMOS O USUARIO_ATUAL PARA AS FUNÇÕES DE CHAT
            p_atual = carregar_personagem(f"{char_sel}.json")
            msgs = carregar_mensagens_salvas(f"{char_sel}.json", usuario_atual)

            c_v, c_t, c_l = st.columns([1, 4, 1])
            with c_v:
                if st.button("⬅️"):
                    st.session_state['char_atual'] = None
                    navegar_para('explorar')
            with c_t:
                st.markdown(f"<h3 style='text-align:center'>{p_atual['nome']}</h3>", unsafe_allow_html=True)
            with c_l:
                if st.button("🗑️"):
                    limpar_historico_visual(f"{char_sel}.json", usuario_atual)
                    st.rerun()

            chat_container = st.container(height=400)
            with chat_container:
                for msg in msgs:
                    cls = "bubble-user" if msg["role"] == "user" else "bubble-ai"
                    st.markdown(f"<div class='{cls}'>{msg['content']}</div>", unsafe_allow_html=True)

            if prompt := st.chat_input("Mensagem..."):
                salvar_mensagem_no_historico(f"{char_sel}.json", usuario_atual, "user", prompt)
                st.rerun()

            if msgs and msgs[-1]["role"] == "user":
                with st.spinner("..."):
                    resp = responder_usuario(msgs[-1]["content"], p_atual, f"{char_sel}.json", usuario_atual)
                    resp_limpa = re.sub(r'\[.*?\]', '', resp).strip() or resp
                    salvar_mensagem_no_historico(f"{char_sel}.json", usuario_atual, "assistant", resp_limpa)
                    st.rerun()

    # --- TELA 3: EU (PERFIL E CRIAÇÃO) ---
    elif aba == 'eu':
        st.header("👤 Meu Perfil")
        st.write(f"**Usuário:** {usuario_atual}")
        st.write(f"**Nível:** {'👑 Admin' if is_admin else '🎮 Jogador'}")

        # CONTROLE DE LIMITE DE CRIAÇÃO
        chars_meus = contar_meus_personagens(usuario_atual)
        limite = 4

        # BLOCO DE CRIAÇÃO
        with st.expander("🛠️ Criar Novo Personagem", expanded=True):
            if not is_admin and chars_meus >= limite:
                st.error(f"Você atingiu o limite de {limite} personagens privados.")
            else:
                with st.form("new_char"):
                    nome = st.text_input("Nome")
                    arq = st.text_input("Arquétipo")
                    hist = st.text_area("História")

                    # VISIBILIDADE (SÓ ADMIN ESCOLHE)
                    visibilidade = "private"
                    if is_admin:
                        visibilidade = st.selectbox("Visibilidade", ["public", "private"], index=0)
                        st.caption("Public = Todos veem. Private = Só você vê.")
                    else:
                        st.caption("🔒 Seu personagem será privado (só você e o admin veem).")

                    if st.form_submit_button("Criar"):
                        criar_personagem_avancado(
                            nome, arq, "Neutro", "Nenhum", "Conversar", "Casual", "Médio", "Nenhum", hist,
                            dono=usuario_atual,
                            visibilidade=visibilidade
                        )
                        st.success("Personagem criado!")
                        time.sleep(1)
                        st.rerun()

        # BLOCO DE UPLOAD (SÓ ADMIN)
        if is_admin:
            with st.expander("📚 Conhecimento Global (Admin Only)"):
                pdf = st.file_uploader("PDF Global", type="pdf")
                if pdf:
                    msg = processar_conhecimento_mundo(pdf)
                    st.success(msg)