# Raspberry Pi Pico code - main.py
from machine import Pin, Timer
import array
import rp2

# Configurações
OUTPUT_PIN = 12
INPUT_PIN = 13
FREQUENCY = 1000  # Hz - ajustável até ~10kHz
SAMPLE_BUFFER_SIZE = 1000

# Configuração dos pinos
output = Pin(OUTPUT_PIN, Pin.OUT)
input_pin = Pin(INPUT_PIN, Pin.IN)

# Buffer circular para amostras
samples = array.array('H', [0] * SAMPLE_BUFFER_SIZE)
sample_index = 0

# PIO para geração de onda de alta frequência
@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def square_wave():
    wrap_target()
    set(pins, 1)    [31]  # HIGH com delay
    set(pins, 0)    [31]  # LOW com delay
    wrap()

def setup_square_wave(frequency):
    sm = rp2.StateMachine(0, square_wave, freq=frequency*2, set_base=output)
    return sm

def sample_handler(timer):
    global sample_index
    samples[sample_index] = input_pin.value()
    sample_index = (sample_index + 1) % SAMPLE_BUFFER_SIZE
    
    if sample_index == 0:
        # Buffer cheio, envia dados
        print(''.join(str(x) for x in samples))

def main():
    # Configura gerador de onda usando PIO
    sm = setup_square_wave(FREQUENCY)
    sm.active(1)
    
    # Configura timer para amostragem
    timer = Timer()
    timer.init(freq=FREQUENCY*2, mode=Timer.PERIODIC, callback=sample_handler)
    
    while True:
        pass

if __name__ == "__main__":
    main()
