import serial
import json
import csv
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import pandas as pd
import logging
from reportlab.pdfgen import canvas
import seaborn as sns

# Configuração de logging
logging.basicConfig(
    filename='anomalias.log',
    level=logging.WARNING,
    format='%(asctime)s - %(message)s'
)

class AnaliseSensores:
    def __init__(self):
        # Configuração da porta serial
        self.porta_serial = serial.Serial('COM10', 9600)
        
        # Configuração do banco de dados
        self.conn = sqlite3.connect('dados_sensores.db')
        self.criar_tabela()
        
        # Dados para visualização em tempo real
        self.dados = {
            'Node1': {'temp': [], 'umid': [], 'tempo': []},
            'Node2': {'temp': [], 'umid': [], 'tempo': []},
            'Node3': {'temp': [], 'umid': [], 'tempo': []}
        }
        
        # Limites de operação
        self.TEMP_MAX = 30
        self.UMID_MAX = 70
        self.UMID_MIN = 40

    def criar_tabela(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leituras (
                timestamp TEXT,
                node_id TEXT,
                temperatura REAL,
                umidade REAL
            )
        ''')
        self.conn.commit()

    def ler_dados_serial(self):
        if self.porta_serial.in_waiting:
            linha = self.porta_serial.readline().decode().strip()
            try:
                dados = json.loads(linha)
                return dados
            except json.JSONDecodeError:
                return None

    def salvar_dados(self, dados):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = self.conn.cursor()
        
        cursor.execute(
            'INSERT INTO leituras VALUES (?, ?, ?, ?)',
            (timestamp, dados['node'], dados['temperatura'], dados['umidade'])
        )
        self.conn.commit()
        
        # Atualiza dados para visualização
        node = dados['node']
        self.dados[node]['temp'].append(dados['temperatura'])
        self.dados[node]['umid'].append(dados['umidade'])
        self.dados[node]['tempo'].append(timestamp)

    def verificar_anomalias(self, dados):
        if dados['temperatura'] > self.TEMP_MAX:
            logging.warning(
                f"Temperatura alta no {dados['node']}: {dados['temperatura']}°C"
            )
            self.enviar_comando(dados['node'], 'ALARME_ON')
            self.enviar_comando(dados['node'], 'DESLIGAR_MOTOR')
        
        if dados['umidade'] > self.UMID_MAX or dados['umidade'] < self.UMID_MIN:
            logging.warning(
                f"Umidade anormal no {dados['node']}: {dados['umidade']}%"
            )

    def atualizar_grafico(self, frame):
        plt.clf()
        for node in self.dados:
            plt.subplot(2, 1, 1)
            plt.plot(self.dados[node]['tempo'][-50:], 
                    self.dados[node]['temp'][-50:], 
                    label=f"{node} Temp")
            plt.title('Temperatura por Nó')
            plt.legend()
            
            plt.subplot(2, 1, 2)
            plt.plot(self.dados[node]['tempo'][-50:], 
                    self.dados[node]['umid'][-50:], 
                    label=f"{node} Umid")
            plt.title('Umidade por Nó')
            plt.legend()
        
        plt.tight_layout()

    def gerar_relatorio(self):
        df = pd.read_sql_query("SELECT * FROM leituras", self.conn)
        
        relatorio = "=== RELATÓRIO DE DESEMPENHO ===\n\n"
        
        for node in ['Node1', 'Node2', 'Node3']:
            node_data = df[df['node_id'] == node]
            relatorio += f"\nNó: {node}\n"
            relatorio += f"Temperatura Média: {node_data['temperatura'].mean():.2f}°C\n"
            relatorio += f"Temperatura Máxima: {node_data['temperatura'].max():.2f}°C\n"
            relatorio += f"Temperatura Mínima: {node_data['temperatura'].min():.2f}°C\n"
            relatorio += f"Umidade Média: {node_data['umidade'].mean():.2f}%\n"
        
        with open('relatorio.txt', 'w') as f:
            f.write(relatorio)

    def enviar_comando(self, node, comando):
        comando_json = json.dumps({'node': node, 'comando': comando})
        self.porta_serial.write(comando_json.encode())

    def executar(self):
        # Configuração da animação do gráfico
        fig = plt.figure(figsize=(10, 8))
        ani = FuncAnimation(fig, self.atualizar_grafico, interval=1000)
        plt.show(block=False)

        try:
            while True:
                dados = self.ler_dados_serial()
                if dados:
                    self.salvar_dados(dados)
                    self.verificar_anomalias(dados)
                    
                    # Gera relatório a cada 100 leituras
                    if len(self.dados['Node1']['temp']) % 100 == 0:
                        self.gerar_relatorio()

        except KeyboardInterrupt:
            self.porta_serial.close()
            self.conn.close()
            plt.close()

if __name__ == "__main__":
    analise = AnaliseSensores()
    analise.executar()
