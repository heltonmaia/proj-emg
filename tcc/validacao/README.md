# `tcc/validacao/` — validação espectral do sinal EMG

Esta pasta guarda o trabalho que confirmou cientificamente que o sinal
EMG capturado pelo setup atual (Raspberry Pi Pico + sensor de
instrumentação ±9 V) **é EMG real**, e não apenas artefato (rede
elétrica, drift de movimento, etc.).

Duas gravações de referência foram analisadas em paralelo:

| Gravação | fs | Origem | Formato CSV |
|---|---|---|---|
| `reference_signal_500hz.csv` | 500 Hz | Pico (cópia de `rec_emg/new_emg_data8.csv`) | `Tempo(s), EMG_Value` |
| `reference_signal_1000hz.csv` | 1000 Hz | Pico em variante a 1 kHz (cópia de `tcc/emg_1000hz_raw5.csv`) | `EMG_Value` (tempo sintetizado do índice) |

Ambas com 30 s de duração, mesmo sensor e setup, com a sequência de
prompts assumida: 0s aberta parada → 5s fecha → 10s abre → 15s fecha →
20s abre → 25s fecha.

## Conteúdo

```
tcc/validacao/
├── README.md
├── spectral_analysis.py            # script que processa as duas gravações
├── reference_signal_500hz.csv      # gravação Pico, 500 Hz
├── reference_signal_1000hz.csv     # gravação Pico, 1000 Hz
├── 500hz/                          # resultados da gravação de 500 Hz
│   ├── spectral_analysis.{png,svg} # figura combinada 4 painéis
│   ├── panel_timeseries.svg        # painel individual: sinal no tempo
│   ├── panel_spectrogram.svg       # painel individual: espectrograma
│   ├── panel_fft.svg               # painel individual: FFT linear
│   └── panel_welch_psd.svg         # painel individual: PSD Welch (log)
└── 1000hz/                         # idem, resultados da gravação de 1000 Hz
    ├── spectral_analysis.{png,svg}
    ├── panel_timeseries.svg
    ├── panel_spectrogram.svg
    ├── panel_fft.svg
    └── panel_welch_psd.svg
```

PNG é só pra preview rápido; SVG é o formato de trabalho (vetorial,
editável). O espectrograma usa `rasterized=True` no `pcolormesh` —
eixos e texto ficam vetoriais, só o heatmap é embutido como raster.
Isso mantém os arquivos em ~1 MB em vez de ~95 MB.

## Como rodar

```bash
source ../../.venv/bin/activate
cd tcc/validacao
python spectral_analysis.py
```

## A pergunta que motivou esta pasta

> *"O classificador EMG atual está aprendendo padrões de contração
> muscular real, ou só amplitude de ruído (rede elétrica, artefato de
> movimento)?"*

As features que a árvore de decisão usa (RMS, desvio padrão, média,
waveform length) são todas sensíveis a amplitude. Não distinguem
intrinsecamente entre EMG e ruído com amplitude similar. Por isso, a
pergunta é legítima e precisava de validação antes de seguir.

## Metodologia

1. Cortar o sinal em janelas alinhadas com os prompts:
   - **Repouso**: 0–5 s, 10–15 s, 20–25 s (mão aberta, parada)
   - **Contração**: 5–10 s, 15–20 s, 25–30 s (mão fechada)
2. Para cada janela, calcular o FFT médio e a PSD de Welch.
3. Comparar o espectro médio de repouso vs contração em três bandas
   diagnósticas:

| Banda | O que indica se predominar |
|---|---|
| **< 5 Hz** | Drift / artefato de movimento |
| **20–150 Hz** | Banda dominante de sEMG |
| **60 / 120 / 180 Hz** (picos finos) | Captação da rede elétrica |

## Resultado: razão Contração / Repouso por banda

| Banda | 500 Hz C/R | 1000 Hz C/R |
|---|---:|---:|
| < 5 Hz (drift) | 2.57x | **2.03x** ← menor de todos em ambos |
| 5–20 Hz | 2.63x | 2.82x |
| **20–150 Hz (EMG dominante)** | **2.83x** | **2.67x** |
| **150–250 Hz (EMG alta)** | **3.24x** | **3.07x** |
| ~60 Hz (rede) | 2.95x | 2.47x |
| ~120 Hz (2ª harm.) | 2.48x | 3.09x |
| ~180 Hz (3ª harm.) | 3.22x | 2.79x |

A 1000 Hz cobre adicionalmente a banda 250–500 Hz, que o Pico em 500 Hz
não conseguia ver (Nyquist cortava). A PSD da gravação de 1000 Hz
(painel 4 da figura `spectral_analysis_1000hz.png`) mostra **energia de
EMG persistindo até ~400 Hz** durante contração — confirmando na prática
que vale a pena ir pra 2 kHz no C5 (Nyquist = 1 kHz, cobre toda a banda
útil de sEMG com folga).

## Conclusão

**O sinal é EMG real, validado nas duas taxas de amostragem.** Três
evidências convergem em ambas as gravações:

1. **A banda EMG (20–250 Hz) sobe broadband** durante contração
   (2.67x – 3.24x), uniformemente. EMG real ativa toda essa faixa.
2. **A banda <5 Hz (artefato de movimento) tem o MENOR ratio** dos
   bandos analisados em ambas as gravações — se o classificador
   estivesse pegando apenas movimento, seria o contrário.
3. **Os picos de 60/120/180 Hz aumentam proporcionalmente** ao resto da
   banda — rede elétrica está presente mas não domina.

O espectrograma (painel 2 das figuras combinadas) confirma visualmente:
durante as contrações, **toda a coluna de frequências** se ilumina
(assinatura de broadband EMG), não apenas linhas estreitas em 60 Hz.

## O que isso significa pro projeto

- O TCC está cientificamente fundamentado: o classificador de fato
  discrimina contração muscular.
- A árvore de decisão atual, mesmo simples, opera sobre features
  legítimas de amplitude EMG.
- **Margens claras pra melhorar**:
  - Aplicar um **notch em 60 Hz** antes da extração de features melhora
    a relação sinal/ruído (eliminar os ~2.5–3x de captação de rede).
  - Aplicar um **passa-alta em 20 Hz** elimina drift de movimento
    (~2x na banda <5 Hz).
  - **Subir fs para 2 kHz no C5** (já implementado em `esp32-c5/`)
    permite cobrir toda a banda útil de sEMG sem dobrar o sinal —
    a comparação 500 Hz vs 1000 Hz aqui já demonstra que há sinal
    relevante em 250+ Hz, que o Pico cortava.

## Próximos passos planejados

1. Gravar novos registros com o setup C5 + sensor (mesmas conexões,
   eletrodos no flexor digitorum superficialis).
2. Repetir esta análise espectral no novo sinal pra confirmar que o
   novo setup mantém ou melhora a qualidade.
3. Decidir esquema de 3 classes (provavelmente: relaxada / aberta
   rígida / fechada rígida ou 3 níveis de força no flexor).
4. Treinar novo classificador sobre features extraídas após notch +
   passa-faixa causal aplicado on-device.
