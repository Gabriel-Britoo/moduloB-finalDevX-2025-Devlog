🌡️ Sistema de Monitoramento IoT com Arduino, nRF24L01 e Python

Este projeto implementa um sistema de monitoramento sem fio que coleta dados de temperatura e umidade de múltiplos nós sensores e os envia a um receptor central, que por sua vez se comunica com um script Python responsável por registrar, analisar e visualizar os dados coletados.

🧩 Estrutura do Projeto
Componente	Função
Node Sensor (Arduino + DHT11 + nRF24L01 + Servo + LEDs + Buzzer)	Mede temperatura e umidade e envia via rádio para o receptor.
Receptor (Arduino + nRF24L01)	Recebe os dados dos sensores, analisa as leituras e envia comandos de resposta (“ALERTA” ou “ESTÁVEL”).
Script Python (analise_sensores.py)	Coleta dados via porta serial, registra em CSV, detecta anomalias, gera logs e gráficos em tempo real.
🧠 Como o Sistema Funciona

O Node Sensor coleta dados de temperatura e umidade a cada 5 segundos com o sensor DHT11.

Esses dados são enviados via módulo nRF24L01 para o Arduino Receptor.

O Receptor interpreta os dados (JSON) e decide:

Enviar “ALERTA” se a temperatura for ≥ 30 °C;

Enviar “ESTÁVEL” se estiver dentro do normal.

O Node Sensor reage ao comando:

🔴 “ALERTA” → Liga LED vermelho, buzzer e para o servo;

🟢 “ESTÁVEL” → Liga LED verde, desliga buzzer e servo volta a se mover.

O script Python lê os dados enviados via porta serial pelo Receptor, salva em dados_sensores.csv, registra alertas no log e exibe gráficos periódicos de temperatura e umidade.

⚙️ Materiais Necessários
🛰️ Node Sensor

1x Arduino UNO (ou Nano)

1x Módulo nRF24L01

1x Sensor DHT11

1x Servo motor

1x LED vermelho + resistor

1x LED verde + resistor

1x Buzzer

Jumpers e protoboard

📡 Receptor

1x Arduino UNO (ou Nano)

1x Módulo nRF24L01

Cabo USB para conexão com o computador

🔌 Conexões Principais
nRF24L01 ↔ Arduino
NRF24L01	Arduino UNO
VCC	3.3V
GND	GND
CE	8
CSN	10
SCK	13
MOSI	11
MISO	12
DHT11

VCC → 5V

GND → GND

DATA → Pino 2

Servo

Sinal → Pino 3

VCC → 5V

GND → GND

LEDs e Buzzer

LED vermelho → Pino 4

LED verde → Pino 5

Buzzer → Pino 6

🧩 Códigos

node_sensor.ino → Código do nó sensor (coleta dados e reage aos comandos)

receptor.ino → Código do receptor (interpreta dados e envia respostas)

analise_sensores.py → Script Python de monitoramento e análise

💻 Instruções de Uso
1️⃣ Configurar os Arduinos

Faça upload do código node_sensor.ino no Arduino do sensor.

Faça upload do código receptor.ino no Arduino conectado ao computador.

Verifique se ambos os módulos nRF24L01 estão corretamente alimentados e conectados.

2️⃣ Executar o Script Python

Instale as dependências:

pip install pyserial matplotlib pandas


Conecte o Arduino receptor ao PC.

Descubra a porta serial (ex: COM7 no Windows ou /dev/ttyUSB0 no Linux).

Execute o script:

python analise_sensores.py --port COM7


(Substitua COM7 pela porta correta)

O programa exibirá as leituras no terminal e salvará:

dados_sensores.csv → dados de temperatura e umidade

anomalias.log → registros de alertas

gráficos gerados periodicamente (a cada 10 leituras)

📊 Resultados Esperados

O terminal mostrará as leituras em tempo real.

Um gráfico com as últimas leituras será exibido automaticamente.

Caso a temperatura ultrapasse 30 °C, o sistema aciona alerta visual e sonoro no Node Sensor.

Todos os dados ficam salvos localmente para análise posterior.

🧾 Arquivos Gerados
Arquivo	Descrição
dados_sensores.csv	Armazena todas as leituras (timestamp, node, temperatura, umidade)
anomalias.log	Registra alertas de temperatura/umidade fora do limite
analise_sensores.py	Script de monitoramento e visualização
⚠️ Observações

Certifique-se de alimentar o nRF24L01 com 3.3 V estáveis.

O DHT11 pode ter uma variação de até ±2 °C.

Para mais de um Node Sensor, altere o campo "n" no JSON (ex: "Node2", "Node3").

O gráfico do Python mostra até 20 leituras recentes por nó.
