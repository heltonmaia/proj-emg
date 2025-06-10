from machine import ADC, Pin
import time
import math

# ---------- Parâmetros ----------
NUM_AMOSTRAS = 100         # Janela de leitura (200 ms a 500 Hz)
TAMANHO_FILTRO = 5         # Média móvel com 5 amostras

# ---------- Inicialização ----------
adc = ADC(26)  # GPIO26 = ADC0

# ---------- Função do modelo (árvore de decisão) ----------
def prever_movimento(rms, desvio_padrao, media, waveform_length):
    if rms <= 2603.51:
        if desvio_padrao <= 55.87:
            if media <= 243.24:
                if rms <= 239.65:
                    if desvio_padrao <= 23.45:
                        return 0
                    else:
                        return 0
                else:
                    return 1
            else:
                return 0
        else:
            if desvio_padrao <= 57.87:
                if desvio_padrao <= 56.44:
                    if waveform_length <= 374.06:
                        return 1
                    else:
                        return 0
                else:
                    return 1
            else:
                if desvio_padrao <= 72.30:
                    if waveform_length <= 585.20:
                        return 0
                    else:
                        return 0
                else:
                    if rms <= 340.36:
                        return 1
                    else:
                        return 0
    else:
        if media <= 3861.59:
            if rms <= 3833.33:
                if media <= 3472.66:
                    if waveform_length <= 5482.57:
                        return 1
                    else:
                        return 1
                else:
                    return 1
            else:
                return 0
        else:
            if desvio_padrao <= 1327.76:
                if desvio_padrao <= 929.76:
                    return 1
                else:
                    if waveform_length <= 7776.34:
                        return 0
                    else:
                        return 1
            else:
                if desvio_padrao <= 1402.51:
                    return 0
                else:
                    return 1

# ---------- Funções auxiliares ----------
def media_movel(dados, tamanho):
    filtrado = []
    for i in range(len(dados)):
        janela = dados[max(0, i - tamanho + 1):i + 1]
        filtrado.append(sum(janela) / len(janela))
    return filtrado

def calcula_media(valores):
    return sum(valores) / len(valores)

def calcula_rms(valores):
    return math.sqrt(sum(x**2 for x in valores) / len(valores))

def calcula_desvio(valores, media):
    return math.sqrt(sum((x - media)**2 for x in valores) / len(valores))

def calcula_waveform_length(valores):
    return sum(abs(valores[i] - valores[i-1]) for i in range(1, len(valores)))

# ---------- Loop principal ----------
print("Iniciando leitura EMG com filtro digital...")

while True:
    janela = []

    for _ in range(NUM_AMOSTRAS):
        leitura = adc.read_u16() >> 4  # 12 bits (0 a 4095)

        # Amplificar leitura bruta
        janela.append(leitura * 10)

        time.sleep(1/500)  # 500 Hz

    # ---------- Aplicar filtro de média móvel ----------
    filtrado = media_movel(janela, TAMANHO_FILTRO)

    # ---------- Calcular features ----------
    media = calcula_media(filtrado)
    rms = calcula_rms(filtrado)
    desvio = calcula_desvio(filtrado, media)
    wl = calcula_waveform_length(filtrado)

    #print(f"RMS: {rms:.2f}, Desvio: {desvio:.2f}, Média: {media:.2f}, WL: {wl:.2f}")


    # ---------- Prever movimento ----------
    classe = prever_movimento(rms, desvio, media, wl)

    if classe == 1:
        print("🖐️ Mão FECHADA")
    else:
        print("✋ Mão ABERTA")

    time.sleep(0.1)

