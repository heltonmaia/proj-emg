Com estas otimizações, as frequências máximas confiáveis seriam aproximadamente:

1. Versão Original:
- Frequência máxima confiável: ~200 Hz
- Limitada principalmente pelo Serial.println() e baudrate de 9600

2. Versão Otimizada:
- Arduino: até ~16 kHz usando Timer1
- Raspberry Pi Pico: até ~10 kHz usando PIO
- Aquisição no PC: até ~5 kHz com buffering adequado

Para conseguir estas frequências mais altas:
1. Aumentei o baudrate para 115200
2. Implementei buffering em todos os níveis
3. Usei Timer1 no Arduino
4. Usei PIO no Pico
5. Implementei threading no código Python
6. Reduzi overhead de impressão

---

Limitações que ainda existem:
1. Jitter do sistema operacional no PC
2. Overhead da comunicação serial
3. Tamanho do buffer serial
4. Tempo de processamento das amostras

Para frequências ainda mais altas, você precisaria:
1. Usar um microcontrolador dedicado
2. Implementar DMA
3. Usar protocolos mais rápidos que Serial (SPI, I2C)
4. Possivelmente usar um sistema operacional real-time
