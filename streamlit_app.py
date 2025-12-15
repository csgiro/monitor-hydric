# -*- coding: utf-8 -*-
"""
Dashboard de Monitoramento Hídrico
Interface Streamlit para visualização de dados de qualidade da água
"""

# =============================================================================
# IMPORTAÇÕES
# =============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import pytz
import plotly.express as px
import plotly.graph_objects as go

# Importar funções da API
from thingspeak_api import (
    buscar_dados_thingspeak,
    processar_dados_thingspeak,
    criar_historico_qualidade,
    calcular_qualidade_agua
)

# Importar handler de notificações
from notifications_handler import NotificationsHandler

# =============================================================================
# CONFIGURAÇÕES E CONSTANTES
# =============================================================================

# Configuração da página Streamlit
st.set_page_config(
    page_title="Dashboard de Monitoramento Hídrico",
    page_icon="💧",
    layout="wide"
)

# Constantes para parâmetros de qualidade da água
TEMP_MIN = 15
TEMP_MAX = 35
TURBIDEZ_MIN = 0
TURBIDEZ_MAX = 10
PH_MIN = 6.0
PH_MAX = 9.0
SOLIDOS_MIN = 0
SOLIDOS_MAX = 2000

# =============================================================================
# FUNÇÕES DE DADOS SIMULADOS (FALLBACK)
# =============================================================================

@st.cache_data(ttl=2) 
def ler_dados_simulados():
    """
    Simula a leitura de dados de diferentes sensores (nível, temperatura, vazão).
    """
    # Simulação de dados
    nivel_atual = np.random.randint(30, 95) 
    temperatura = np.random.uniform(22.0, 31.0) 
    vazao = np.random.uniform(2.5, 8.0) 
    
    # Simulação de histórico (últimas 2 horas)
    num_pontos = 60 # 1 ponto a cada 2 minutos
    indices = pd.date_range(end=datetime.now(), periods=num_pontos, freq='2min')
    
    # Tendência de Nível: ligeira queda com ruído
    nivel_hist = np.linspace(80, nivel_atual, num_pontos) + np.random.normal(0, 5, num_pontos)
    nivel_hist = np.clip(nivel_hist, 0, 100)
    
    # Tendência de Vazão: ligeiro aumento com ruído
    vazao_hist = np.linspace(4.0, vazao, num_pontos) + np.random.normal(0, 0.5, num_pontos)
    vazao_hist = np.clip(vazao_hist, 0, 10)
    
    historico_df = pd.DataFrame({
        'Nível (%)': nivel_hist,
        'Vazão (L/min)': vazao_hist
    }, index=indices)

    return nivel_atual, temperatura, vazao, historico_df

@st.cache_data(ttl=2)
def ler_dados_qualidade_agua():
    """
    Gera dados mockados de qualidade da água dos últimos 15 dias com variações nas faixas (ideal, alerta, crítico).
    Ranges baseados em:
    - Turbidez: Ideal < 1.0, Alerta 1.0-5.0, Crítico > 5.0
    - TDS: Ideal < 500, Alerta 500-1000, Crítico > 1000
    - pH: Ideal 6.5-8.5, Alerta 6.0-6.5 ou 8.5-9.5, Crítico < 6.0 ou > 9.5
    - Temp: Ideal 20-28°C, Alerta variação > 3°C, Crítico variação > 5°C
    """
    # Criar índices para os últimos 15 dias (1 ponto a cada hora)
    agora = datetime.now()
    fim_mock = agora
    inicio_mock = fim_mock - timedelta(days=15)
    indices = pd.date_range(start=inicio_mock, end=fim_mock, freq='1h')
    num_pontos = len(indices)
    
    # Criar arrays para cada parâmetro com variações nas faixas
    turbidez_hist = []
    ph_hist = []
    temp_hist = []
    solidos_hist = []
    
    # Gerar dados com variações aleatórias entre as faixas
    for i in range(num_pontos):
        # TURBIDEZ: alternar entre ideal, alerta e crítico
        rand = np.random.random()
        if rand < 0.6:  # 60% ideal
            turbidez = np.random.uniform(0.1, 0.9)
        elif rand < 0.9:  # 30% alerta
            turbidez = np.random.uniform(1.0, 5.0)
        else:  # 10% crítico
            turbidez = np.random.uniform(5.0, 7.0)
        turbidez_hist.append(turbidez)  
        # pH: alternar entre ideal, alerta e crítico
        rand = np.random.random()
        if rand < 0.7:  # 70% ideal
            ph = np.random.uniform(6.5, 8.5)
        elif rand < 0.95:  # 25% alerta
            if np.random.random() < 0.5:
                ph = np.random.uniform(6.0, 6.5)  # Alerta baixo
            else:
                ph = np.random.uniform(8.0, 9)  # Alerta alto
        else:  # 5% crítico
            if np.random.random() < 0.5:
                ph = np.random.uniform(5.0, 6.0)  # Crítico baixo
            else:
                ph = np.random.uniform(8.5, 9)  # Crítico alto
        ph_hist.append(ph)
        
        # TEMPERATURA: alternar entre ideal, alerta e crítico
        rand = np.random.random()
        if rand < 0.65:  # 65% ideal
            temp = np.random.uniform(20, 28)
        elif rand < 0.9:  # 25% alerta (variação > 3°C)
            if np.random.random() < 0.5:
                temp = np.random.uniform(17, 20)  # Alerta baixo
            else:
                temp = np.random.uniform(24, 27)  # Alerta alto
        else:  # 10% crítico (variação > 5°C)
            if np.random.random() < 0.5:
                temp = np.random.uniform(17, 20)  # Crítico baixo
            else:
                temp = np.random.uniform(30, 32)  # Crítico alto
        temp_hist.append(temp)
        
        # TDS (Sólidos Dissolvidos): alternar entre ideal, alerta e crítico
        rand = np.random.random()
        if rand < 0.6:  # 60% ideal
            tds = np.random.uniform(50, 500)
        elif rand < 0.9:  # 30% alerta
            tds = np.random.uniform(500, 600)
        else:  # 10% crítico
            tds = np.random.uniform(550, 650)
        solidos_hist.append(tds)
    
    # Converter para arrays numpy
    turbidez_hist = np.array(turbidez_hist)
    ph_hist = np.array(ph_hist)
    temp_hist = np.array(temp_hist)
    solidos_hist = np.array(solidos_hist)
    
    # Valores atuais (último ponto)
    turbidez_atual = turbidez_hist[-1]
    ph_atual = ph_hist[-1]
    temperatura_atual = temp_hist[-1]
    solidos_atual = solidos_hist[-1]
    
    # Criar DataFrame com histórico
    historico_qualidade = pd.DataFrame({
        'Turbidez (NTU)': turbidez_hist,
        'pH': ph_hist,
        'Temperatura (°C)': temp_hist,
        'Sólidos Dissolvidos (mg/L)': solidos_hist
    }, index=indices)
    
    return turbidez_atual, ph_atual, temperatura_atual, solidos_atual, historico_qualidade

def combinar_dados_mockados_e_reais(df_qualidade_real, dados_processados):
    """
    Combina dados mockados (até dia 13) com dados reais do ThingSpeak (dia 14 em diante).
    - Dados mockados: até dia 13 (Turbidez, Temp, TDS) / todos os dias (pH)
    - Dados reais: a partir do dia 14 para Turbidez, Temp, TDS
    - pH: sempre mockado
    
    Args:
        df_qualidade_real: DataFrame com dados reais do ThingSpeak (pode ser None)
        dados_processados: Dicionário com dados atuais processados do ThingSpeak
    
    Returns:
        Tuple: (turbidez_atual, ph_atual, temperatura_atual, solidos_atual, df_qualidade_combinado)
    """
    # Gerar dados mockados dos últimos 15 dias
    _, _, _, _, df_qualidade_mock = ler_dados_qualidade_agua()
    
    # Data limite para dados mockados (até fim do dia 13 de dezembro de 2024)
    # A partir do dia 14, apenas ThingSpeak (exceto pH que continua mockado)
    data_limite_mock = datetime(2025, 12, 13, 23, 59, 59)
    
    # Filtrar dados mockados: até dia 13 para Turbidez, Temp, TDS
    # pH continua mockado para todos os dias
    df_mock_filtrado = df_qualidade_mock[df_qualidade_mock.index <= data_limite_mock].copy()
    
    # Se não houver dados reais, retornar apenas os mockados (até dia 13)
    if df_qualidade_real is None or len(df_qualidade_real) == 0:
        print("📊 Usando apenas dados mockados até dia 13 (sem dados reais do ThingSpeak)")
        if len(df_mock_filtrado) > 0:
            turbidez_atual = df_mock_filtrado['Turbidez (NTU)'].iloc[-1]
            ph_atual = df_mock_filtrado['pH'].iloc[-1]
            temperatura_atual = df_mock_filtrado['Temperatura (°C)'].iloc[-1]
            solidos_atual = df_mock_filtrado['Sólidos Dissolvidos (mg/L)'].iloc[-1]
            return turbidez_atual, ph_atual, temperatura_atual, solidos_atual, df_mock_filtrado
        else:
            # Sem dados mockados disponíveis
            return 0, 7.0, 25, 0, pd.DataFrame()
    
    # Garantir que o índice dos dados reais é DatetimeIndex
    if not isinstance(df_qualidade_real.index, pd.DatetimeIndex):
        print("⚠️ Índice do DataFrame real não é DatetimeIndex")
        if len(df_mock_filtrado) > 0:
            return df_mock_filtrado['Turbidez (NTU)'].iloc[-1], df_mock_filtrado['pH'].iloc[-1], \
                   df_mock_filtrado['Temperatura (°C)'].iloc[-1], df_mock_filtrado['Sólidos Dissolvidos (mg/L)'].iloc[-1], df_mock_filtrado
        return 0, 7.0, 25, 0, df_mock_filtrado
    
    # Converter dados do ThingSpeak de UTC para UTC-3 (Horário de Brasília)
    try:
        if df_qualidade_real.index.tz is None:
            # Assumir que dados do ThingSpeak estão em UTC, converter para Brasília
            df_qualidade_real.index = pd.to_datetime(df_qualidade_real.index)
            df_qualidade_real.index = df_qualidade_real.index - timedelta(hours=3)
        elif hasattr(df_qualidade_real.index, 'tz') and df_qualidade_real.index.tz is not None:
            # Se tiver timezone, converter para Brasília e remover timezone info
            df_qualidade_real.index = df_qualidade_real.index.tz_convert('America/Sao_Paulo').tz_localize(None)
    except (AttributeError, TypeError) as e:
        print(f"⚠️ Erro ao converter timezone dos dados reais: {e}")
        pass
    
    # Remover timezone do índice mockado se houver
    try:
        if hasattr(df_mock_filtrado.index, 'tz') and df_mock_filtrado.index.tz is not None:
            df_mock_filtrado.index = df_mock_filtrado.index.tz_localize(None)
    except (AttributeError, TypeError):
        pass
    
    # Combinar: dados mockados até dia 13 + dados reais do ThingSpeak a partir do dia 14
    # EXCEÇÃO: pH continua sendo mockado para todos os dias
    
    # Começar com os dados mockados até dia 13
    df_combinado = df_mock_filtrado.copy()
    
    # Adicionar dados reais do ThingSpeak
    for idx in df_qualidade_real.index:
        # Gerar pH mockado para cada registro (real ou não)
        rand = np.random.random()
        if rand < 0.7:  # 70% ideal
            ph_mock = np.random.uniform(6.5, 8.5)
        elif rand < 0.95:  # 25% alerta
            if np.random.random() < 0.5:
                ph_mock = np.random.uniform(6.0, 6.5)
            else:
                ph_mock = np.random.uniform(8.5, 9.5)
        else:  # 5% crítico
            if np.random.random() < 0.5:
                ph_mock = np.random.uniform(5.0, 6.0)
            else:
                ph_mock = np.random.uniform(9.5, 10.0)
        
        if idx <= data_limite_mock:
            # Até dia 13: sobrescrever mockados com dados reais (exceto pH)
            if idx in df_combinado.index:
                ph_valor_mock = df_combinado.loc[idx, 'pH']  # Preservar pH mockado
                df_combinado.loc[idx] = df_qualidade_real.loc[idx]
                df_combinado.loc[idx, 'pH'] = ph_valor_mock  # Restaurar pH mockado
        else:
            # A partir do dia 14: usar apenas dados reais do ThingSpeak + pH mockado
            nova_linha = df_qualidade_real.loc[[idx]].copy()
            nova_linha['pH'] = ph_mock  # pH sempre mockado
            df_combinado = pd.concat([df_combinado, nova_linha])
    
    df_combinado = df_combinado.sort_index()
    
    # Atualizar valores atuais com a última medição do DataFrame combinado
    ultima_medicao = df_combinado.iloc[-1]
    turbidez_atual = ultima_medicao['Turbidez (NTU)']
    ph_atual = ultima_medicao['pH']  # pH é mockado
    temperatura_atual = ultima_medicao['Temperatura (°C)']
    solidos_atual = ultima_medicao['Sólidos Dissolvidos (mg/L)']
    
    print(f"✅ Dados combinados: {len(df_mock_filtrado)} pontos mockados (até dia 13) + {len(df_qualidade_real)} pontos reais = {len(df_combinado)} total")
    print(f"📊 Última medição: Turbidez={turbidez_atual:.2f}, pH={ph_atual:.2f} (mockado), Temp={temperatura_atual:.1f}°C, TDS={solidos_atual:.0f}")
    
    return turbidez_atual, ph_atual, temperatura_atual, solidos_atual, df_combinado

# =============================================================================
# FUNÇÕES AUXILIARES PARA GRÁFICOS
# =============================================================================

def configurar_grafico_plotly(fig, df_data):
    """
    Configura gráfico Plotly com botões de seleção de período (Última hora, Último dia, Última semana, Último mês).
    Usuário pode fazer zoom out. Autoscale/Reset retorna ao período selecionado.
    """
    # Calcular ranges para os diferentes períodos
    range_hora_str = None
    range_dia_str = None
    range_semana_str = None
    range_mes_str = None
    
    if df_data is not None and len(df_data) > 0 and isinstance(df_data.index, pd.DatetimeIndex):
        data_max = df_data.index.max()
        data_min = df_data.index.min()
        
        # Última hora
        data_min_hora = data_max - timedelta(hours=1)
        if data_min_hora < data_min:
            data_min_hora = data_min
        
        # Último dia
        data_min_dia = data_max - timedelta(days=1)
        if data_min_dia < data_min:
            data_min_dia = data_min
        
        # Última semana
        data_min_semana = data_max - timedelta(days=7)
        if data_min_semana < data_min:
            data_min_semana = data_min
        
        # Último mês
        data_min_mes = data_max - timedelta(days=30)
        if data_min_mes < data_min:
            data_min_mes = data_min
        
        # Converter para string ISO
        range_hora_str = [data_min_hora.strftime('%Y-%m-%d %H:%M:%S'), data_max.strftime('%Y-%m-%d %H:%M:%S')]
        range_dia_str = [data_min_dia.strftime('%Y-%m-%d %H:%M:%S'), data_max.strftime('%Y-%m-%d %H:%M:%S')]
        range_semana_str = [data_min_semana.strftime('%Y-%m-%d %H:%M:%S'), data_max.strftime('%Y-%m-%d %H:%M:%S')]
        range_mes_str = [data_min_mes.strftime('%Y-%m-%d %H:%M:%S'), data_max.strftime('%Y-%m-%d %H:%M:%S')]
    
    # Criar botões de seleção de período
    buttons = []
    
    if range_hora_str and range_dia_str and range_semana_str and range_mes_str:
        # Botão: Última hora
        buttons.append(
            dict(
                label="Última hora",
                method="relayout",
                args=[{"xaxis.range": range_hora_str}],
                args2=[{"xaxis.range": range_hora_str}]
            )
        )
        
        # Botão: Último dia
        buttons.append(
            dict(
                label="Último dia",
                method="relayout",
                args=[{"xaxis.range": range_dia_str}],
                args2=[{"xaxis.range": range_dia_str}]
            )
        )
        
        # Botão: Última semana
        buttons.append(
            dict(
                label="Última semana",
                method="relayout",
                args=[{"xaxis.range": range_semana_str}],
                args2=[{"xaxis.range": range_semana_str}]
            )
        )
        
        # Botão: Último mês
        buttons.append(
            dict(
                label="Último mês",
                method="relayout",
                args=[{"xaxis.range": range_mes_str}],
                args2=[{"xaxis.range": range_mes_str}]
            )
        )
    
    # Configurar layout geral com range inicial de última hora
    fig.update_layout(
        xaxis=dict(
            title_text="",
            tickformat='%d/%m/%Y<br>%H:%M',
            hoverformat='%d/%m/%Y %H:%M',
            type='date',
            showgrid=True,
            gridcolor='rgba(128, 128, 128, 0.2)',
            range=range_hora_str if range_hora_str else None,
            autorange=False,
            fixedrange=False
        ),
        hovermode='x unified',
        # Adicionar menu de botões para seleção de período
        updatemenus=[
            dict(
                type="buttons",
                direction="left",
                buttons=buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                active=0,
                x=0.0,
                xanchor="left",
                y=1.42,
                yanchor="top",
                bgcolor="rgba(0,0,0,0)",
                bordercolor="#1f77b4",
                borderwidth=1,
                font=dict(color="#1f77b4")
            )
        ] if buttons else []
    )
    
    return fig

# =============================================================================
# INTERFACE STREAMLIT
# =============================================================================

# Sidebar
with st.sidebar:
    # Logo centralizada com tamanho reduzido (75%)
    col_logo1, col_logo2, col_logo3 = st.columns([1, 3, 1])
    with col_logo2:
        st.image("assets/logo.png", use_container_width=True)
    
    st.markdown(
        "<h1 style='text-align: center;'>Monitor Hídrico</h1>",
        unsafe_allow_html=True
    )
    st.markdown("---")
    # Inicializar estado da página selecionada
    if 'page' not in st.session_state:
        st.session_state.page = "🏠 Dashboard"
    
    # Inicializar contador de novas notificações e notificações vistas
    if 'new_notifications_count' not in st.session_state:
        st.session_state.new_notifications_count = 0
    if 'last_seen_notifications_count' not in st.session_state:
        st.session_state.last_seen_notifications_count = 0
    
    # CSS customizado para esconder botões padrão e estilizar como texto
    st.markdown("""
        <style>
        /* Reduzir espaçamento entre título e divider */
        div[data-testid="stSidebar"] h1 {
            margin-bottom: 0.5rem;
        }
        div[data-testid="stSidebar"] hr {
            margin-top: 0.5rem;
            margin-bottom: 1rem;
        }
        /* Esconder o estilo padrão dos botões e fazer parecer texto */
        div[data-testid="stSidebar"] button {
            background: none;
            border: none;
            padding: 8px 0px;
            text-align: left;
            font-size: 16px;
            color: #fafafa;
            transition: color 0.3s ease;
        }
        div[data-testid="stSidebar"] button:hover {
            background: none;
            border: none;
            color: #1f77b4;
        }
        div[data-testid="stSidebar"] button:active,
        div[data-testid="stSidebar"] button:focus {
            background: none;
            border: none;
            box-shadow: none;
        }
        /* Estilo para badge de notificação */
        .notification-badge {
            background-color: #FF4444;
            color: white;
            border-radius: 50%;
            padding: 2px 6px;
            font-size: 11px;
            font-weight: bold;
            margin-left: 5px;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.6; }
            100% { opacity: 1; }
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Opções do menu como botões customizados
    if st.button("🏠 Dashboard", key="btn_home", use_container_width=True):
        st.session_state.page = "🏠 Dashboard"
    
    # Verificar se há notificações não vistas
    notifications_count = len(st.session_state.get('notifications', []))
    has_unseen = notifications_count > st.session_state.last_seen_notifications_count
    
    # Botão de notificações com badge vermelho se houver novas
    notif_label = "🔔 Notificações"
    if has_unseen or st.session_state.new_notifications_count > 0:
        notif_label = f"🔔 Notificações 🔴"
    
    if st.button(notif_label, key="btn_notif", use_container_width=True):
        st.session_state.page = "🔔 Notificações"
        # Marcar notificações como vistas
        st.session_state.last_seen_notifications_count = notifications_count
        st.session_state.new_notifications_count = 0
    
    if st.button("🚪 Logout", key="btn_logout", use_container_width=True):
        st.session_state.page = "🚪 Logout"
    
    opcao = st.session_state.page

# Conteúdo principal baseado na opção selecionada
if opcao == "🏠 Dashboard":
    st.title("💧 Painel de Monitoramento Hídrico")

    # 1. Carregar os dados (ThingSpeak ou simulados)
    try:
        print("🚀 Iniciando carregamento de dados...")
        
        # Tentar buscar dados do ThingSpeak primeiro
        df_thingspeak, sucesso_thingspeak = buscar_dados_thingspeak()
        
        if sucesso_thingspeak and df_thingspeak is not None:
            # Processar dados do ThingSpeak
            dados_processados = processar_dados_thingspeak(df_thingspeak)
            
            # Criar histórico de qualidade do ThingSpeak
            df_qualidade_real = criar_historico_qualidade(df_thingspeak)
            
            # Combinar dados mockados (15 dias) com dados reais (sobrescrever mockados onde houver real)
            turbidez_atual, ph_atual, temperatura_atual, solidos_atual, df_qualidade = combinar_dados_mockados_e_reais(
                df_qualidade_real, dados_processados
            )
            
            # Dados básicos simulados (não disponíveis no ThingSpeak)
            nivel, temperatura, vazao, df_historico = ler_dados_simulados()
            
        else:
            st.warning("⚠️ Não foi possível conectar ao ThingSpeak, usando dados mockados")
            print("🔄 Usando dados mockados como fallback...")
            turbidez_atual, ph_atual, temperatura_atual, solidos_atual, df_qualidade = ler_dados_qualidade_agua()
            nivel, temperatura, vazao, df_historico = ler_dados_simulados()
            
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        print(f"❌ Erro crítico: {e}")
        st.stop()

    # Mostrar o horário do último dado recebido do ThingSpeak
    # Pegar o timestamp do último registro do DataFrame
    if df_qualidade is not None and len(df_qualidade) > 0:
        ultimo_timestamp = df_qualidade.index.max()
        if isinstance(ultimo_timestamp, pd.Timestamp):
            ultimo_dado_hora = ultimo_timestamp.strftime("%H:%M:%S")
        else:
            ultimo_dado_hora = str(ultimo_timestamp)
    else:
        ultimo_dado_hora = "N/A"
    
    col_info, col_btn = st.columns([4, 1])
    
    with col_info:
        st.info(f"Último dado recebido: **{ultimo_dado_hora}**", icon="🕒")
    
    with col_btn:
        if st.button("Atualizar Dados", key="refresh_data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # 2. SEÇÃO DE MÉTRICAS ATUAIS (CARDS) - Indicadores de Qualidade da Última Medição
    st.markdown("## Indicadores de Qualidade Atual")
    st.caption("Dados da última medição registrada nos gráficos")

    # Calcular qualidade geral
    qualidade_atual = calcular_qualidade_agua(turbidez_atual, ph_atual, temperatura_atual, solidos_atual)

    col1, col2, col3, col4, col5 = st.columns(5)

    # Métrica 1: Turbidez
    # Ideal < 1.0, Alerta 1.0-5.0, Crítico > 5.0
    if turbidez_atual < 1.0:
        turbidez_status = "Ideal"
        turbidez_cor = 'normal'
    elif turbidez_atual <= 5.0:
        turbidez_status = "Atenção"
        turbidez_cor = 'off'
    else:
        turbidez_status = "Crítico"
        turbidez_cor = 'inverse'

    col1.metric(
        label="Turbidez",
        value=f"{turbidez_atual:.2f} NTU",
        delta=turbidez_status,
        delta_color=turbidez_cor
    )

    # Métrica 2: pH
    # Ideal 6.5-8.5, Alerta 6.0-6.5 ou 8.5-9.5, Crítico < 6.0 ou > 9.5
    if 6.5 <= ph_atual <= 8.5:
        ph_status = "Ideal"
        ph_cor = 'normal'
    elif (6.0 <= ph_atual < 6.5) or (8.5 < ph_atual <= 9.5):
        ph_status = "Atenção"
        ph_cor = 'off'
    else:
        ph_status = "Crítico"
        ph_cor = 'inverse'

    col2.metric(
        label="pH",
        value=f"{ph_atual:.2f}",
        delta=ph_status,
        delta_color=ph_cor
    )

    # Métrica 3: Temperatura da Água
    # Ideal 20-28°C, Alerta variação > 3°C, Crítico variação > 5°C
    if 20 <= temperatura_atual <= 28:
        temp_status = "Ideal"
        temp_cor = 'normal'
    elif 17 <= temperatura_atual < 20 or 28 < temperatura_atual <= 31:
        temp_status = "Atenção"
        temp_cor = 'off'
    else:
        temp_status = "Crítico"
        temp_cor = 'inverse'

    col3.metric(
        label="Temperatura",
        value=f"{temperatura_atual:.1f} °C",
        delta=temp_status,
        delta_color=temp_cor
    )

    # Métrica 4: TDS (Sólidos Dissolvidos)
    # Ideal < 500, Alerta 500-1000, Crítico > 1000
    if solidos_atual < 500:
        tds_status = "Ideal"
        tds_cor = 'normal'
    elif solidos_atual <= 1000:
        tds_status = "Atenção"
        tds_cor = 'off'
    else:
        tds_status = "Crítico"
        tds_cor = 'inverse'

    col4.metric(
        label="TDS",
        value=f"{solidos_atual:.0f} mg/L",
        delta=tds_status,
        delta_color=tds_cor
    )

    # Métrica 5: Qualidade Geral
    if qualidade_atual >= 80:
        qualidade_emoji = "🟢"
        qualidade_texto = "EXCELENTE"
        qualidade_cor = "green"
    elif qualidade_atual >= 60:
        qualidade_emoji = "🟡"
        qualidade_texto = "BOA"
        qualidade_cor = "#FFC107"
    elif qualidade_atual >= 40:
        qualidade_emoji = "🟠"
        qualidade_texto = "REGULAR"
        qualidade_cor = "orange"
    else:
        qualidade_emoji = "🔴"
        qualidade_texto = "RUIM"
        qualidade_cor = "red"

    with col5:
        st.markdown(
            f"""
            <div style="padding: 10px; border-radius: 8px; border: 1px solid lightgray; text-align: center; background-color: {qualidade_cor}; color: white; margin-top: 15px;">
                <p style="font-size: 14px; margin: 0; font-weight: bold;">Qualidade Geral</p>
                <p style="font-size: 20px; margin: 0; font-weight: bold;">{qualidade_emoji} {qualidade_texto}</p>
                <p style="font-size: 18px; margin: 5px 0 0 0; font-weight: bold;">{qualidade_atual:.1f}%</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # 3. SEÇÃO DE GRÁFICOS DE QUALIDADE DA ÁGUA
    st.markdown("## Parâmetros de Qualidade da Água")

    # Gráfico 1: Turbidez
    if 'Turbidez (NTU)' in df_qualidade.columns:
        fig_turbidez = px.line(df_qualidade, y='Turbidez (NTU)', title='Turbidez da Água')
        fig_turbidez.add_hline(y=1, line_dash="dash", line_color="green")
        fig_turbidez.add_hline(y=5, line_dash="dash", line_color="orange")
        fig_turbidez.update_layout(
            height=300,
            annotations=[
                dict(
                    text="<span style='color:#00CC66'>── Ideal (1 NTU)</span><br><span style='color:#FFA500'>── Aceitável (5 NTU)</span>",
                    xref="paper", yref="paper",
                    x=1, y=1.28,
                    xanchor="right", yanchor="top",
                    showarrow=False,
                    font=dict(size=11, color="white"),
                    align="right"
                )
            ]
        )
        fig_turbidez.update_xaxes(title_text="")
        fig_turbidez = configurar_grafico_plotly(fig_turbidez, df_qualidade)
        st.plotly_chart(fig_turbidez, use_container_width=True)

    # Gráfico 2: pH
    if 'pH' in df_qualidade.columns:
        fig_ph = px.line(df_qualidade, y='pH', title='pH da Água')
        fig_ph.add_hline(y=7.0, line_dash="dash", line_color="green")
        fig_ph.add_hline(y=6.5, line_dash="dash", line_color="orange")
        fig_ph.add_hline(y=8.5, line_dash="dash", line_color="orange")
        fig_ph.update_layout(
            height=300,
            annotations=[
                dict(
                    text="<span style='color:#00CC66'>── Neutro (7.0)</span><br><span style='color:#FFA500'>── Limites (6.5 / 8.5)</span>",
                    xref="paper", yref="paper",
                    x=1, y=1.28,
                    xanchor="right", yanchor="top",
                    showarrow=False,
                    font=dict(size=11, color="white"),
                    align="right"
                )
            ]
        )
        fig_ph.update_xaxes(title_text="")
        fig_ph = configurar_grafico_plotly(fig_ph, df_qualidade)
        st.plotly_chart(fig_ph, use_container_width=True)

    # Gráfico 3: Temperatura
    if 'Temperatura (°C)' in df_qualidade.columns:
        fig_temp = px.line(df_qualidade, y='Temperatura (°C)', title='Temperatura da Água')
        fig_temp.add_hline(y=22.5, line_dash="dash", line_color="green")
        fig_temp.add_hline(y=25, line_dash="dash", line_color="orange")
        fig_temp.update_layout(
            height=300,
            annotations=[
                dict(
                    text="<span style='color:#00CC66'>── Ideal (22.5°C)</span><br><span style='color:#FFA500'>── Limite (25°C)</span>",
                    xref="paper", yref="paper",
                    x=1, y=1.28,
                    xanchor="right", yanchor="top",
                    showarrow=False,
                    font=dict(size=11, color="white"),
                    align="right"
                )
            ]
        )
        fig_temp.update_xaxes(title_text="")
        fig_temp = configurar_grafico_plotly(fig_temp, df_qualidade)
        st.plotly_chart(fig_temp, use_container_width=True)

    # Gráfico 4: Sólidos Dissolvidos (TDS)
    if 'Sólidos Dissolvidos (mg/L)' in df_qualidade.columns:
        fig_solidos = px.line(df_qualidade, y='Sólidos Dissolvidos (mg/L)', title='Sólidos Dissolvidos (TDS)')
        fig_solidos.add_hline(y=500, line_dash="dash", line_color="green")
        fig_solidos.add_hline(y=1000, line_dash="dash", line_color="orange")
        fig_solidos.update_layout(
            height=300,
            annotations=[
                dict(
                    text="<span style='color:#00CC66'>── Ideal (500 mg/L)</span><br><span style='color:#FFA500'>── Aceitável (1000 mg/L)</span>",
                    xref="paper", yref="paper",
                    x=1, y=1.28,
                    xanchor="right", yanchor="top",
                    showarrow=False,
                    font=dict(size=11, color="white"),
                    align="right"
                )
            ]
        )
        fig_solidos.update_xaxes(title_text="")
        fig_solidos = configurar_grafico_plotly(fig_solidos, df_qualidade)
        st.plotly_chart(fig_solidos, use_container_width=True)

    # Gráfico 5: Qualidade Geral da Água
    # Calcular histórico de qualidade
    if df_qualidade is not None and len(df_qualidade) > 0:
        qualidade_hist = []
        for i in range(len(df_qualidade)):
            turb = df_qualidade['Turbidez (NTU)'].iloc[i] if 'Turbidez (NTU)' in df_qualidade.columns else 0
            ph = df_qualidade['pH'].iloc[i] if 'pH' in df_qualidade.columns else 7.0
            temp = df_qualidade['Temperatura (°C)'].iloc[i] if 'Temperatura (°C)' in df_qualidade.columns else 25
            sol = df_qualidade['Sólidos Dissolvidos (mg/L)'].iloc[i] if 'Sólidos Dissolvidos (mg/L)' in df_qualidade.columns else 0
            qualidade_hist.append(calcular_qualidade_agua(turb, ph, temp, sol))
        
        df_qualidade['Qualidade Geral (%)'] = qualidade_hist
        
        fig_qualidade = px.line(df_qualidade, y='Qualidade Geral (%)', title='Qualidade Geral da Água')
        fig_qualidade.add_hline(y=80, line_dash="dash", line_color="green")
        fig_qualidade.add_hline(y=60, line_dash="dash", line_color="orange")
        fig_qualidade.add_hline(y=40, line_dash="dash", line_color="red")
        fig_qualidade.update_layout(
            height=300,
            annotations=[
                dict(
                    text="<span style='color:#00CC66'>── Boa (80%)</span><br><span style='color:#FFA500'>── Regular (60%)</span><br><span style='color:#FF4444'>── Ruim (40%)</span>",
                    xref="paper", yref="paper",
                    x=1, y=1.28,
                    xanchor="right", yanchor="top",
                    showarrow=False,
                    font=dict(size=11, color="white"),
                    align="right"
                )
            ]
        )
        fig_qualidade.update_xaxes(title_text="")
        fig_qualidade = configurar_grafico_plotly(fig_qualidade, df_qualidade)
        st.plotly_chart(fig_qualidade, use_container_width=True)
    
    # Auto-refresh: atualiza automaticamente a cada 30 segundos
    time.sleep(30)
    st.cache_data.clear()
    st.rerun()

elif opcao == "🔔 Notificações":
    st.title("🔔 Notificações e Alertas")
    st.caption("Alertas de qualidade da água recebidos via AWS SNS/SQS")
    
    # Inicializar o handler de notificações
    try:
        # Verificar se as credenciais AWS estão disponíveis
        if "SQS_QUEUE_URL" in st.secrets and "AWS_REGION" in st.secrets:
            # Inicializar handler (apenas uma vez)
            if 'notifications_handler' not in st.session_state:
                st.session_state.notifications_handler = NotificationsHandler(
                    queue_url=st.secrets["SQS_QUEUE_URL"],
                    aws_region=st.secrets["AWS_REGION"]
                )
            
            # Inicializar lista de notificações
            if 'notifications' not in st.session_state:
                st.session_state.notifications = []
            
            # Controles de atualização
            col_btn, col_auto = st.columns([2, 3])
            
            with col_btn:
                if st.button("🔄 Buscar Todas as Notificações", use_container_width=False, type="primary"):
                    new_notifications = st.session_state.notifications_handler.get_all_notifications(max_messages=10)
                    
                    if new_notifications:
                        # Adiciona as novas notificações no topo da lista
                        for notif in reversed(new_notifications):
                            st.session_state.notifications.insert(0, notif)
                        
                        # Atualizar contador de vistas (estamos na página, então marcamos como vistas)
                        st.session_state.last_seen_notifications_count = len(st.session_state.notifications)
                        st.session_state.new_notifications_count = 0
                        
                        st.success(f"✅ {len(new_notifications)} nova(s) notificação(ões) recebida(s)!")
                        st.rerun()
                    else:
                        st.info("Nenhuma notificação nova na fila no momento.")
            
            with col_auto:
                auto_refresh = st.checkbox("Auto-atualizar a cada 30s", value=False)
            
            st.markdown("---")
            
            # Exibir histórico de notificações
            st.markdown("### 📬 Histórico de Alertas")
            
            if not st.session_state.notifications:
                st.info("Nenhum alerta recebido ainda. Clique em 'Buscar Todas as Notificações' para buscar alertas da fila.")
            else:
                # Contador de notificações
                st.caption(f"Total de alertas recebidos: **{len(st.session_state.notifications)}**")
                st.markdown("")
                
                # Criar lista de dados para a tabela
                table_data = []
                for i, notif in enumerate(st.session_state.notifications):
                    params = st.session_state.notifications_handler.parse_notification_params(notif)
                    
                    # Adicionar número do alerta
                    row = {
                        '#': len(st.session_state.notifications) - i,
                        'Assunto': params['Assunto'],
                        'Turbidez (NTU)': params['Turbidez (NTU)'],
                        'pH': params['pH'],
                        'Temperatura (°C)': params['Temperatura (°C)'],
                        'TDS (mg/L)': params['TDS (mg/L)'],
                        'Data/Hora': params['Data/Hora']
                    }
                    table_data.append(row)
                
                # Criar DataFrame (já está ordenado com mais recente no topo)
                df_alertas = pd.DataFrame(table_data)
                
                # Definir função de estilo para colorir linhas baseado no tipo de alerta
                def highlight_rows(row):
                    if 'crítico' in str(row['Assunto']).lower():
                        return ['background-color: rgba(255, 75, 75, 0.2)'] * len(row)
                    elif 'atenção' in str(row['Assunto']).lower() or 'alerta' in str(row['Assunto']).lower():
                        return ['background-color: rgba(255, 193, 7, 0.2)'] * len(row)
                    else:
                        return ['background-color: rgba(33, 150, 243, 0.1)'] * len(row)
                
                # Aplicar estilo e formatação
                styled_df = df_alertas.style.apply(highlight_rows, axis=1).format({
                    'Turbidez (NTU)': lambda x: f'{x:.2f}' if isinstance(x, (int, float)) else x,
                    'pH': lambda x: f'{x:.2f}' if isinstance(x, (int, float)) else x,
                    'Temperatura (°C)': lambda x: f'{x:.2f}' if isinstance(x, (int, float)) else x,
                    'TDS (mg/L)': lambda x: f'{x:.2f}' if isinstance(x, (int, float)) else x
                })
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )
            
            # Auto-refresh: busca automaticamente a cada 30 segundos
            if auto_refresh:
                time.sleep(30)
                
                # Buscar novas notificações automaticamente
                new_notifications = st.session_state.notifications_handler.get_all_notifications(max_messages=10)
                
                if new_notifications:
                    # Adiciona as novas notificações no topo da lista
                    for notif in reversed(new_notifications):
                        st.session_state.notifications.insert(0, notif)
                    
                    # Atualizar contador de vistas (estamos na página, então marcamos como vistas)
                    st.session_state.last_seen_notifications_count = len(st.session_state.notifications)
                    st.session_state.new_notifications_count = 0
                
                # Recarrega a página
                st.rerun()
                
        else:
            st.warning("⚠️ Credenciais AWS não configuradas. Configure SQS_QUEUE_URL e AWS_REGION em st.secrets.")
            
    except Exception as e:
        st.error(f"Erro ao carregar sistema de notificações: {e}")
        st.info("Configure as credenciais AWS no arquivo de secrets do Streamlit.")

elif opcao == "🚪 Logout":
    st.title("🚪 Logout")
    st.info("Você foi desconectado do sistema.")
    st.button("Confirmar Logout", key="logout_confirm")
