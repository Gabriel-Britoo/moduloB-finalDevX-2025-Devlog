#include <DHT.h>
#include <SPI.h>
#include <nRF24L01.h>
#include <RF24.h>
#include <Servo.h>
#include <ArduinoJson.h>

// Configuração do módulo NRF24L01
RF24 radio(8, 10); // CE no pino 8, CSN no pino 10
const byte endereco[6] = "00007"; // Endereço para comunicação

char comandoRecebido[32]; // Buffer para armazenar comandos recebidos

// Definição dos pinos
#define ledR 4     // LED vermelho no pino 4
#define ledG 5     // LED verde no pino 5
#define buzzer 6   // Buzzer no pino 6
#define DHTPIN 2   // Sensor DHT11 no pino 2
#define DHTTYPE DHT11 // Tipo do sensor

DHT dht(DHTPIN, DHTTYPE); // Objeto do sensor DHT

Servo servoMotor; // Objeto do servo motor
int angulo = 0; // Ângulo atual do servo
int direcao = 1; // Direção do movimento (1 = aumenta, -1 = diminui)
unsigned long ultimoMovimento = 0; // Último tempo de movimento
const unsigned long intervaloMovimento = 20; // Intervalo entre movimentos (ms)

void setup() {
  // Configuração dos pinos como saída
  pinMode(ledR, OUTPUT);
  pinMode(ledG, OUTPUT);
  pinMode(buzzer, OUTPUT);
  
  servoMotor.attach(3); // Servo no pino 3

  dht.begin(); // Inicializa sensor DHT

  // Configuração do rádio
  radio.begin();
  radio.openWritingPipe(endereco); // Pipe para enviar dados
  radio.openReadingPipe(1, endereco); // Pipe para receber dados
  radio.setPALevel(RF24_PA_LOW); // Potência baixa do transmissor
  radio.startListening(); // Inicia no modo receptor

  Serial.begin(9600); // Inicializa comunicação serial
  
  servoMotor.write(angulo); // Posição inicial do servo
}

void loop() {
  // Leitura dos sensores
  float umi = dht.readHumidity();
  float temp = dht.readTemperature();

  // Verifica se a leitura do sensor foi bem sucedida
  if (isnan(umi) || isnan(temp)) {
    Serial.println("Falha ao ler o sensor de temperatura e umidade.");
    delay(2000);
    return;
  }

  movimentoServoContinuo(); // Controla o movimento contínuo do servo

  // Envia dados a cada 5 segundos
  static unsigned long ultimoEnvio = 0;
  if (millis() - ultimoEnvio >= 5000) {
    ultimoEnvio = millis();
    
    // Cria JSON com os dados do sensor
    StaticJsonDocument<200> doc;
    doc["n"] = "Node1"; // Nome do nó
    doc["t"] = temp;    // Temperatura
    doc["u"] = umi;     // Umidade
    char buffer[128];
    serializeJson(doc, buffer); // Converte JSON para string

    // Envia dados via rádio
    radio.stopListening();
    if (radio.write(buffer, strlen(buffer) + 1)) {
      Serial.print("Dados enviados: ");
      Serial.println(buffer);
    } else {
      Serial.println("Falha no envio.");
    }

    // Aguarda resposta do receptor por 1 segundo
    radio.startListening();
    unsigned long inicioEspera = millis();
    
    while (millis() - inicioEspera < 1000) {
      if (radio.available()) {
        memset(comandoRecebido, 0, sizeof(comandoRecebido));
        radio.read(comandoRecebido, sizeof(comandoRecebido));
        
        Serial.print("Comando recebido: ");
        Serial.println(comandoRecebido);

        // Executa ações baseadas no comando recebido
        if (strcmp(comandoRecebido, "ALERTA") == 0) {
          // Modo de alerta - temperatura alta
          servoMotor.detach(); // Para o servo
          tone(buzzer, 900);   // Ativa buzzer
          digitalWrite(ledG, LOW);  // Apaga LED verde
          digitalWrite(ledR, HIGH); // Acende LED vermelho
        } else if (strcmp(comandoRecebido, "ESTAVEL") == 0) {
          // Modo estável - temperatura normal
          servoMotor.attach(3); // Reativa o servo
          noTone(buzzer);       // Desliga buzzer
          digitalWrite(ledG, HIGH); // Acende LED verde
          digitalWrite(ledR, LOW);  // Apaga LED vermelho
        }
        break; // Sai do loop após receber comando
      }
    }
  }
}

// Função para movimento contínuo e suave do servo
void movimentoServoContinuo() {
  if (millis() - ultimoMovimento >= intervaloMovimento) {
    ultimoMovimento = millis();
    
    angulo += 3 * direcao; // Move 3 graus por vez (ajuste de velocidade)
    
    // Inverte direção nos limites
    if (angulo >= 180) {
      direcao = -1; // Muda para movimento decrescente
      angulo = 180; // Garante que não ultrapasse o limite
    } else if (angulo <= 0) {
      direcao = 1;  // Muda para movimento crescente
      angulo = 0;   // Garante que não ultrapasse o limite
    }
    
    servoMotor.write(angulo); // Envia novo ângulo para o servo
  }
}