import streamlit as st
import pandas as pd
from datetime import datetime
import time
import gspread
from google.oauth2.service_account import Credentials
import folium
from streamlit_folium import st_folium

# =============================================================================
# --- 1. CONFIGURAÇÕES GERAIS ---
# =============================================================================
st.set_page_config(page_title="No Precinho - Ofertas", page_icon="📍", layout="wide")

st.markdown("""
<style>
    footer { display: none !important; visibility: hidden !important; }
    .painel-login { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-top: 4px solid #ff4b4b; }
    .caixa-destaque { background-color: #e6f7ff; padding: 15px; border-radius: 8px; border-left: 5px solid #0066cc; margin-bottom: 20px;}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# --- 2. CONEXÃO COM BANCO DE DADOS (GOOGLE SHEETS) ---
# =============================================================================
@st.cache_resource(ttl=3600, show_spinner=False)
def get_gspread_client():
    if "gcp_service_account" in st.secrets:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    return None

@st.cache_data(ttl=60, show_spinner=False)
def carregar_tabela(nome_aba):
    try:
        gc = get_gspread_client()
        if gc:
            ws = gc.open("Base_NoPrecinho").worksheet(nome_aba)
            dados = ws.get_all_values()
            if len(dados) <= 1:
                return pd.DataFrame(columns=dados[0] if dados else [])
            df = pd.DataFrame(dados[1:], columns=dados[0])
            df.columns = df.columns.astype(str).str.strip().str.lower()
            return df
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

# NOVO: Função para salvar a oferta na aba "Ofertas"
def salvar_nova_oferta(usuario_loja, produto, preco_de, preco_por, link_imagem):
    try:
        gc = get_gspread_client()
        if gc:
            ws = gc.open("Base_NoPrecinho").worksheet("Ofertas")
            id_oferta = f"OFT-{int(time.time())}" # Gera um código único baseado na hora
            data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Ordem das colunas: id_oferta, usuario_loja, produto, preco_de, preco_por, link_imagem, data_hora, status_pagamento
            nova_linha = [id_oferta, usuario_loja, produto, preco_de, preco_por, link_imagem, data_hora, "pendente"]
            ws.append_row(nova_linha)
            st.cache_data.clear()
            return True
    except Exception as e:
        st.error(f"Erro ao comunicar com o servidor: {e}")
        return False

# =============================================================================
# --- 3. SISTEMA DE LOGIN ---
# =============================================================================
if "usuario_logado" not in st.session_state: st.session_state.usuario_logado = None
if "perfil_logado" not in st.session_state: st.session_state.perfil_logado = None

def fazer_login(usuario, senha):
    df_users = carregar_tabela("Usuarios")
    if not df_users.empty and 'usuario' in df_users.columns:
        user_row = df_users[(df_users['usuario'] == usuario) & (df_users['senha'] == senha)]
        if not user_row.empty:
            status_user = str(user_row.iloc[0].get('status', '')).strip().lower()
            if status_user == 'aprovado':
                st.session_state.usuario_logado = user_row.iloc[0]['usuario'] # Usamos o login como identificador
                st.session_state.nome_logado = user_row.iloc[0]['nome']
                st.session_state.perfil_logado = str(user_row.iloc[0]['perfil']).strip().lower()
                st.success("✅ Acesso Concedido!")
                st.rerun()
            else:
                st.warning("⏳ O seu cadastro está em análise pela nossa equipa. Aguarde a aprovação.")
        else:
            st.error("❌ Usuário ou senha incorretos.")
    else:
        st.warning("⚠️ Banco de dados vazio ou sem conexão.")

def fazer_logout():
    st.session_state.usuario_logado = None
    st.session_state.perfil_logado = None
    st.session_state.nome_logado = None
    st.rerun()

# =============================================================================
# --- 4. BARRA LATERAL (MENU E LOGIN) ---
# =============================================================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #ff4b4b;'>📍 NO PRECINHO</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    if st.session_state.usuario_logado is None:
        st.markdown("<div class='painel-login'>", unsafe_allow_html=True)
        st.markdown("### 🔐 Área do Comerciante")
        user_input = st.text_input("Usuário")
        pass_input = st.text_input("Senha", type="password")
        if st.button("Entrar", type="primary", use_container_width=True):
            fazer_login(user_input, pass_input)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br><p style='font-size:0.8em; text-align:center;'>Quer anunciar? Fale conosco!</p>", unsafe_allow_html=True)
    else:
        st.success(f"👋 Olá, {st.session_state.nome_logado}!")
        
        if st.session_state.perfil_logado == "admin":
            st.button("👑 Painel Admin", use_container_width=True)
        elif st.session_state.perfil_logado == "comerciante":
            st.button("🏪 Lançar Oferta", use_container_width=True)
            
        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True):
            fazer_logout()

# =============================================================================
# --- 5. TELA PRINCIPAL (FRONT-END) ---
# =============================================================================
if st.session_state.usuario_logado is None:
    st.title("Descubra as melhores ofertas perto de você! 🛒")
    pesquisa = st.text_input("🔍 O que você procura hoje?", placeholder="Ex: Leite, Carne, Pão...")
    
    # Mapa Fixo Temporário (Até configurarmos o GPS no próximo passo)
    m = folium.Map(location=[-8.1189, -35.2925], zoom_start=14)
    folium.Marker([-8.1189, -35.2925], popup="Leite Ninho - R$ 15,00", tooltip="Mercadinho do João").add_to(m)
    st_folium(m, width=1200, height=500, returned_objects=[])

elif st.session_state.perfil_logado == "admin":
    st.header("👑 Centro de Comando - Administração")
    st.info("O painel da diretoria será construído na próxima fase para aprovar as ofertas recebidas!")

elif st.session_state.perfil_logado == "comerciante":
    st.header("🏪 Central de Lançamento de Ofertas")
    st.markdown("Preencha os dados abaixo para enviar o seu produto para o mapa da cidade. **O anúncio dura 24 horas!**")
    
    st.markdown("<div class='caixa-destaque'>💡 <b>Dica de Imagem:</b> Hospede a foto do seu produto no site <a href='https://pt-br.imgbb.com/' target='_blank'>ImgBB</a> e cole o <b>Link Direto</b> no formulário abaixo.</div>", unsafe_allow_html=True)
    
    with st.form("form_nova_oferta", clear_on_submit=True):
        st.subheader("📦 Dados do Produto")
        
        produto_nome = st.text_input("Nome do Produto + Quantidade (Ex: Leite Ninho 400g)", max_chars=50)
        
        c1, c2 = st.columns(2)
        with c1:
            preco_antigo = st.text_input("De: R$ (Preço Normal)")
        with c2:
            preco_novo = st.text_input("Por: R$ (Preço da Oferta)")
            
        link_img = st.text_input("🔗 Link Direto da Imagem (Opcional, mas recomendado)")
        
        st.markdown("---")
        st.markdown("### 💳 Pagamento da Taxa de Divulgação")
        st.write("Cada anúncio de 24h tem um custo fixo de **R$ 2,00**. Realize o PIX e envie a oferta para a central de aprovação.")
        st.info("🔑 Chave PIX: **04994867460** (Eliude Bernardo de Souza Silva)")
        
        enviar_btn = st.form_submit_button("🚀 Enviar Oferta para Aprovação", type="primary", use_container_width=True)
        
        if enviar_btn:
            if not produto_nome or not preco_novo:
                st.error("⚠️ O nome do produto e o preço da oferta são obrigatórios!")
            else:
                with st.spinner("A transmitir oferta para a central..."):
                    if salvar_nova_oferta(st.session_state.usuario_logado, produto_nome, preco_antigo, preco_novo, link_img):
                        st.success("✅ Oferta enviada com sucesso! Assim que o administrador confirmar o seu PIX de R$ 2,00, ela aparecerá no mapa para toda a cidade.")
