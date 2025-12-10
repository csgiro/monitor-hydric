# -*- coding: utf-8 -*-
"""
Dashboard de Monitoramento Hídrico
Integração com ThingSpeak API
"""

# =============================================================================
# IMPORTAÇÕES
# =============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import requests
import json

# =============================================================================
# CONFIGURAÇÕES E CONSTANTES
# =============================================================================

# Configuração da página Streamlit
st.set_page_config(
    page_title="Dashboard de Monitoramento Hídrico",
    page_icon="💧",
    layout="wide"
)

# Constantes para simulação
NIVEL_MAXIMO = 100
TEMP_ALERTA = 30
VAZAO_NORMAL = 5.0

# Constantes para parâmetros de qualidade da água
TEMP_MIN = 20
TEMP_MAX = 35
TURBIDEZ_MIN = 0
TURBIDEZ_MAX = 10
PH_MIN = 6.5
PH_MAX = 8.5
SOLIDOS_MIN = 0
SOLIDOS_MAX = 1000

# Configurações do ThingSpeak
THINGSPEAK_CHANNEL_ID = "3112165"
THINGSPEAK_API_KEY = "6FN9AVESVHIO6ACV"
THINGSPEAK_BASE_URL = "https://api.thingspeak.com/channels"

# =============================================================================
# FUNÇÕES DE INTEGRAÇÃO COM THINGSPEAK API
# =============================================================================

def buscar_dados_thingspeak():
    """
    Busca dados reais do ThingSpeak.
    Retorna: (DataFrame, sucesso)
    """
    print("🔄 Iniciando requisição para ThingSpeak...")
    
    try:
        # URL para buscar os últimos dados do canal
        url = f"{THINGSPEAK_BASE_URL}/{THINGSPEAK_CHANNEL_ID}/feeds.json"
        params = {
            'api_key': THINGSPEAK_API_KEY,
            'results': 100  # Últimos 100 registros
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        response.raise_for_status()
        
        data = response.json()
        
        if 'feeds' in data and len(data['feeds']) > 0:
            print(f"✅ {len(data['feeds'])} registros encontrados")
            
            # Converter para DataFrame
            df = pd.DataFrame(data['feeds'])
            print(f"📊 Colunas do DataFrame: {list(df.columns)}")
            
            # Converter timestamps para datetime
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at'])
                print("⏰ Timestamps convertidos para datetime")
            
            return df, True
        else:
            print("⚠️ Nenhum feed encontrado nos dados")
            return None, False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de requisição: {e}")
        return None, False
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return None, False

def buscar_dados_thingspeak_ultimo():
    """
    Busca apenas o último dado do ThingSpeak.
    Retorna: (dict, sucesso)
    """
    print("🔄 Buscando último dado do ThingSpeak...")
    
    try:
        url = f"{THINGSPEAK_BASE_URL}/{THINGSPEAK_CHANNEL_ID}/feeds/last.json"
        params = {'api_key': THINGSPEAK_API_KEY}
        
        print(f"📡 URL: {url}")
        
        response = requests.get(url, params=params, timeout=10)
        print(f"📊 Status: {response.status_code}")
        
        response.raise_for_status()
        
        data = response.json()
        print(f"📋 Último dado: {json.dumps(data, indent=2)}")
        
        return data, True
        
    except Exception as e:
        print(f"❌ Erro ao buscar último dado: {e}")
        return None, False

def processar_dados_thingspeak(df_thingspeak):
    """
    Processa os dados do ThingSpeak e extrai as informações necessárias.
    Retorna: dict com dados processados
    """
    print("🔧 Processando dados do ThingSpeak...")
    
    if df_thingspeak is None or len(df_thingspeak) == 0:
        print("⚠️ Nenhum dado para processar")
        return None
    
    # Mostrar campos disponíveis
    campos_disponiveis = [col for col in df_thingspeak.columns if col.startswith('field')]
    print(f"📊 Campos disponíveis: {campos_disponiveis}")
    
    # Pegar o último registro
    ultimo_registro = df_thingspeak.iloc[-1]
    print(f"📋 Último registro: {ultimo_registro.to_dict()}")
    
    # Mapear campos de forma segura
    dados_processados = {
        'nivel': float(ultimo_registro.get('field1', 50)) if 'field1' in df_thingspeak.columns else 50,
        'temperatura': float(ultimo_registro.get('field2', 25)) if 'field2' in df_thingspeak.columns else 25,
        'vazao': float(ultimo_registro.get('field3', 5)) if 'field3' in df_thingspeak.columns else 5,
        'temp_agua': float(ultimo_registro.get('field4', 25)) if 'field4' in df_thingspeak.columns else 25,
        'turbidez': float(ultimo_registro.get('field5', 2)) if 'field5' in df_thingspeak.columns else 2,
        'ph': float(ultimo_registro.get('field6', 7.0)) if 'field6' in df_thingspeak.columns else 7.0,
        'solidos': float(ultimo_registro.get('field7', 200)) if 'field7' in df_thingspeak.columns else 200,
    }
    
    print(f"📊 Dados processados: {dados_processados}")
    
    return dados_processados

# =============================================================================
# FUNÇÕES DE DADOS SIMULADOS (FALLBACK)
# =============================================================================

@st.cache_data(ttl=2) 
def ler_dados_simulados():
    """
    Simula a leitura de dados de diferentes sensores (nível, temperatura, vazão).
    """
    # Simulação de dados
    # Gera variação maior para demonstrar o real-time na dashboard
    nivel_atual = np.random.randint(30, 95) 
    temperatura = np.random.uniform(22.0, 31.0) 
    vazao = np.random.uniform(2.5, 8.0) 
    
    # Simulação de histórico (últimas 2 horas)
    num_pontos = 60 # 1 ponto a cada 2 minutos
    indices = pd.date_range(end=datetime.now(), periods=num_pontos, freq='2min')
    
    # Tendência de Nível: ligeira queda com ruído
    nivel_hist = np.linspace(80, nivel_atual, num_pontos) + np.random.normal(0, 5, num_pontos)
    nivel_hist = np.clip(nivel_hist, 0, NIVEL_MAXIMO) # Garante que fique entre 0 e 100
    
    # Tendência de Vazão: ligeiro aumento com ruído
    vazao_hist = np.linspace(4.0, vazao, num_pontos) + np.random.normal(0, 0.5, num_pontos)
    vazao_hist = np.clip(vazao_hist, 0, 10) # Garante valores razoáveis
    
    historico_df = pd.DataFrame({
        'Nível (%)': nivel_hist,
        'Vazão (L/min)': vazao_hist
    }, index=indices)

    return nivel_atual, temperatura, vazao, historico_df

@st.cache_data(ttl=2)
def ler_dados_qualidade_agua():
    """
    Simula dados de qualidade da água: temperatura, turbidez, pH e sólidos dissolvidos.
    """
    # Dados atuais
    temp_atual = np.random.uniform(TEMP_MIN, TEMP_MAX)
    turbidez_atual = np.random.uniform(TURBIDEZ_MIN, TURBIDEZ_MAX)
    ph_atual = np.random.uniform(PH_MIN, PH_MAX)
    solidos_atual = np.random.uniform(SOLIDOS_MIN, SOLIDOS_MAX)
    
    # Histórico (últimas 2 horas)
    num_pontos = 60
    indices = pd.date_range(end=datetime.now(), periods=num_pontos, freq='2min')
    
    # Simulação de tendências com ruído
    temp_hist = np.linspace(25, temp_atual, num_pontos) + np.random.normal(0, 1, num_pontos)
    turbidez_hist = np.linspace(2, turbidez_atual, num_pontos) + np.random.normal(0, 0.5, num_pontos)
    ph_hist = np.linspace(7.2, ph_atual, num_pontos) + np.random.normal(0, 0.1, num_pontos)
    solidos_hist = np.linspace(200, solidos_atual, num_pontos) + np.random.normal(0, 50, num_pontos)
    
    # Garantir limites realistas
    temp_hist = np.clip(temp_hist, TEMP_MIN, TEMP_MAX)
    turbidez_hist = np.clip(turbidez_hist, TURBIDEZ_MIN, TURBIDEZ_MAX)
    ph_hist = np.clip(ph_hist, PH_MIN, PH_MAX)
    solidos_hist = np.clip(solidos_hist, SOLIDOS_MIN, SOLIDOS_MAX)
    
    historico_qualidade = pd.DataFrame({
        'Temperatura (°C)': temp_hist,
        'Turbidez (NTU)': turbidez_hist,
        'pH': ph_hist,
        'Sólidos Dissolvidos (mg/L)': solidos_hist
    }, index=indices)
    
    return temp_atual, turbidez_atual, ph_atual, solidos_atual, historico_qualidade

def calcular_qualidade_agua(temp, turbidez, ph, solidos):
    """
    Calcula um índice de qualidade da água baseado nos 4 parâmetros.
    """
    # Normalização dos parâmetros (0-100)
    temp_score = max(0, 100 - abs(temp - 25) * 4)  # Ideal: 25°C
    turbidez_score = max(0, 100 - turbidez * 10)   # Ideal: 0 NTU
    ph_score = max(0, 100 - abs(ph - 7.0) * 20)    # Ideal: 7.0
    solidos_score = max(0, 100 - solidos / 10)     # Ideal: 0 mg/L
    
    # Média ponderada (todos com peso igual)
    qualidade = (temp_score + turbidez_score + ph_score + solidos_score) / 4
    
    return qualidade

# =============================================================================
# INTERFACE STREAMLIT
# =============================================================================

# Sidebar
with st.sidebar:
    st.title("💧 Menu")
    st.markdown("---")
    
    # Opções do menu
    opcao = st.selectbox(
        "Selecione uma opção:",
        ["🏠 Home", "🚪 Logout"]
    )
    
    st.markdown("---")
    st.caption("Dashboard de Monitoramento Hídrico")
    st.caption("Dados atualizados a cada 2 segundos")

# Conteúdo principal baseado na opção selecionada
if opcao == "🏠 Home":
    st.title("💧 Painel de Monitoramento Hídrico")
    st.caption("Dashboard de visualização de dados em tempo real (Mock Data).")

    # Adiciona um placeholder para o botão de atualização e o indicador de última atualização
    col_info, col_refresh = st.columns([4, 1])

    # O Streamlit rerun automático é crucial para simular o tempo real
    # Se estiver rodando o script localmente, ele vai recarregar a cada 2 segundos devido ao st.cache_data(ttl=2)
    # Para forçar uma atualização manual, o botão continua funcionando.
    if col_refresh.button("Atualizar Dados (Manual)", key="refresh_button"):
        st.cache_data.clear()
        # O comando abaixo reinicia o script para buscar novos dados do cache (ou função)
        st.rerun()

    # 1. Carregar os dados (ThingSpeak ou simulados)
    try:
        print("🚀 Iniciando carregamento de dados...")
        
        # Tentar buscar dados do ThingSpeak primeiro
        df_thingspeak, sucesso_thingspeak = buscar_dados_thingspeak()
        
        if sucesso_thingspeak and df_thingspeak is not None:
            st.success("✅ Conectado ao ThingSpeak - Dados reais")
            
            # Processar dados do ThingSpeak
            dados_processados = processar_dados_thingspeak(df_thingspeak)
            
            if dados_processados:
                # Usar dados reais do ThingSpeak
                nivel = dados_processados['nivel']
                temperatura = dados_processados['temperatura']
                vazao = dados_processados['vazao']
                temp_atual = dados_processados['temp_agua']
                turbidez_atual = dados_processados['turbidez']
                ph_atual = dados_processados['ph']
                solidos_atual = dados_processados['solidos']
                
                # Criar DataFrames para histórico
                campos_historico = []
                nomes_historico = []
                
                if 'field1' in df_thingspeak.columns:
                    campos_historico.append('field1')
                    nomes_historico.append('Nível (%)')
                if 'field2' in df_thingspeak.columns:
                    campos_historico.append('field2')
                    nomes_historico.append('Temperatura (°C)')
                if 'field3' in df_thingspeak.columns:
                    campos_historico.append('field3')
                    nomes_historico.append('Vazão (L/min)')
                
                if campos_historico:
                    df_historico = df_thingspeak[campos_historico].copy()
                    df_historico.columns = nomes_historico
                else:
                    # Fallback para dados simulados se não houver campos
                    nivel, temperatura, vazao, df_historico = ler_dados_simulados()
                
                # Criar dados de qualidade
                campos_qualidade = []
                nomes_qualidade = []
                
                if 'field4' in df_thingspeak.columns:
                    campos_qualidade.append('field4')
                    nomes_qualidade.append('Temperatura (°C)')
                if 'field5' in df_thingspeak.columns:
                    campos_qualidade.append('field5')
                    nomes_qualidade.append('Turbidez (NTU)')
                if 'field6' in df_thingspeak.columns:
                    campos_qualidade.append('field6')
                    nomes_qualidade.append('pH')
                if 'field7' in df_thingspeak.columns:
                    campos_qualidade.append('field7')
                    nomes_qualidade.append('Sólidos Dissolvidos (mg/L)')
                
                if campos_qualidade:
                    df_qualidade = df_thingspeak[campos_qualidade].copy()
                    df_qualidade.columns = nomes_qualidade
                else:
                    # Se não houver campos de qualidade, usar dados simulados
                    temp_atual, turbidez_atual, ph_atual, solidos_atual, df_qualidade = ler_dados_qualidade_agua()
            else:
                st.warning("⚠️ Erro ao processar dados do ThingSpeak, usando dados simulados")
                nivel, temperatura, vazao, df_historico = ler_dados_simulados()
                temp_atual, turbidez_atual, ph_atual, solidos_atual, df_qualidade = ler_dados_qualidade_agua()
        else:
            st.warning("⚠️ Não foi possível conectar ao ThingSpeak, usando dados simulados")
            print("🔄 Usando dados simulados como fallback...")
            nivel, temperatura, vazao, df_historico = ler_dados_simulados()
            temp_atual, turbidez_atual, ph_atual, solidos_atual, df_qualidade = ler_dados_qualidade_agua()
            
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        print(f"❌ Erro crítico: {e}")
        st.stop()

    # Espaço reservado para o tempo da última atualização
    ultima_atualizacao = datetime.now().strftime("%H:%M:%S")
    # Se a simulação mudar a cada 2 segundos, esta mensagem é importante:
    col_info.info(f"Última atualização: **{ultima_atualizacao}** (Os dados mudam a cada 2 segundos)", icon="🕒")


    # 2. SEÇÃO DE MÉTRICAS ATUAIS (CARDS)
    st.markdown("## Dados Atuais")

    col1, col2, col3, col4 = st.columns(4)

    # Métrica 1: Nível do Reservatório
    nivel_cor = 'normal' 
    if nivel < 20:
        nivel_cor = 'inverse' # Alerta crítico (vermelho)
    elif nivel < 50:
        nivel_cor = 'warning' # Aviso (amarelo)

    # O Streamlit exibe cores automaticamente baseado na delta_color: 'normal' (azul), 'warning' (amarelo), 'inverse' (vermelho)
    col1.metric(
        label="Nível do Reservatório",
        value=f"{nivel:.1f} %",
        delta_color=nivel_cor, 
        delta="Nível do Momento" # Adicionando um delta genérico para forçar a cor
    )

    # Métrica 2: Temperatura da Água
    temp_status = "Alerta" if temperatura >= TEMP_ALERTA else "Normal"
    temp_cor = 'inverse' if temperatura >= TEMP_ALERTA else 'normal'

    col2.metric(
        label="Temperatura da Água",
        value=f"{temperatura:.1f} °C",
        delta=temp_status,
        delta_color=temp_cor
    )

    # Métrica 3: Vazão Atual
    delta_vazao = vazao - VAZAO_NORMAL
    delta_vazao_cor = 'normal' if abs(delta_vazao) < 1.0 else 'inverse'

    col3.metric(
        label="Vazão Atual",
        value=f"{vazao:.2f} L/min",
        delta=f"{delta_vazao:+.2f} L/min vs Normal",
        delta_color=delta_vazao_cor
    )

    # Métrica 4: Status Operacional (Semáforo)
    if nivel < 20 or temperatura >= TEMP_ALERTA:
        status_emoji = "🔴"
        status_texto = "ALERTA CRÍTICO"
        status_cor = "red"
    elif nivel < 50:
        status_emoji = "🟠"
        status_texto = "ATENÇÃO"
        status_cor = "orange"
    else:
        status_emoji = "🟢"
        status_texto = "OPERACIONAL"
        status_cor = "green"

    with col4:
        st.markdown(
            f"""
            <div style="padding: 10px; border-radius: 8px; border: 1px solid lightgray; text-align: center; background-color: {status_cor}; color: white; margin-top: 15px;">
                <p style="font-size: 16px; margin: 0; font-weight: bold;">Status do Sistema</p>
                <p style="font-size: 24px; margin: 0; font-weight: bold;">{status_emoji} {status_texto}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # 3. SEÇÃO DE GRÁFICOS DE QUALIDADE DA ÁGUA
    st.markdown("## Parâmetros de Qualidade da Água")

    # Gráfico 1: Temperatura
    fig_temp = px.line(df_qualidade, y='Temperatura (°C)', title='Temperatura da Água')
    fig_temp.update_layout(height=300)
    st.plotly_chart(fig_temp, use_container_width=True)

    # Gráfico 2: Turbidez
    fig_turbidez = px.line(df_qualidade, y='Turbidez (NTU)', title='Turbidez da Água')
    fig_turbidez.update_layout(height=300)
    st.plotly_chart(fig_turbidez, use_container_width=True)

    # Gráfico 3: pH
    fig_ph = px.line(df_qualidade, y='pH', title='pH da Água')
    fig_ph.update_layout(height=300)
    st.plotly_chart(fig_ph, use_container_width=True)

    # Gráfico 4: Sólidos Dissolvidos
    fig_solidos = px.line(df_qualidade, y='Sólidos Dissolvidos (mg/L)', title='Sólidos Dissolvidos')
    fig_solidos.update_layout(height=300)
    st.plotly_chart(fig_solidos, use_container_width=True)

    # Gráfico 5: Qualidade Geral da Água
    qualidade_atual = calcular_qualidade_agua(temp_atual, turbidez_atual, ph_atual, solidos_atual)
    
    # Calcular histórico de qualidade
    qualidade_hist = []
    for i in range(len(df_qualidade)):
        temp = df_qualidade['Temperatura (°C)'].iloc[i]
        turb = df_qualidade['Turbidez (NTU)'].iloc[i]
        ph = df_qualidade['pH'].iloc[i]
        sol = df_qualidade['Sólidos Dissolvidos (mg/L)'].iloc[i]
        qualidade_hist.append(calcular_qualidade_agua(temp, turb, ph, sol))
    
    df_qualidade['Qualidade Geral (%)'] = qualidade_hist
    
    fig_qualidade = px.line(df_qualidade, y='Qualidade Geral (%)', title='Qualidade Geral da Água')
    fig_qualidade.add_hline(y=80, line_dash="dash", line_color="green", annotation_text="Boa Qualidade (80%)")
    fig_qualidade.add_hline(y=60, line_dash="dash", line_color="orange", annotation_text="Qualidade Regular (60%)")
    fig_qualidade.add_hline(y=40, line_dash="dash", line_color="red", annotation_text="Qualidade Ruim (40%)")
    fig_qualidade.update_layout(height=300)
    st.plotly_chart(fig_qualidade, use_container_width=True)

    # Métricas de qualidade atual
    st.markdown("### Indicadores de Qualidade Atual")
    col_q1, col_q2, col_q3, col_q4, col_q5 = st.columns(5)
    
    with col_q1:
        st.metric("Temperatura", f"{temp_atual:.1f}°C")
    with col_q2:
        st.metric("Turbidez", f"{turbidez_atual:.1f} NTU")
    with col_q3:
        st.metric("pH", f"{ph_atual:.2f}")
    with col_q4:
        st.metric("Sólidos", f"{solidos_atual:.0f} mg/L")
    with col_q5:
        st.metric("Qualidade Geral", f"{qualidade_atual:.1f}%")

elif opcao == "🚪 Logout":
    st.title("🚪 Logout")
    st.info("Você foi desconectado do sistema.")
    st.button("Confirmar Logout", key="logout_confirm")

# O Streamlit se atualiza automaticamente a cada 2 segundos devido ao st.cache_data(ttl=2)
# Não é necessário um loop infinito - o Streamlit gerencia isso automaticamente