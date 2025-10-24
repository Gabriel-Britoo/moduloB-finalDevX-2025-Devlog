import argparse
import os
import serial
from serial.tools import list_ports
import json
import csv
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import pandas as pd
import logging
import time

# Configuração de logging
logging.basicConfig(
    filename='anomalias.log',
    level=logging.WARNING,
    format='%(asctime)s - %(message)s'
)

class AnaliseSensores:
    def __init__(self, porta=None, baudrate=9600, tentar_auto_detect=True):
        self.porta_serial = None
        portas_detectadas = [p.device for p in list_ports.comports()]
        
        print(f"Portas seriais detectadas: {portas_detectadas}")
        
        # Tenta conectar na porta especificada
        if porta:
            try:
                self.porta_serial = serial.Serial(porta, baudrate, timeout=1)
                print(f"Conectado à porta {porta}")
            except Exception as e:
                print(f"Erro na porta {porta}: {e}")
                if not tentar_auto_detect:
                    raise SystemExit(f"Não foi possível abrir a porta {porta}")
        
        # Auto-detect se necessário
        if not self.porta_serial and tentar_auto_detect:
            for p in portas_detectadas:
                try:
                    self.porta_serial = serial.Serial(p, baudrate, timeout=1)
                    print(f"Conectado automaticamente à porta {p}")
                    break
                except Exception as e:
                    print(f"Falha na porta {p}: {e}")
                    continue
        
        if not self.porta_serial:
            raise SystemExit("Não foi possível abrir nenhuma porta serial")
        
        # SEMPRE cria o arquivo CSV
        self.criar_tabela()
        
        # Dados para visualização
        self.dados = {
            'Node1': {'temp': [], 'umid': [], 'tempo': []},
            'Node2': {'temp': [], 'umid': [], 'tempo': []},
            'Node3': {'temp': [], 'umid': [], 'tempo': []}
        }
        
        # Limites
        self.TEMP_MAX = 30
        self.UMID_MAX = 70
        self.UMID_MIN = 40
        
        # Configuração do gráfico
        self.fig, self.axs = plt.subplots(2, 1, figsize=(12, 8))
        self.fig.suptitle('Monitoramento de Sensores em Tempo Real')
        
        # Inicializa as linhas do gráfico
        self.linhas_temp = {}
        self.linhas_umid = {}
        cores = ['red', 'blue', 'green']
        
        for i, node in enumerate(['Node1', 'Node2', 'Node3']):
            self.linhas_temp[node], = self.axs[0].plot([], [], 
                                                     label=f'{node} - Temperatura', 
                                                     color=cores[i], 
                                                     marker='o', 
                                                     linewidth=2)
            self.linhas_umid[node], = self.axs[1].plot([], [], 
                                                      label=f'{node} - Umidade', 
                                                      color=cores[i], 
                                                      marker='s', 
                                                      linewidth=2)
        
        # Configura os eixos
        self.axs[0].set_ylabel('Temperatura (°C)')
        self.axs[0].set_title('Temperatura por Nó')
        self.axs[0].legend()
        self.axs[0].grid(True, alpha=0.3)
        
        self.axs[1].set_ylabel('Umidade (%)')
        self.axs[1].set_xlabel('Tempo')
        self.axs[1].set_title('Umidade por Nó')
        self.axs[1].legend()
        self.axs[1].grid(True, alpha=0.3)
        
        plt.tight_layout()

    def criar_tabela(self):
        csv_file = 'dados_sensores.csv'
        header = ['timestamp', 'node_id', 'temperatura', 'umidade']
        if not os.path.exists(csv_file):
            try:
                with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(header)
                print(f"Arquivo {csv_file} criado com sucesso")
            except Exception as e:
                print(f"Erro ao criar CSV: {e}")

    def ler_dados_serial(self):
        try:
            if self.porta_serial.in_waiting > 0:
                linha = self.porta_serial.readline().decode('utf-8', errors='ignore').strip()
                print(f"Raw data: {linha}")  # DEBUG
                
                if not linha:
                    return None
                
                # Tenta extrair JSON
                start = linha.find('{')
                end = linha.rfind('}')
                if start != -1 and end != -1:
                    json_str = linha[start:end+1]
                    try:
                        dados_raw = json.loads(json_str)
                        print(f"JSON parseado: {dados_raw}")  # DEBUG
                    except json.JSONDecodeError as e:
                        print(f"Erro JSON: {e}")
                        return None
                else:
                    return None

                # Processa dados
                node = dados_raw.get('n') or dados_raw.get('node')
                temp = dados_raw.get('t') or dados_raw.get('temperatura')
                umi = dados_raw.get('u') or dados_raw.get('umidade')

                if node is None or temp is None or umi is None:
                    print("Dados incompletos no JSON")
                    return None

                return {
                    'node': node, 
                    'temperatura': float(temp), 
                    'umidade': float(umi)
                }
        except Exception as e:
            print(f"Erro na leitura serial: {e}")
            return None
        return None

    def salvar_dados(self, dados):
        timestamp = datetime.now().strftime('%H:%M:%S')  # Formato mais curto para gráfico
        node = dados['node']
        
        # Atualiza dados em tempo real (mantém apenas últimos 50 pontos)
        self.dados[node]['temp'].append(dados['temperatura'])
        self.dados[node]['umid'].append(dados['umidade'])
        self.dados[node]['tempo'].append(timestamp)
        
        # Limita o número de pontos no gráfico para melhor performance
        max_pontos = 50
        for node in self.dados:
            for key in ['temp', 'umid', 'tempo']:
                if len(self.dados[node][key]) > max_pontos:
                    self.dados[node][key] = self.dados[node][key][-max_pontos:]
        
        # Salva em CSV
        csv_file = 'dados_sensores.csv'
        timestamp_completo = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp_completo, node, dados['temperatura'], dados['umidade']])
        except Exception as e:
            print(f"Erro ao salvar CSV: {e}")

    def verificar_anomalias(self, dados):
        if dados['temperatura'] > self.TEMP_MAX:
            msg = f"Temperatura alta no {dados['node']}: {dados['temperatura']}°C"
            print(f"ALERTA: {msg}")
            logging.warning(msg)
            self.enviar_comando(dados['node'], 'ALARME_ON')
        
        if dados['umidade'] > self.UMID_MAX or dados['umidade'] < self.UMID_MIN:
            msg = f"Umidade anormal no {dados['node']}: {dados['umidade']}%"
            print(f"ALERTA: {msg}")
            logging.warning(msg)

    def atualizar_grafico(self, frame):
        try:
            # Atualiza os dados de cada linha
            for node in ['Node1', 'Node2', 'Node3']:
                if self.dados[node]['tempo'] and self.dados[node]['temp']:
                    # Atualiza dados de temperatura
                    self.linhas_temp[node].set_data(
                        range(len(self.dados[node]['tempo'])), 
                        self.dados[node]['temp']
                    )
                    
                    # Atualiza dados de umidade
                    self.linhas_umid[node].set_data(
                        range(len(self.dados[node]['tempo'])), 
                        self.dados[node]['umid']
                    )
            
            # Ajusta os limites dos eixos
            for ax in self.axs:
                ax.relim()
                ax.autoscale_view()
            
            # Atualiza os labels do eixo X com os tempos reais
            if self.dados['Node1']['tempo']:
                n_points = len(self.dados['Node1']['tempo'])
                step = max(1, n_points // 10)  # Mostra ~10 labels
                indices = list(range(0, n_points, step))
                tempos = [self.dados['Node1']['tempo'][i] for i in indices if i < n_points]
                
                self.axs[1].set_xticks(indices[:len(tempos)])
                self.axs[1].set_xticklabels(tempos, rotation=45)
            
            self.fig.tight_layout()
            
        except Exception as e:
            print(f"Erro ao atualizar gráfico: {e}")

    def enviar_comando(self, node, comando):
        try:
            payload = comando + '\n'
            self.porta_serial.write(payload.encode())
            print(f"Comando enviado: {comando}")
        except Exception as e:
            print(f"Erro ao enviar comando: {e}")

    def executar(self):
        print("Iniciando coleta de dados...")
        print("Pressione Ctrl+C para parar")
        
        # Inicia a animação do gráfico
        ani = FuncAnimation(self.fig, self.atualizar_grafico, interval=1000, cache_frame_data=False)
        
        try:
            contador = 0
            while True:
                dados = self.ler_dados_serial()
                if dados:
                    print(f"Dados recebidos: {dados}")
                    self.salvar_dados(dados)
                    self.verificar_anomalias(dados)
                    contador += 1
                
                # Pequena pausa para não sobrecarregar
                plt.pause(0.1)
                
        except KeyboardInterrupt:
            print("\nParando coleta de dados...")
            if self.porta_serial:
                self.porta_serial.close()
            plt.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Sistema de monitoramento de sensores')
    parser.add_argument('--port', '-p', help='Porta serial (ex: COM3, /dev/ttyUSB0)', default=None)
    args = parser.parse_args()

    try:
        analise = AnaliseSensores(porta=args.port)
        analise.executar()
    except Exception as e:
        print(f"Erro fatal: {e}")