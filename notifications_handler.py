# -*- coding: utf-8 -*-
"""
Módulo para gerenciar notificações da AWS SQS
"""

import boto3
import json
import streamlit as st

class NotificationsHandler:
    """Classe para gerenciar notificações SQS"""
    
    def __init__(self, queue_url, aws_region):
        """
        Inicializa o handler de notificações.
        
        Args:
            queue_url: URL da fila SQS
            aws_region: Região AWS
        """
        self.queue_url = queue_url
        self.aws_region = aws_region
        self.sqs_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Inicializa o cliente SQS"""
        try:
            self.sqs_client = boto3.client('sqs', region_name=self.aws_region)
            return True
        except Exception as e:
            print(f"❌ Erro ao inicializar cliente SQS: {e}")
            return False
    
    def get_notification(self):
        """
        Busca uma mensagem da fila SQS.
        
        Returns:
            dict com os dados da notificação ou None
        """
        if not self.sqs_client:
            return None
        
        try:
            # Tenta receber 1 mensagem, usando Long Polling de 2 segundos
            response = self.sqs_client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=2  # Long polling
            )
            
            # Verifica se alguma mensagem foi recebida
            if 'Messages' in response:
                message = response['Messages'][0]
                receipt_handle = message['ReceiptHandle']
                
                # Processa a mensagem
                sqs_body_str = message['Body']
                sns_message_data = json.loads(sqs_body_str)
                
                # Extrai os dados
                subject = sns_message_data.get('Subject', 'Sem Assunto')
                notification_message = sns_message_data.get('Message', 'Sem Mensagem')
                timestamp = sns_message_data.get('Timestamp', '')
                
                # Deleta a mensagem da fila
                self.sqs_client.delete_message(
                    QueueUrl=self.queue_url,
                    ReceiptHandle=receipt_handle
                )
                
                return {
                    'subject': subject,
                    'message': notification_message,
                    'timestamp': timestamp
                }
                
        except Exception as e:
            print(f"❌ Erro ao processar SQS: {e}")
            return None
        
        return None
    
    def get_all_notifications(self, max_messages=10):
        """
        Busca todas as mensagens disponíveis na fila SQS.
        
        Args:
            max_messages: Número máximo de mensagens a buscar por vez (1-10)
            
        Returns:
            lista de dicts com os dados das notificações
        """
        if not self.sqs_client:
            return []
        
        all_notifications = []
        
        try:
            # Busca até 10 mensagens por vez (limite da AWS)
            max_per_batch = min(max_messages, 10)
            
            while True:
                response = self.sqs_client.receive_message(
                    QueueUrl=self.queue_url,
                    MaxNumberOfMessages=max_per_batch,
                    WaitTimeSeconds=2  # Long polling
                )
                
                if 'Messages' not in response:
                    # Não há mais mensagens
                    break
                
                messages = response['Messages']
                
                for message in messages:
                    try:
                        receipt_handle = message['ReceiptHandle']
                        
                        # Processa a mensagem
                        sqs_body_str = message['Body']
                        sns_message_data = json.loads(sqs_body_str)
                        
                        # Extrai os dados
                        subject = sns_message_data.get('Subject', 'Sem Assunto')
                        notification_message = sns_message_data.get('Message', 'Sem Mensagem')
                        timestamp = sns_message_data.get('Timestamp', '')
                        
                        all_notifications.append({
                            'subject': subject,
                            'message': notification_message,
                            'timestamp': timestamp
                        })
                        
                        # Deleta a mensagem da fila
                        self.sqs_client.delete_message(
                            QueueUrl=self.queue_url,
                            ReceiptHandle=receipt_handle
                        )
                    except Exception as e:
                        print(f"❌ Erro ao processar mensagem individual: {e}")
                        continue
                
                # Se recebeu menos mensagens que o solicitado, não há mais na fila
                if len(messages) < max_per_batch:
                    break
                    
        except Exception as e:
            print(f"❌ Erro ao buscar notificações: {e}")
        
        return all_notifications
    
    def format_notification(self, notification):
        """
        Formata uma notificação para exibição.
        
        Args:
            notification: dict com os dados da notificação
            
        Returns:
            string formatada
        """
        if not notification:
            return None
        
        return (f"**Assunto:** {notification['subject']}\n\n"
                f"**Mensagem:**\n```\n{notification['message']}\n```\n"
                f"*Recebido em: {notification['timestamp']}*")
    
    def parse_notification_params(self, notification):
        """
        Extrai os parâmetros da mensagem da notificação.
        
        Args:
            notification: dict com os dados da notificação
            
        Returns:
            dict com os parâmetros extraídos
        """
        import re
        from datetime import datetime
        
        params = {
            'Assunto': notification.get('subject', 'N/A'),
            'Turbidez (NTU)': 'N/A',
            'pH': 'N/A',
            'Temperatura (°C)': 'N/A',
            'TDS (mg/L)': 'N/A',
            'Data/Hora': 'N/A'
        }
        
        message = notification.get('message', '')
        
        # Extrair Turbidez
        turb_match = re.search(r'[Tt]urbitidy:\s*([\d.]+)', message)
        if turb_match:
            params['Turbidez (NTU)'] = float(turb_match.group(1))
        
        # Extrair pH
        ph_match = re.search(r'pH:\s*([\d.]+)', message)
        if ph_match:
            params['pH'] = float(ph_match.group(1))
        
        # Extrair Temperatura
        temp_match = re.search(r'[Tt]emperature:\s*([\d.]+)', message)
        if temp_match:
            params['Temperatura (°C)'] = float(temp_match.group(1))
        
        # Extrair TDS
        tds_match = re.search(r'TDS:\s*([\d.]+)', message)
        if tds_match:
            params['TDS (mg/L)'] = float(tds_match.group(1))
        
        # Formatar timestamp
        timestamp_str = notification.get('timestamp', '')
        if timestamp_str:
            try:
                # Parse ISO format: 2025-12-08T23:56:59.227Z
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                params['Data/Hora'] = dt.strftime('%d/%m/%Y %H:%M:%S')
            except:
                params['Data/Hora'] = timestamp_str
        
        return params

