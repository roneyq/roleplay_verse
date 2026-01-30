import streamlit as st
import sys
import os

# --- Hack do BD (só roda se estiver na nuvem/linux) ---
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    # Se der erro (estamos no windows), apenas ignora e segue a vida
    pass


import re
import time
# Importando as novas funções de histórico
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

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Roleplay Verse", page_icon="💬", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0e1117; color: #e0e0e0; }

    /* Estilo de Menu */
    .stRadio > div { flex-direction: row; }

    /* Bolhas de Chat estilo WhatsApp */
    .stChatMessage { gap: 1rem; }
</style>
""", unsafe_allow_html=True)


# --- FUNÇÕES AUXILIARES ---
def separar_pensamento_fala(texto_bruto):
    pensamento = None
    fala = texto_bruto
    if "ESTRUTURA DE PERSONAGEM" in texto_bruto:
        texto_bruto = texto_bruto.split("ESTRUTURA DE PERSONAGEM")[0]
    padrao = r'\[PENSAMENTO\]:?\s*(.*?)\[FALA\]:?\s*(.*)'
    match = re.search(padrao, texto_bruto, re.DOTALL | re.IGNORECASE)
    if match:
        pensamento = match.group(1).strip()
        fala = match.group(2).strip()
    else:
        fala = re.sub(r'\[PENSAMENTO\]:?|\[FALA\]:?', '', texto_bruto, flags=re.IGNORECASE).strip()
    return pensamento, fala


def get_avatar(nome, arquetipo):
    nome_lower = nome.lower()
    arq_lower = arquetipo.lower()
    if "aria" in nome_lower or "ladra" in arq_lower: return "🥷"
    if "marcus" in nome_lower or "detetive" in arq_lower: return "🕵️‍♂️"
    if "mago" in arq_lower: return "🧙‍♂️"
    return "👤"


# --- MENU PRINCIPAL (SIDEBAR) ---
with st.sidebar:
    st.title("🎲 Universo RPG")

    # --- NOVO: UPLOAD DE MUNDO ---
    with st.expander("📚 Injetar Conhecimento (PDF)"):
        arquivo_pdf = st.file_uploader("Subir Lore/Regras", type="pdf")
        if arquivo_pdf is not None:
            with st.spinner("Lendo livro..."):
                # Precisamos importar a função nova do brain
                from brain import processar_conhecimento_mundo

                msg = processar_conhecimento_mundo(arquivo_pdf)
                st.success(msg)

    st.markdown("---")
    # ... o resto do código de seleção de personagem continua igual ...

# --- LÓGICA: CRIAR PERSONAGEM ---
if menu_escolha == "➕ Criar Personagem":
    st.header("🛠️ Criar Novo Personagem")
    with st.form("criacao"):
        nome = st.text_input("Nome")
        arquetipo = st.text_input("Arquétipo")
        historia = st.text_area("História / Lore")
        col1, col2 = st.columns(2)
        with col1:
            tracos = st.text_area("Personalidade (CSV)")
            valores = st.text_area("Valores (CSV)")
        with col2:
            estilo = st.text_area("Estilo de Fala (CSV)")
            objetivo = st.text_input("Objetivo Atual")
        maleabilidade = st.select_slider("Nível de Maleabilidade", options=["Teimoso", "Racional", "Influenciável"])
        segredo = st.text_input("Segredo Obscuro")

        if st.form_submit_button("Salvar Personagem"):
            if nome and arquetipo:
                criar_personagem_avancado(nome, arquetipo, tracos, valores, objetivo, estilo, maleabilidade, segredo,
                                          historia)
                st.success(f"{nome} criado com sucesso!")
                time.sleep(1)
                st.rerun()

# --- LÓGICA: CONFIGURAÇÕES (Placeholder) ---
elif menu_escolha == "⚙️ Configurações":
    st.header("Configurações do Sistema")
    st.info("Funcionalidades futuras: Exportar chat, Mudar tema, Ajustar Token da API.")

# --- LÓGICA: CONVERSAS (WHATSAPP STYLE) ---
elif menu_escolha == "💬 Minhas Conversas":
    # 1. Lista de Contatos
    arquivos = listar_personagens()
    opcoes_limpas = {f.replace(".json", ""): f for f in arquivos}

    if not arquivos:
        st.warning("Você não tem personagens. Vá em 'Criar Personagem' primeiro.")
    else:
        # Seletor de Contato na Sidebar (para não poluir o chat)
        with st.sidebar:
            st.subheader("Contatos")
            contato_selecionado = st.selectbox(
                "Selecionar Chat:",
                list(opcoes_limpas.keys())
            )

            # Botão de Reset
            arquivo_atual = opcoes_limpas[contato_selecionado]
            if st.button("🗑️ Limpar Conversa", type="primary"):
                limpar_historico_visual(arquivo_atual)
                st.rerun()

        # 2. Carregar Dados do Personagem e Histórico
        arquivo_atual = opcoes_limpas[contato_selecionado]
        personagem_atual = carregar_personagem(arquivo_atual)
        mensagens_salvas = carregar_mensagens_salvas(arquivo_atual)

        # 3. Cabeçalho do Chat
        avatar_img = get_avatar(personagem_atual['nome'], personagem_atual['arquetipo'])
        st.markdown(f"""
        <div style='display: flex; align-items: center; gap: 10px; padding: 10px; background-color: #161b22; border-radius: 10px; margin-bottom: 20px;'>
            <h1 style='margin: 0;'>{avatar_img}</h1>
            <div>
                <h3 style='margin: 0; color: #fff;'>{personagem_atual['nome']}</h3>
                <small style='color: #8b949e;'>{personagem_atual['arquetipo']}</small>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 4. Renderizar Mensagens Antigas (Persistência)
        # Inicializa session state COM o histórico do disco
        if "chat_history" not in st.session_state or st.session_state.get("current_char") != contato_selecionado:
            st.session_state.chat_history = mensagens_salvas
            st.session_state.current_char = contato_selecionado

        for msg in st.session_state.chat_history:
            icon = avatar_img if msg["role"] == "assistant" else "🧑‍💻"
            with st.chat_message(msg["role"], avatar=icon):
                st.markdown(msg["content"])

        # 5. Input e Processamento
        if prompt := st.chat_input(f"Mensagem para {personagem_atual['nome']}..."):
            # Exibe e Salva User
            st.chat_message("user", avatar="🧑‍💻").markdown(prompt)
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            salvar_mensagem_no_historico(arquivo_atual, "user", prompt)

            # Resposta IA
            with st.chat_message("assistant", avatar=avatar_img):
                with st.spinner("Digitando..."):
                    try:
                        resposta_bruta = responder_usuario(prompt, personagem_atual, arquivo_atual)
                        pensamento, fala_limpa = separar_pensamento_fala(resposta_bruta)

                        # Mostra pensamento se houver
                        if pensamento:
                            with st.expander("💭 Pensamento"):
                                st.markdown(f"*{pensamento}*")

                        st.markdown(fala_limpa)

                        # Salva IA
                        st.session_state.chat_history.append({"role": "assistant", "content": fala_limpa})
                        salvar_mensagem_no_historico(arquivo_atual, "assistant", fala_limpa)

                    except Exception as e:
                        st.error(f"Erro: {e}")