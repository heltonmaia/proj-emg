from machine import ADC, Pin, Timer
import time

# Configuração
adc_pin = 26
adc = ADC(Pin(adc_pin))
DATA_FILENAME = "emg_data.csv"
RECORDING_DURATION = 30  # segundos

# Buffer menor para caber na RAM
BUFFER_SIZE = 1000  # 0.2 segundos de dados
emg_buffer = []
start_time = time.ticks_us()

def collect_data(timer):
    global emg_buffer, start_time
    
    emg_value = adc.read_u16()
    elapsed_time = time.ticks_diff(time.ticks_us(), start_time) / 1_000_000
    
    emg_buffer.append((elapsed_time, emg_value))
    
    # Salva quando o buffer atingir o tamanho máximo
    if len(emg_buffer) >= BUFFER_SIZE:
        save_buffer()
        emg_buffer = []  # Limpa o buffer

def save_buffer():
    with open(DATA_FILENAME, "a") as file:
        for time_val, emg_val in emg_buffer:
            file.write(f"{time_val:.6f},{emg_val}\n")

# Inicializa arquivo
with open(DATA_FILENAME, "w") as file:
    file.write("Tempo(s),EMG_Value\n")

# Configura Timer
timer = Timer()
timer.init(freq=5000, mode=Timer.PERIODIC, callback=collect_data)

try:
    print(f"Gravando por {RECORDING_DURATION} segundos...")
    time.sleep(RECORDING_DURATION)
    timer.deinit()  # Para o timer
    save_buffer()   # Salva dados restantes
    print("Gravação finalizada!")
except KeyboardInterrupt:
    timer.deinit()
    save_buffer()
    print("\nGravação interrompida pelo usuário.")