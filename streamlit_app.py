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
    Simula dados de qualidade da água: turbidez, pH, temperatura e sólidos dissolvidos.
    """
    # Dados atuais
    turbidez_atual = np.random.uniform(TURBIDEZ_MIN, TURBIDEZ_MAX)
    ph_atual = np.random.uniform(PH_MIN, PH_MAX)
    temperatura_atual = np.random.uniform(TEMP_MIN, TEMP_MAX)
    solidos_atual = np.random.uniform(SOLIDOS_MIN, SOLIDOS_MAX)
    
    # Histórico (últimas 2 horas)
    num_pontos = 60
    indices = pd.date_range(end=datetime.now(), periods=num_pontos, freq='2min')
    
    # Simulação de tendências com ruído
    turbidez_hist = np.linspace(1, turbidez_atual, num_pontos) + np.random.normal(0, 0.2, num_pontos)
    ph_hist = np.linspace(7.2, ph_atual, num_pontos) + np.random.normal(0, 0.1, num_pontos)
    temp_hist = np.linspace(25, temperatura_atual, num_pontos) + np.random.normal(0, 1, num_pontos)
    solidos_hist = np.linspace(200, solidos_atual, num_pontos) + np.random.normal(0, 50, num_pontos)
    
    # Garantir limites realistas
    turbidez_hist = np.clip(turbidez_hist, TURBIDEZ_MIN, TURBIDEZ_MAX)
    ph_hist = np.clip(ph_hist, PH_MIN, PH_MAX)
    temp_hist = np.clip(temp_hist, TEMP_MIN, TEMP_MAX)
    solidos_hist = np.clip(solidos_hist, SOLIDOS_MIN, SOLIDOS_MAX)
    
    historico_qualidade = pd.DataFrame({
        'Turbidez (NTU)': turbidez_hist,
        'pH': ph_hist,
        'Temperatura (°C)': temp_hist,
        'Sólidos Dissolvidos (mg/L)': solidos_hist
    }, index=indices)
    
    return turbidez_atual, ph_atual, temperatura_atual, solidos_atual, historico_qualidade

# =============================================================================
# FUNÇÕES AUXILIARES PARA GRÁFICOS
# =============================================================================

def configurar_grafico_plotly(fig, df_data):
    """
    Configura gráfico Plotly com tradução de meses para português e range inicial de 3 dias.
    """
    # Dicionário de meses em português
    meses_pt = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    
    # Calcular range inicial (últimos 3 dias)
    range_min = None
    range_max = None
    
    if df_data is not None and len(df_data) > 0 and isinstance(df_data.index, pd.DatetimeIndex):
        data_max = df_data.index.max()
        data_min_range = data_max - timedelta(days=3)
        # Garantir que não vamos além dos dados disponíveis
        data_real_min = df_data.index.min()
        if data_min_range < data_real_min:
            data_min_range = data_real_min
        
        range_min = data_min_range
        range_max = data_max
    
    # Configurar formato de data e range inicial
    # Usar formato brasileiro (dd/mm/yyyy) para evitar nomes de meses em inglês
    fig.update_xaxes(
        title_text="",
        tickformat='%d/%m/%Y<br>%H:%M',
        hoverformat='%d/%m/%Y %H:%M',
        range=[range_min, range_max] if range_min and range_max else None,
        autorange=False  # Desabilitar autorange para manter o range inicial, mas permite zoom manual
    )
    
    # Atualizar hovertemplate para usar formato brasileiro com meses em português
    for trace in fig.data:
        if hasattr(trace, 'hovertemplate') and trace.hovertemplate:
            # Substituir nomes de meses em inglês por português usando formato customizado
            # O Plotly usará o formato especificado em hoverformat
            pass
    
    # Configurar layout geral
    fig.update_layout(
        xaxis=dict(
            type='date',
            showgrid=True,
            gridcolor='rgba(128, 128, 128, 0.2)'
        ),
        hovermode='x unified'
    )
    
    return fig

# =============================================================================
# INTERFACE STREAMLIT
# =============================================================================

# Sidebar
with st.sidebar:
    st.markdown(
        "<h1 style='text-align: center;'>Monitor Hídrico</h1>",
        unsafe_allow_html=True
    )
    st.markdown("---")
    # Inicializar estado da página selecionada
    if 'page' not in st.session_state:
        st.session_state.page = "🏠 Dashboard"
    
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
        </style>
    """, unsafe_allow_html=True)
    
    # Opções do menu como botões customizados
    if st.button("🏠 Dashboard", key="btn_home", use_container_width=True):
        st.session_state.page = "🏠 Dashboard"
    
    if st.button("🔔 Notificações", key="btn_notif", use_container_width=True):
        st.session_state.page = "🔔 Notificações"
    
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
            
            if dados_processados:
                # Usar dados reais do ThingSpeak
                turbidez_atual = dados_processados['turbidez']
                ph_atual = dados_processados['ph']
                temperatura_atual = dados_processados['temperatura']
                solidos_atual = dados_processados['solidos_dissolvidos']
                
                # Criar histórico de qualidade
                df_qualidade = criar_historico_qualidade(df_thingspeak)
                
                if df_qualidade is None:
                    # Fallback para dados simulados se não conseguir criar histórico
                    turbidez_atual, ph_atual, temperatura_atual, solidos_atual, df_qualidade = ler_dados_qualidade_agua()
                
                # Dados básicos simulados (não disponíveis no ThingSpeak)
                nivel, temperatura, vazao, df_historico = ler_dados_simulados()
                
            else:
                st.warning("⚠️ Erro ao processar dados do ThingSpeak, usando dados simulados")
                turbidez_atual, ph_atual, temperatura_atual, solidos_atual, df_qualidade = ler_dados_qualidade_agua()
                nivel, temperatura, vazao, df_historico = ler_dados_simulados()
        else:
            st.warning("⚠️ Não foi possível conectar ao ThingSpeak, usando dados simulados")
            print("🔄 Usando dados simulados como fallback...")
            turbidez_atual, ph_atual, temperatura_atual, solidos_atual, df_qualidade = ler_dados_qualidade_agua()
            nivel, temperatura, vazao, df_historico = ler_dados_simulados()
            
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        print(f"❌ Erro crítico: {e}")
        st.stop()

    # Espaço reservado para o tempo da última atualização e botão de atualizar
    # Converter UTC para UTC-3 (Horário de Brasília)
    utc = pytz.UTC
    brasilia_tz = pytz.timezone('America/Sao_Paulo')
    agora_utc = datetime.now(utc)
    agora_brasilia = agora_utc.astimezone(brasilia_tz)
    ultima_atualizacao = agora_brasilia.strftime("%H:%M:%S")
    col_info, col_btn = st.columns([4, 1])
    
    with col_info:
        st.info(f"Última atualização: **{ultima_atualizacao}**", icon="🕒")
    
    with col_btn:
        if st.button("Atualizar Dados", key="refresh_data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # 2. SEÇÃO DE MÉTRICAS ATUAIS (CARDS) - Indicadores de Qualidade
    st.markdown("## Indicadores de Qualidade Atual")

    # Calcular qualidade geral
    qualidade_atual = calcular_qualidade_agua(turbidez_atual, ph_atual, temperatura_atual, solidos_atual)

    col1, col2, col3, col4 = st.columns(4)

    # Métrica 1: Turbidez
    turbidez_status = "Normal" if turbidez_atual <= 5.0 else "Alerta"
    turbidez_cor = 'normal' if turbidez_atual <= 5.0 else 'inverse'

    col1.metric(
        label="Turbidez",
        value=f"{turbidez_atual:.2f} NTU",
        delta=turbidez_status,
        delta_color=turbidez_cor
    )

    # Métrica 2: Temperatura da Água
    temp_status = "Alerta" if temperatura_atual >= 30 else "Normal"
    temp_cor = 'inverse' if temperatura_atual >= 30 else 'normal'

    col2.metric(
        label="Temperatura da Água",
        value=f"{temperatura_atual:.1f} °C",
        delta=temp_status,
        delta_color=temp_cor
    )

    # Métrica 3: TDS (Sólidos Dissolvidos)
    tds_status = "Normal" if solidos_atual <= 1000 else "Alerta"
    tds_cor = 'normal' if solidos_atual <= 1000 else 'inverse'

    col3.metric(
        label="TDS",
        value=f"{solidos_atual:.0f} mg/L",
        delta=tds_status,
        delta_color=tds_cor
    )

    # Métrica 4: Qualidade Geral
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

    with col4:
        st.markdown(
            f"""
            <div style="padding: 10px; border-radius: 8px; border: 1px solid lightgray; text-align: center; background-color: {qualidade_cor}; color: white; margin-top: 15px;">
                <p style="font-size: 16px; margin: 0; font-weight: bold;">Qualidade Geral</p>
                <p style="font-size: 24px; margin: 0; font-weight: bold;">{qualidade_emoji} {qualidade_texto}</p>
                <p style="font-size: 20px; margin: 5px 0 0 0; font-weight: bold;">{qualidade_atual:.1f}%</p>
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
        fig_turbidez.add_hline(y=1, line_dash="dash", line_color="green", annotation_text="Ideal (1 NTU)")
        fig_turbidez.add_hline(y=5, line_dash="dash", line_color="orange", annotation_text="Aceitável (5 NTU)")
        fig_turbidez.update_layout(height=300)
        fig_turbidez.update_xaxes(title_text="")
        fig_turbidez = configurar_grafico_plotly(fig_turbidez, df_qualidade)
        st.plotly_chart(fig_turbidez, use_container_width=True)

    # Gráfico 2: pH
    if 'pH' in df_qualidade.columns:
        fig_ph = px.line(df_qualidade, y='pH', title='pH da Água')
        fig_ph.add_hline(y=7.0, line_dash="dash", line_color="green", annotation_text="Neutro (7.0)")
        fig_ph.add_hline(y=6.5, line_dash="dash", line_color="orange", annotation_text="Limite Mínimo (6.5)")
        fig_ph.add_hline(y=8.5, line_dash="dash", line_color="orange", annotation_text="Limite Máximo (8.5)")
        fig_ph.update_layout(height=300)
        fig_ph.update_xaxes(title_text="")
        fig_ph = configurar_grafico_plotly(fig_ph, df_qualidade)
        st.plotly_chart(fig_ph, use_container_width=True)

    # Gráfico 3: Temperatura
    if 'Temperatura (°C)' in df_qualidade.columns:
        fig_temp = px.line(df_qualidade, y='Temperatura (°C)', title='Temperatura da Água')
        fig_temp.add_hline(y=22.5, line_dash="dash", line_color="green", annotation_text="Ideal (22.5°C)")
        fig_temp.add_hline(y=25, line_dash="dash", line_color="orange", annotation_text="Limite Superior (25°C)")
        fig_temp.update_layout(height=300)
        fig_temp.update_xaxes(title_text="")
        fig_temp = configurar_grafico_plotly(fig_temp, df_qualidade)
        st.plotly_chart(fig_temp, use_container_width=True)

    # Gráfico 4: Sólidos Dissolvidos (TDS)
    if 'Sólidos Dissolvidos (mg/L)' in df_qualidade.columns:
        fig_solidos = px.line(df_qualidade, y='Sólidos Dissolvidos (mg/L)', title='Sólidos Dissolvidos (TDS)')
        fig_solidos.add_hline(y=500, line_dash="dash", line_color="green", annotation_text="Ideal (500 mg/L)")
        fig_solidos.add_hline(y=1000, line_dash="dash", line_color="orange", annotation_text="Aceitável (1000 mg/L)")
        fig_solidos.update_layout(height=300)
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
        fig_qualidade.add_hline(y=80, line_dash="dash", line_color="green", annotation_text="Boa Qualidade (80%)")
        fig_qualidade.add_hline(y=60, line_dash="dash", line_color="orange", annotation_text="Qualidade Regular (60%)")
        fig_qualidade.add_hline(y=40, line_dash="dash", line_color="red", annotation_text="Qualidade Ruim (40%)")
        fig_qualidade.update_layout(height=300)
        fig_qualidade.update_xaxes(title_text="")
        fig_qualidade = configurar_grafico_plotly(fig_qualidade, df_qualidade)
        st.plotly_chart(fig_qualidade, use_container_width=True)

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
