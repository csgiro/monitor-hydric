# -*- coding: utf-8 -*-
"""
Módulo de integração com ThingSpeak API
Responsável por buscar e processar dados do ThingSpeak
"""

import requests
import pandas as pd
import json
from datetime import datetime

# =============================================================================
# CONFIGURAÇÕES DO THINGSPEAK
# =============================================================================

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
        
        print(f"📡 URL da requisição: {url}")
        print(f"🔑 Parâmetros: {params}")
        
        response = requests.get(url, params=params, timeout=10)
        print(f"📊 Status da resposta: {response.status_code}")
        
        response.raise_for_status()
        
        data = response.json()
        print(f"📋 Dados recebidos: {json.dumps(data, indent=2)}")
        
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
    
    Mapeamento dos campos conforme dados reais:
    - field1: Turbidez (NTU)
    - field2: pH
    - field3: Temperatura (°C)
    - field4: Sólidos Dissolvidos/TDS (mg/L)
    
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
    
    # Função auxiliar para converter valores com segurança
    def safe_float(value, default):
        try:
            if value is None or value == '' or str(value).lower() == 'nan':
                return default
            return float(value)
        except (ValueError, TypeError):
            return default
    
    # Mapear campos conforme dados reais
    dados_processados = {
        'turbidez': safe_float(ultimo_registro.get('field1'), 0) if 'field1' in df_thingspeak.columns else 0,
        'ph': safe_float(ultimo_registro.get('field2'), 7.0) if 'field2' in df_thingspeak.columns else 7.0,
        'temperatura': safe_float(ultimo_registro.get('field3'), 25) if 'field3' in df_thingspeak.columns else 25,
        'solidos_dissolvidos': safe_float(ultimo_registro.get('field4'), 0) if 'field4' in df_thingspeak.columns else 0,
    }
    
    print(f"📊 Dados processados: {dados_processados}")
    
    return dados_processados

def criar_historico_qualidade(df_thingspeak):
    """
    Cria DataFrame com histórico de qualidade da água baseado nos dados do ThingSpeak.
    """
    print("📈 Criando histórico de qualidade da água...")
    
    if df_thingspeak is None or len(df_thingspeak) == 0:
        print("⚠️ Nenhum dado para criar histórico")
        return None
    
    # Mapear campos conforme dados reais
    campos_qualidade = []
    nomes_qualidade = []
    
    if 'field1' in df_thingspeak.columns:
        campos_qualidade.append('field1')
        nomes_qualidade.append('Turbidez (NTU)')
    if 'field2' in df_thingspeak.columns:
        campos_qualidade.append('field2')
        nomes_qualidade.append('pH')
    if 'field3' in df_thingspeak.columns:
        campos_qualidade.append('field3')
        nomes_qualidade.append('Temperatura (°C)')
    if 'field4' in df_thingspeak.columns:
        campos_qualidade.append('field4')
        nomes_qualidade.append('Sólidos Dissolvidos (mg/L)')
    
    if campos_qualidade:
        df_qualidade = df_thingspeak[campos_qualidade].copy()
        df_qualidade.columns = nomes_qualidade
        
        for col in df_qualidade.columns:
            df_qualidade[col] = pd.to_numeric(df_qualidade[col], errors='coerce').fillna(0)
        
        # Adicionar índice de tempo se disponível
        if 'created_at' in df_thingspeak.columns:
            df_qualidade.index = df_thingspeak['created_at']
        
        print(f"✅ Histórico criado com {len(df_qualidade)} registros")
        print(f"📊 Colunas: {list(df_qualidade.columns)}")
        
        return df_qualidade
    else:
        print("⚠️ Nenhum campo de qualidade encontrado")
        return None

def calcular_qualidade_agua(turbidez, ph, temperatura, solidos_dissolvidos):
    """
    Calcula um índice de qualidade da água baseado nos 4 parâmetros.
    
    Parâmetros:
    - turbidez: em NTU (ideal: 0-1 NTU)
    - ph: escala de 0-14 (ideal: 6.5-8.5)
    - temperatura: em °C (ideal: 20-25°C)
    - solidos_dissolvidos: em mg/L (ideal: 0-500 mg/L)
    """
    # Garantir que todos os valores sejam numéricos
    turbidez = float(turbidez) if turbidez is not None else 0
    ph = float(ph) if ph is not None else 7.0
    temperatura = float(temperatura) if temperatura is not None else 25
    solidos_dissolvidos = float(solidos_dissolvidos) if solidos_dissolvidos is not None else 0
    
    print(f"🧮 Calculando qualidade da água...")
    print(f"   Turbidez: {turbidez} NTU")
    print(f"   pH: {ph}")
    print(f"   Temperatura: {temperatura}°C")
    print(f"   Sólidos Dissolvidos: {solidos_dissolvidos} mg/L")
    
    # Normalização dos parâmetros (0-100)
    # Turbidez: ideal 0-1 NTU, aceitável até 5 NTU
    turbidez_score = max(0, 100 - turbidez * 20) if turbidez <= 5 else 0
    
    # pH: ideal 6.5-8.5, aceitável 6.0-9.0
    if 6.0 <= ph <= 9.0:
        ph_score = 100 - abs(ph - 7.0) * 20  # Penaliza distância do pH ideal (7.0)
    else:
        ph_score = 0
    
    # Temperatura: ideal 20-25°C, aceitável 15-30°C
    if 15 <= temperatura <= 30:
        temp_score = 100 - abs(temperatura - 22.5) * 4  # Penaliza distância da temperatura ideal
    else:
        temp_score = 0
    
    # Sólidos Dissolvidos: ideal 0-500 mg/L, aceitável até 1000 mg/L
    if solidos_dissolvidos <= 1000:
        solidos_score = max(0, 100 - solidos_dissolvidos / 10)  # Penaliza valores altos
    else:
        solidos_score = 0
    
    # Média ponderada (todos com peso igual)
    qualidade = (turbidez_score + ph_score + temp_score + solidos_score) / 4
    
    print(f"📊 Scores individuais:")
    print(f"   Turbidez: {turbidez_score:.1f}%")
    print(f"   pH: {ph_score:.1f}%")
    print(f"   Temperatura: {temp_score:.1f}%")
    print(f"   Sólidos Dissolvidos: {solidos_score:.1f}%")
    print(f"🎯 Qualidade Geral: {qualidade:.1f}%")
    
    return qualidade
