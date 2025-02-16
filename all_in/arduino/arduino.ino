

/*
//Programa teste para envio de uma square wave

const int pin = 9;   // Pino de saída da onda quadrada
const int led = 13;  // LED embutido da placa
int freq = 100;        // Frequência da onda em Hz

void setup() {
    pinMode(pin, OUTPUT);
    pinMode(led, OUTPUT);
}

void loop() {
    int periodo = 1000 / freq; // Calcula o período em milissegundos (1/freq)

    digitalWrite(pin, HIGH);
    digitalWrite(led, HIGH);
    delay(periodo / 2); // Metade do período (nível alto)

    digitalWrite(pin, LOW);
    digitalWrite(led, LOW);
    delay(periodo / 2); // Metade do período (nível baixo)
}
*/