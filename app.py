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

# --- CSS AVANÇADO (DARK MODE PREMIUM + GALERIA) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    /* GERAL */
    .stApp { background-color: #000000; color: #e0e0e0; font-family: 'Inter', sans-serif; }
    #MainMenu, footer, header { visibility: hidden; }

    /* BOTÕES */
    .stButton > button {
        background: linear-gradient(90deg, #8A2387, #E94057, #F27121);
        color: white; border: none; border-radius: 25px;
        padding: 10px 24px; font-weight: 600; width: 100%;
        transition: transform 0.2s;
    }
    .stButton > button:hover { transform: scale(1.02); color: white; }

    /* BOTÃO SECUNDÁRIO (Cinza/Outline) */
    .btn-secondary {
        background: transparent !important;
        border: 1px solid #555 !important;
        color: #aaa !important;
    }

    /* CARD DE PERSONAGEM (FEED) */
    .char-card {
        background-color: #1a1a1a; border-radius: 15px; padding: 15px;
        border: 1px solid #333; margin-bottom: 20px; text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); position: relative;
    }
    .char-card img {
        border-radius: 10px; width: 100%; height: 250px; object-fit: cover; margin-bottom: 10px;
    }
    .char-name { font-size: 1.2rem; font-weight: 800; color: #fff; }
    .char-desc { font-size: 0.8rem; color: #888; height: 40px; overflow: hidden; margin-bottom: 10px;}

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

    /* GALERIA BLOQUEADA (EFEITO BLUR) */
    .locked-content {
        position: relative; overflow: hidden; border-radius: 10px; margin-bottom: 10px;
    }
    .locked-content img {
        filter: blur(8px); opacity: 0.6; width: 100%; height: 150px; object-fit: cover;
    }
    .lock-icon {
        position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
        font-size: 2rem; color: white; text-shadow: 0 2px 5px rgba(0,0,0,0.8);
    }

    /* PROGRESS BAR CUSTOM */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #8A2387, #F27121);
    }

    /* TABS */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #0e0e0e; padding: 10px; border-radius: 20px;
        position: sticky; top: 0; z-index: 999; justify-content: space-around;
    }
</style>
""", unsafe_allow_html=True)


# --- FUNÇÕES AUXILIARES ---
def get_avatar_url(arquetipo, seed):
    # Gera imagens diferentes baseadas no nome
    arq = arquetipo.lower()
    base = "https://api.dicebear.com/7.x/adventurer/svg"
    if "ladra" in arq: return f"{base}?seed={seed}&backgroundColor=b6e3f4"
    if "detetive" in arq: return f"{base}?seed={seed}&backgroundColor=c0aede"
    return f"{base}?seed={seed}"


def render_galeria_simulada():
    # Simula conteúdo para monetização futura
    st.markdown("#### 📸 Galeria & Mídia")
    c1, c2, c3 = st.columns(3)

    # Foto 1: Desbloqueada
    with c1:
        st.image("https://placehold.co/200x200/2a0845/FFF?text=Desbloqueado", use_container_width=True)
        st.caption("📷 Selfie Matinal")

    # Foto 2: Bloqueada (Premium)
    with c2:
        st.markdown("""
        <div class="locked-content">
            <img src="https://placehold.co/200x200/333/666?text=Private">
            <div class="lock-icon">🔒</div>
        </div>
        """, unsafe_allow_html=True)
        st.caption("💎 Exclusivo (Premium)")

    # Foto 3: Bloqueada (Nível)
    with c3:
        st.markdown("""
        <div class="locked-content">
            <img src="https://placehold.co/200x200/333/666?text=Level+5">
            <div class="lock-icon">🔒</div>
        </div>
        """, unsafe_allow_html=True)
        st.caption("🔓 Requer Nível 5")


# --- NAVEGAÇÃO ---
# Inicializa estado se não existir
if 'aba_ativa' not in st.session_state: st.session_state['aba_ativa'] = 'explorar'
if 'char_atual' not in st.session_state: st.session_state['char_atual'] = None
if 'perfil_visualizar' not in st.session_state: st.session_state[
    'perfil_visualizar'] = None  # Para ver perfil sem conversar

# Tabs principais
tab1, tab2, tab3 = st.tabs(["🔥 Explorar", "💬 Chat", "👤 Eu"])

# --- ABA 1: EXPLORAR (FEED + PERFIL DETALHADO) ---
with tab1:
    # Lógica de Navegação Interna: Grid ou Perfil Detalhado?
    personagem_foco = st.session_state['perfil_visualizar']

    if personagem_foco:
        # --- TELA DE DETALHES DO PERSONAGEM ---
        p = carregar_personagem(f"{personagem_foco}.json")
        img_url = get_avatar_url(p['arquetipo'], p['nome'])

        # Botão Voltar
        if st.button("⬅️ Voltar para o Feed"):
            st.session_state['perfil_visualizar'] = None
            st.rerun()

        # Header do Perfil
        col_img, col_dados = st.columns([1, 2])
        with col_img:
            st.image(img_url, use_container_width=True)
        with col_dados:
            st.title(p['nome'])
            st.subheader(p['arquetipo'])
            st.write(f"📝 *{p.get('objetivo_atual', '...')}.*")

            # Botão de Ação Principal
            if st.button("💬 Começar Conversa", key="btn_start_chat_profile"):
                st.session_state['char_atual'] = personagem_foco
                st.session_state['perfil_visualizar'] = None
                st.rerun()

        st.markdown("---")

        # Stats e Progresso
        st.write("❤️ **Nível de Relacionamento**")
        progresso = random.randint(10, 90)  # Simulação
        st.progress(progresso)
        st.caption(f"Nível {int(progresso / 10)} - {progresso}% para o próximo nível")

        # Características (Tags)
        st.write("🧠 **Personalidade**")
        tracos = p.get('tracos_personalidade', [])
        st.markdown(" ".join([f"`#{t.strip()}`" for t in tracos]))

        st.markdown("---")

        # Galeria (Sistema de Monetização Futuro)
        render_galeria_simulada()

        # Botão Fake de Compra
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💎 Assinar Premium para ver tudo"):
            st.toast("Funcionalidade em breve!", icon="🚧")

    else:
        # --- TELA DE FEED (GRID) ---
        st.markdown("### ✨ Quem você quer conhecer hoje?")
        arquivos = listar_personagens()
        cols = st.columns(2)

        for i, arquivo in enumerate(arquivos):
            p = carregar_personagem(arquivo)
            nome_limpo = arquivo.replace(".json", "")
            avatar = get_avatar_url(p['arquetipo'], p['nome'])

            with cols[i % 2]:
                # Card Visual
                st.markdown(f"""
                <div class="char-card">
                    <img src="{avatar}">
                    <div class="char-name">{p['nome']}</div>
                    <div class="char-desc">{p.get('arquetipo')}</div>
                </div>
                """, unsafe_allow_html=True)

                # Botoes de Ação
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    # Botão Ver Perfil
                    if st.button("👤 Perfil", key=f"btn_perfil_{i}"):
                        st.session_state['perfil_visualizar'] = nome_limpo
                        st.rerun()
                with c_btn2:
                    # Botão Conversar (CORRIGIDO)
                    if st.button("💬 Chat", key=f"btn_chat_{i}"):
                        st.session_state['char_atual'] = nome_limpo
                        st.rerun()

# --- ABA 2: CHAT (CONVERSAS) ---
with tab2:
    char_selecionado = st.session_state.get('char_atual')

    if not char_selecionado:
        st.info("👈 Escolha alguém na aba 'Explorar' para conversar.")
        # Lista rápida de recentes
        st.markdown("#### 🕒 Continuar Conversa:")
        arquivos = listar_personagens()
        for arquivo in arquivos:
            nome = arquivo.replace(".json", "")
            if st.button(f"➡️ {nome}", key=f"hist_{nome}"):
                st.session_state['char_atual'] = nome
                st.rerun()
    else:
        # --- INTERFACE DO CHAT ---
        p_atual = carregar_personagem(f"{char_selecionado}.json")
        msgs = carregar_mensagens_salvas(f"{char_selecionado}.json")

        # Header Compacto
        c_back, c_tit, c_act = st.columns([1, 4, 1])
        with c_back:
            if st.button("❌", help="Fechar conversa"):
                st.session_state['char_atual'] = None
                st.rerun()
        with c_tit:
            st.markdown(f"**{p_atual['nome']}**")
        with c_act:
            if st.button("🗑️", help="Limpar"):
                limpar_historico_visual(f"{char_selecionado}.json")
                st.rerun()

        st.markdown("---")

        # Área de Mensagens
        chat_container = st.container(height=400)
        with chat_container:
            for msg in msgs:
                css_class = "bubble-user" if msg["role"] == "user" else "bubble-ai"
                st.markdown(f'<div class="{css_class}">{msg["content"]}</div>', unsafe_allow_html=True)

        # Input
        if prompt := st.chat_input("Digite sua mensagem..."):
            # Salva User
            salvar_mensagem_no_historico(f"{char_selecionado}.json", "user", prompt)
            st.rerun()  # Atualiza para mostrar msg do user instantaneamente

        # Processamento da IA (Se a ultima msg for do user, a IA responde)
        if msgs and msgs[-1]["role"] == "user":
            with st.spinner("Digitando..."):
                resposta_full = responder_usuario(msgs[-1]["content"], p_atual, f"{char_selecionado}.json")

                # Limpeza simples de tags (opcional)
                fala_limpa = re.sub(r'\[.*?\]', '', resposta_full).strip()
                if not fala_limpa: fala_limpa = resposta_full

                salvar_mensagem_no_historico(f"{char_selecionado}.json", "assistant", fala_limpa)
                st.rerun()

# --- ABA 3: EU (CONFIGURAÇÕES E CRIAÇÃO) ---
with tab3:
    st.header("👤 Minha Conta")

    # 1. Configurações Gerais (O que tinha sumido)
    with st.expander("⚙️ Configurações do App", expanded=True):
        st.toggle("🔔 Notificações (Push)", value=True)
        st.toggle("🌙 Modo Escuro Forçado", value=True, disabled=True)
        st.selectbox("Idioma", ["Português (BR)", "English", "Español"])
        if st.button("⚠️ Apagar Todos os Dados"):
            st.toast("Função de segurança. Implementar depois.", icon="🔒")

    # 2. Criar Novo Personagem (Ferramenta de Admin/User)
    with st.expander("🛠️ Criar Nova Persona (IA)"):
        with st.form("new_char"):
            nome = st.text_input("Nome")
            arquetipo = st.text_input("Arquétipo (Ex: Vampira, CEO)")
            historia = st.text_area("História / Lore")

            c1, c2 = st.columns(2)
            tracos = c1.text_input("Personalidade (CSV)")
            estilo = c2.text_input("Estilo de Fala")

            if st.form_submit_button("Criar"):
                criar_personagem_avancado(nome, arquetipo, tracos, "Nenhum", "Interagir", estilo, "Médio", "Nenhum",
                                          historia)
                st.success("Criado!")
                time.sleep(1)
                st.rerun()

    # 3. Injetar Conhecimento (RAG)
    with st.expander("📚 Carregar Livros/Lore (PDF)"):
        pdf = st.file_uploader("Enviar PDF", type="pdf")
        if pdf:
            msg = processar_conhecimento_mundo(pdf)
            st.success(msg)

    st.markdown("---")
    st.caption("Roleplay Verse v1.0 - Alpha")