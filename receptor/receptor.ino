#include <SPI.h>
#include <nRF24L01.h>
#include <RF24.h>
#include <ArduinoJson.h>

// Configuração do módulo NRF24L01
RF24 radio(8, 10); // CE no pino 8, CSN no pino 10
const byte endereco[6] = "00007"; // Endereço para comunicação

void setup() {
  Serial.begin(9600);
  
  // Inicialização do rádio
  radio.begin();
  radio.openReadingPipe(0, endereco); // Pipe para receber dados
  radio.openWritingPipe(endereco);    // Pipe para enviar dados
  radio.setPALevel(RF24_PA_LOW);      // Potência do transmissor (baixa)
  radio.startListening();             // Inicia no modo receptor
}

void loop() {
  // Verifica se existem dados disponíveis para leitura
  if (radio.available()) {
    char dadosRecebidos[128] = {0}; // Buffer para armazenar dados recebidos
    
    // Lê os dados recebidos
    radio.read(dadosRecebidos, sizeof(dadosRecebidos));

    // Processa o JSON recebido
    StaticJsonDocument<200> doc;
    DeserializationError erro = deserializeJson(doc, dadosRecebidos);

    // Se o JSON foi interpretado com sucesso
    if (!erro) {
      // Extrai os valores do JSON
      const char* node = doc["n"]; // Nome do nó
      float temp = doc["t"];       // Temperatura
      float umi = doc["u"];        // Umidade

      // Exibe os dados no monitor serial
      Serial.print("Node: ");
      Serial.print(node);
      Serial.print(" | Temp: ");
      Serial.print(temp);
      Serial.println(" °C");
      Serial.print(" | Umidade: ");
      Serial.print(umi);
      Serial.println(" %");

      char comando[32]; // Buffer para o comando

      // Lógica de decisão baseada na temperatura
      if (temp >= 30) {
        strcpy(comando, "ALERTA"); // Temperatura alta
        enviaComando(comando);
      } else {
        strcpy(comando, "ESTAVEL"); // Temperatura normal
        enviaComando(comando);
      }

    } else {
      Serial.println("Interpretação do JSON falhou.");
    }
  }
}

// Função para enviar comandos de volta para o transmissor
void enviaComando(char* cmd) {
  radio.stopListening(); // Muda para modo transmissor
  
  // Tenta enviar o comando
  if (radio.write(cmd, strlen(cmd) + 1)) {
    Serial.print("Comando enviado: ");
    Serial.println(cmd);
  } else {
    Serial.print("Falha ao enviar comando: ");
    Serial.println(cmd);
  }
  
  radio.startListening(); // Volta para modo receptor
}