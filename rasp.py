from machine import ADC, Pin
import time

adc = ADC(Pin(26))
DATA_FILENAME = "new_emg_data10.csv"
SAMPLE_RATE = 500
PERIOD_US = int(1_000_000 / SAMPLE_RATE)  # 2000 µs
TOTAL_SAMPLES = SAMPLE_RATE * 30  # 15000

# Inicializa CSV
with open(DATA_FILENAME, "w") as f:
    f.write("Tempo(s),EMG_Value\n")

print("Iniciando gravação...")

start_time = time.ticks_us()
next_sample_time = start_time
sample_count = 0
messages = [
    (0, 'Manter o braço parado com a mão aberta'),
    (5, 'Feche a mão'),
    (10, 'Abra a mão'),
    (15, 'Feche a mão'),
    (20, 'Abra a mão'),
    (25, 'Feche a mão'),
]
last_message_index = -1

with open(DATA_FILENAME, "a") as f:
    while sample_count < TOTAL_SAMPLES:
        now = time.ticks_us()
        if time.ticks_diff(now, next_sample_time) >= 0:
            elapsed_time = sample_count / SAMPLE_RATE
            emg_value = adc.read_u16()
            f.write(f"{elapsed_time:.4f},{emg_value}\n")
            sample_count += 1
            next_sample_time = time.ticks_add(next_sample_time, PERIOD_US)

            for i, (msg_time, msg) in enumerate(messages):
                if elapsed_time >= msg_time and i > last_message_index:
                    print(f"{elapsed_time:.1f}s: {msg}")
                    last_message_index = i
                    break

print("\nGravação finalizada com sucesso.")
