import streamlit as st
import boto3
import json
import time

# --- Configuração ---
SQS_QUEUE_URL = st.secrets["SQS_QUEUE_URL"]
AWS_REGION = st.secrets["AWS_REGION"]


def get_notification_from_sqs():
    """Busca (polled) uma mensagem da fila SQS."""
    try:
        # Tenta receber 1 mensagem, usando Long Polling de 5 segundos
        response = sqs_client.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5  # Long polling: eficiente, não gasta CPU
        )


        # Verifica se alguma mensagem foi recebida
        if 'Messages' in response:
            message = response['Messages'][0]
            receipt_handle = message['ReceiptHandle']
            
            # --- Processamento da Mensagem ---
            # 1. O corpo (Body) da mensagem SQS é uma string JSON
            sqs_body_str = message['Body']
            
            # 2. Convertemos essa string para um dicionário Python
            sns_message_data = json.loads(sqs_body_str)
            
            # 3. Extraímos o Subject e a Message reais (que vieram do SNS)
            subject = sns_message_data.get('Subject', 'Sem Assunto')
            notification_message = sns_message_data.get('Message', 'Sem Mensagem')
            timestamp = sns_message_data.get('Timestamp', '')

            # 4. DELETAMOS a mensagem da fila.
            sqs_client.delete_message(
                QueueUrl=SQS_QUEUE_URL,
                ReceiptHandle=receipt_handle
            )
            return f"**Assunto:** {subject}\n\n**Mensagem:**\n```\n{notification_message}\n```\n*Recebido em: {timestamp}*"
            
    except Exception as e:
        print(f"Erro ao processar SQS: {e}")
        return None
    
    return None

# Inicializa o cliente SQS
try:
    sqs_client = boto3.client('sqs', region_name=AWS_REGION)
except Exception as e:
    st.error(f"Erro ao inicializar o cliente Boto3: {e}")
    st.stop()

get_notification_from_sqs()

# --- Interface do Streamlit ---

st.set_page_config(layout="wide")
st.title("🌊 Dashboard de Alertas da Qualidade da Água (TCC)")
st.caption("Aguardando novas notificações do AWS SNS...")

# Usamos st.session_state para guardar a lista de alertas entre as execuções
if 'notifications' not in st.session_state:
    st.session_state.notifications = []

# Este placeholder é o "container" que vamos atualizar
placeholder = st.empty()

# Loop "infinito" para polling
while True:
    # 1. Verifica se há uma nova mensagem
    new_message = get_notification_from_sqs()
    
    # 2. Se houver, atualiza o estado
    if new_message:
        # Adiciona a mensagem mais nova no topo da lista
        st.session_state.notifications.insert(0, new_message)
        
        # Mostra uma "notificação pop-up" (toast) no canto da tela
        st.toast("🚨 NOVO ALERTA RECEBIDO!", icon="🌊")

    # 3. Redesenha a interface dentro do placeholder
    with placeholder.container():
        st.header("Histórico de Alertas")
        
        if not st.session_state.notifications:
            st.info("Nenhum alerta recebido até o momento.")
        
        # Cria colunas para os alertas
        cols = st.columns(3)
        for i, msg in enumerate(st.session_state.notifications):
            # Distribui os alertas nas colunas (0, 1, 2, 0, 1, 2, ...)
            col = cols[i % 3] 
            col.warning(f"**Alerta #{len(st.session_state.notifications) - i}**\n\n{msg}")

    # 4. Espera 2 segundos antes de verificar a fila novamente
    time.sleep(2)
