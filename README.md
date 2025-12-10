# 💧 Dashboard de Monitoramento Hídrico

Dashboard interativo desenvolvido com Streamlit para visualização de dados de qualidade da água em tempo real, integrado com ThingSpeak API.

## 🚀 Funcionalidades

- **Monitoramento em Tempo Real**: Visualização de dados de qualidade da água atualizados a cada 2 segundos
- **Integração com ThingSpeak**: Conexão com API do ThingSpeak para dados reais
- **Fallback para Dados Simulados**: Sistema funciona mesmo sem conexão com ThingSpeak
- **Métricas de Qualidade**: Monitoramento de turbidez, pH, temperatura e sólidos dissolvidos
- **Gráficos Interativos**: Visualizações com Plotly para análise histórica

## 📋 Requisitos

- Python 3.8+
- pip

## 🔧 Instalação

1. Clone o repositório:

```bash
git clone <url-do-repositorio>
cd v2
```

2. Crie e ative um ambiente virtual:

```bash
python3 -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

## ▶️ Como Executar

Execute o dashboard com:

```bash
streamlit run dashboard.py
```

O dashboard será aberto automaticamente no navegador em `http://localhost:8501`

## 📦 Dependências

- streamlit
- pandas
- numpy
- plotly
- requests

## 📊 Parâmetros Monitorados

- **Turbidez** (NTU)
- **pH**
- **Temperatura** (°C)
- **Sólidos Dissolvidos** (mg/L)
- **Nível do Reservatório** (%)
- **Vazão** (L/min)

## 🔗 Integração ThingSpeak

O projeto está configurado para se conectar ao ThingSpeak. As credenciais estão em `thingspeak_api.py`.

## 📝 Licença

Este projeto foi desenvolvido para fins acadêmicos.
