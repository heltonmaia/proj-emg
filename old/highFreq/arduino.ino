// Arduino code - high_frequency_generator.ino
#include <TimerOne.h>

const int OUTPUT_PIN = 8;
const int MAX_BUFFER = 64;
char serialBuffer[MAX_BUFFER];
volatile int bufferIndex = 0;

// Configuração da frequência
const long FREQUENCY = 1000; // Hz - ajustável até ~16kHz
const long PERIOD_MICROS = 1000000L / FREQUENCY;

void setup() {
  pinMode(OUTPUT_PIN, OUTPUT);
  Serial.begin(115200); // Aumentado para 115200 baud
  
  // Configura Timer1
  Timer1.initialize(PERIOD_MICROS / 2);
  Timer1.attachInterrupt(togglePin);
}

void togglePin() {
  static boolean state = false;
  state = !state;
  digitalWrite(OUTPUT_PIN, state);
  
  // Buffer the output instead of sending immediately
  serialBuffer[bufferIndex++] = (state ? '1' : '0');
  serialBuffer[bufferIndex++] = '\n';
  
  // When buffer is full, send it
  if (bufferIndex >= MAX_BUFFER) {
    Serial.write(serialBuffer, bufferIndex);
    bufferIndex = 0;
  }
}

void loop() {
  // Loop principal vazio - todo trabalho é feito pela interrupt
}
