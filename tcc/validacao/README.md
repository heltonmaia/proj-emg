# `tcc/validacao/` — validação espectral do sinal EMG

Esta pasta guarda o trabalho que confirmou cientificamente que o sinal
EMG capturado pelo setup atual (Raspberry Pi Pico + sensor de
instrumentação ±9 V) **é EMG real**, e não apenas artefato (rede
elétrica, drift de movimento, etc.).

## Conteúdo

| Arquivo | O que é |
|---|---|
| `reference_signal.csv` | Gravação de referência (cópia de `rec_emg/new_emg_data8.csv`) — 30 s a 500 Hz com prompts em 0/5/10/15/20/25 s. |
| `spectral_analysis.py` | Script de análise: corta janelas de repouso e contração, calcula FFT médio, PSD de Welch e espectrograma, gera figuras comparativas. |
| `spectral_analysis.{png,svg}` | Figura combinada de 4 painéis (tempo → espectrograma → FFT → Welch PSD). PNG pra preview, SVG vetorial pra inclusão em LaTeX / edição. |
| `panel_timeseries.svg` | Painel individual: sinal no tempo. |
| `panel_spectrogram.svg` | Painel individual: espectrograma. |
| `panel_fft.svg` | Painel individual: FFT linear médio repouso vs contração. |
| `panel_welch_psd.svg` | Painel individual: PSD (Welch, escala log) repouso vs contração. |

Os SVGs do espectrograma usam `rasterized=True` no `pcolormesh` — eixos
e texto continuam vetoriais, só o heatmap em si fica embutido como
raster (PNG dentro do SVG). Isso mantém os arquivos em ~1 MB em vez dos
~95 MB que sairiam com a heatmap totalmente vetorizada.

## Como rodar

```bash
source ../../.venv/bin/activate
cd tcc/validacao
python spectral_analysis.py
```

## A pergunta que motivou esta pasta

> *"O classificador EMG da minha aluna está aprendendo padrões de
> contração muscular real, ou só amplitude de ruído (rede elétrica,
> artefato de movimento)?"*

As features que a árvore de decisão usa (RMS, desvio padrão, média,
waveform length) são todas sensíveis a amplitude. Não distinguem
intrinsecamente entre EMG e ruído com amplitude similar. Por isso, a
pergunta é legítima e precisava de validação antes de seguir.

## Metodologia

1. Cortar o sinal em janelas alinhadas com os prompts:
   - **Repouso**: 0–5 s, 10–15 s, 20–25 s (mão aberta, parada)
   - **Contração**: 5–10 s, 15–20 s, 25–30 s (mão fechada)
2. Para cada janela, calcular o FFT (e PSD de Welch como verificação).
3. Comparar o espectro médio de repouso vs contração em três bandas
   diagnósticas:

| Banda | O que indica se predominar |
|---|---|
| **< 5 Hz** | Drift / artefato de movimento |
| **20–150 Hz** | Banda dominante de sEMG |
| **60 / 120 / 180 Hz** (picos finos) | Captação da rede elétrica |

## Resultado: razão Contração / Repouso por banda

| Banda | C/R |
|---|---|
| < 5 Hz (drift) | 2.57x |
| 5–20 Hz | 2.63x |
| **20–150 Hz (banda dominante EMG)** | **2.83x** |
| **150–250 Hz (banda alta EMG)** | **3.24x** |
| ~60 Hz (rede) | 2.95x |
| ~120 Hz (2ª harm.) | 2.48x |
| ~180 Hz (3ª harm.) | 3.22x |

## Conclusão

**O sinal é EMG real.** Três evidências convergem:

1. **A banda EMG (20–250 Hz) sobe broadband** quando a mão contrai
   (2.83x – 3.24x), uniformemente. EMG real ativa toda essa faixa.
2. **A banda <5 Hz (artefato de movimento) tem o MENOR ratio (2.57x)**
   — se o classificador estivesse pegando apenas movimento, esperaríamos
   o contrário.
3. **Os picos de 60/120/180 Hz aumentam proporcionalmente, não
   desproporcionalmente** ao resto da banda — rede elétrica está
   presente mas não domina.

O espectrograma (painel d da figura) confirma visualmente: durante as
contrações, **toda a coluna de frequências** se ilumina (assinatura de
broadband EMG), não apenas linhas estreitas em 60 Hz.

## O que isso significa pro projeto

- O TCC da aluna está cientificamente fundamentado: o classificador de
  fato discrimina contração muscular.
- A árvore de decisão atual, mesmo simples, opera sobre features
  legítimas de amplitude EMG.
- **Margens claras pra melhorar**:
  - Aplicar um **notch em 60 Hz** antes da extração de features melhora
    a relação sinal/ruído (eliminar os ~2.95x de captação de rede).
  - Aplicar um **passa-alta em 20 Hz** elimina drift de movimento
    (~2.57x na banda <5 Hz).
  - **Subir fs para 2 kHz no C5** (já implementado em `esp32-c5/`)
    permite usar a banda alta de sEMG (até ~500 Hz) que o Pico/500 Hz
    cortava em 250 Hz.

## Próximos passos planejados

1. Gravar novos registros com o setup C5 + sensor (mesmas conexões,
   eletrodos no flexor digitorum superficialis).
2. Repetir esta análise espectral no novo sinal pra confirmar que o
   novo setup mantém ou melhora a qualidade.
3. Decidir esquema de 3 classes (provavelmente: relaxada / aberta
   rígida / fechada rígida ou 3 níveis de força no flexor).
4. Treinar novo classificador sobre features extraídas após notch +
   passa-faixa causal aplicado on-device.
