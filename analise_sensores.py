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
try:
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False
import seaborn as sns

# Configuração de logging
logging.basicConfig(
    filename='anomalias.log',
    level=logging.WARNING,
    format='%(asctime)s - %(message)s'
)

class AnaliseSensores:
    def __init__(self, porta=None, baudrate=9600, tentar_auto_detect=True):
        # Configuração da porta serial
        self.porta_serial = None
        portas_detectadas = [p.device for p in list_ports.comports()]

        # Se porta foi fornecida, tenta abri-la; caso contrário, tenta auto-detect
        if porta:
            try:
                self.porta_serial = serial.Serial(porta, baudrate, timeout=1)
            except Exception as e:
                if not tentar_auto_detect:
                    msg = (
                        f"Erro ao abrir porta serial '{porta}': {e}\n"
                        f"Portas detectadas: {portas_detectadas}\n"
                    )
                    raise SystemExit(msg)
        if not self.porta_serial and tentar_auto_detect:
            # tenta abrir cada porta detectada até encontrar uma que funcione
            for p in portas_detectadas:
                try:
                    self.porta_serial = serial.Serial(p, baudrate, timeout=1)
                    print(f"Conectado automaticamente à porta {p}")
                    break
                except Exception:
                    self.porta_serial = None
            if not self.porta_serial:
                    msg = (
                        f"Não foi possível abrir nenhuma porta serial. Portas detectadas: {portas_detectadas}\n"
                        "Possíveis causas: porta errada, Monitor Serial do Arduino aberto, ausência de permissões.\n"
                        "Feche outras aplicações que possam estar usando a porta e tente novamente."
                    )
                    raise SystemExit(msg)

            # Garante existência do arquivo CSV de dados
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
        # Garante que o arquivo CSV exista com o cabeçalho correto
        csv_file = 'dados_sensores.csv'
        header = ['timestamp', 'node_id', 'temperatura', 'umidade']
        if not os.path.exists(csv_file):
            try:
                with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(header)
            except Exception as e:
                raise SystemExit(f"Não foi possível criar o arquivo CSV '{csv_file}': {e}")

    def ler_dados_serial(self):
        try:
            if self.porta_serial.in_waiting:
                linha = self.porta_serial.readline().decode(errors='ignore').strip()
                if not linha:
                    return None
                try:
                    dados_raw = json.loads(linha)
                except json.JSONDecodeError:
                    # tenta extrair JSON em meio a texto (ex.: "Dados enviados: {...}")
                    start = linha.find('{')
                    end = linha.rfind('}')
                    if start != -1 and end != -1 and end > start:
                        try:
                            dados_raw = json.loads(linha[start:end+1])
                        except json.JSONDecodeError:
                            return None
                    else:
                        return None

                # aceita tanto chaves curtas (n/t/u) quanto longas (node/temperatura/umidade)
                node = dados_raw.get('n') or dados_raw.get('node')
                temp = dados_raw.get('t') or dados_raw.get('temperatura')
                umi = dados_raw.get('u') or dados_raw.get('umidade')

                if node is None or temp is None or umi is None:
                    return None

                dados = {'node': node, 'temperatura': float(temp), 'umidade': float(umi)}
                return dados
        except Exception as e:
            # Não deixa o programa morrer por um erro temporário de leitura
            print(f"Aviso: erro ao ler serial: {e}")
            return None

    def salvar_dados(self, dados):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Persistência: CSV (dados_sensores.csv) - a linha abaixo adiciona o registro
        # Atualiza dados para visualização
        node = dados['node']
        self.dados[node]['temp'].append(dados['temperatura'])
        self.dados[node]['umid'].append(dados['umidade'])
        self.dados[node]['tempo'].append(timestamp)
        
        # Também salva em CSV (dados_sensores.csv)
        csv_file = 'dados_sensores.csv'
        header = ['timestamp', 'node_id', 'temperatura', 'umidade']
        write_header = not os.path.exists(csv_file)
        try:
            with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if write_header:
                    writer.writerow(header)
                writer.writerow([timestamp, dados['node'], dados['temperatura'], dados['umidade']])
        except Exception as e:
            print(f"Aviso: não foi possível escrever CSV: {e}")

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
        csv_file = 'dados_sensores.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
        else:
            df = pd.DataFrame(columns=['timestamp', 'node_id', 'temperatura', 'umidade'])
        
        relatorio = "=== RELATÓRIO DE DESEMPENHO ===\n\n"
        
        for node in ['Node1', 'Node2', 'Node3']:
            node_data = df[df['node_id'] == node]
            relatorio += f"\nNó: {node}\n"
            relatorio += f"Temperatura Média: {node_data['temperatura'].mean():.2f}°C\n"
            relatorio += f"Temperatura Máxima: {node_data['temperatura'].max():.2f}°C\n"
            relatorio += f"Temperatura Mínima: {node_data['temperatura'].min():.2f}°C\n"
            relatorio += f"Umidade Média: {node_data['umidade'].mean():.2f}%\n"
        
        # salva em TXT
        with open('relatorio.txt', 'w', encoding='utf-8') as f:
            f.write(relatorio)

        # se reportlab estiver disponível, gera PDF simples
        if REPORTLAB_AVAILABLE:
            try:
                c = canvas.Canvas('relatorio.pdf')
                text = c.beginText(40, 800)
                for line in relatorio.split('\n'):
                    text.textLine(line)
                c.drawText(text)
                c.save()
            except Exception as e:
                print(f"Aviso: falha ao gerar PDF: {e}")

    def enviar_comando(self, node, comando):
        # Envia um comando simples pela serial para a estação receptora (se suportado)
        try:
            # alguns firmwares podem esperar apenas a string do comando
            payload = comando if isinstance(comando, str) else json.dumps(comando)
            self.porta_serial.write((payload + '\n').encode())
        except Exception as e:
            print(f"Aviso: falha ao enviar comando pela serial: {e}")

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
            if self.porta_serial:
                try:
                    self.porta_serial.close()
                except Exception:
                    pass
            plt.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Coleta e análise de sensores via serial')
    parser.add_argument('--port', '-p', help='Porta serial (ex: COM7, COM10). Se omitido, tenta auto-detectar.', default=None)
    args = parser.parse_args()

    analise = AnaliseSensores(porta=args.port)
    analise.executar()
