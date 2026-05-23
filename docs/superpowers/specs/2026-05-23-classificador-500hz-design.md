# Spec — Classificador EMG 500 Hz: reprodução do pipeline do TCC + tentativa de ganho de acurácia

**Data**: 2026-05-23
**Status**: spec rascunho, aguardando revisão do usuário antes da implementação.

## 1. Contexto

O TCC do projeto descreve um classificador binário (mão aberta / mão fechada) baseado em EMG single-channel, com pipeline:

- Filtragem (`filtfilt` zero-phase): notch 60 Hz + passa-alta 20 Hz + passa-baixa 240 Hz @ 500 Hz / 450 Hz @ 1000 Hz.
- Features extraídas (varia por fs): RMS, MAV, SD, WL @ 500 Hz; RMS, MAV, WL, SSC, ZC @ 1000 Hz.
- Treinamento: `DecisionTreeClassifier(max_depth=5, random_state=42)`, scikit-learn, split 80/20.
- Resultado reportado: **83% (DT @ 500 Hz)** / **87% (DT @ 1000 Hz)**.

O **código de treino não está versionado no repositório** — rodou em Google Colab e produziu um `.pkl` que também não foi commitado. O que existe no repo é o `prediction.py` (arquivo MicroPython embarcado no Pico) com uma árvore de decisão colada à mão como if/else.

Auditoria do `prediction.py` revela **inconsistência entre o código embarcado e o texto do TCC**:

| Aspecto | TCC (texto) | `prediction.py` (deployado) |
|---|---|---|
| Features @ 500 Hz | RMS, **MAV**, SD, WL | RMS, SD, **mean**, WL |
| MAV vs mean | MAV = `mean(\|x\|)` | mean = `mean(x)` — função diferente |

Ou seja, o classificador rodando na prótese **não corresponde** ao que o texto descreve.

## 2. Objetivo

Construir um pipeline de treinamento **versionado, reproducível e alinhado com o texto do TCC**, capaz de:

1. **Reproduzir** o resultado a 500 Hz (~83% de acurácia) a partir dos dados em `rec_emg/`.
2. **Alinhar** o `prediction.py` ao modelo treinado (features corretas, árvore vinda do treino, não colada à mão).
3. **Tentar superar** o baseline do TCC via sweep modesto de features e profundidade de árvore — sem mudar a arquitetura (continua DT) nem o paradigma (continua binário).

Foco: 500 Hz primeiro, porque temos todos os 10 CSVs em `rec_emg/`. Pipeline a 1000 Hz fica como trabalho futuro (só temos 1 dos 5 CSVs originais a 1000 Hz no repo).

## 3. Fora de escopo

Explicitamente **não** vamos fazer nesta iteração:

- 3 classes (relaxada / aberta / fechada rígidas). Fica para iteração futura.
- Coleta de dados nova com C5 a 2 kHz. Fica para iteração futura.
- Random Forest, SVM, MLP. Continuamos com DT pra alinhar com o TCC.
- Filtragem causal on-device (a discussão "filtfilt zero-phase ≠ runtime causal"). Fica para iteração futura.
- Reescrever o `cods_protese_emg.ipynb` original.
- Reformular o texto do TCC.

## 4. Dados de entrada

- **Origem**: `rec_emg/new_emg_data{1..10}.csv`, cada arquivo com 15 001 linhas (header + 15 000 amostras) = 30 s × 500 Hz.
- **Formato**: colunas `Tempo(s), EMG_Value`. `EMG_Value` é leitura ADC de 16 bits (0–65535) do Pico via `adc.read_u16()`.
- **Protocolo de gravação**: prompts a 0/5/10/15/20/25 s alternando mão aberta (0s) → fechada (5s) → aberta (10s) → fechada (15s) → aberta (20s) → fechada (25s). Cada intervalo de 5 s tem um rótulo único.

> Nota: o texto do TCC menciona "5 sessões" a 500 Hz, mas o repositório contém 10 CSVs. Vamos usar **todos os 10**. A discrepância de contagem é registrada aqui mas não bloqueia.

## 5. Arquitetura — estrutura no repositório

```
tcc/treinamento/                       ← NOVA pasta
├── README.md                          # documentação completa do pipeline
├── train.py                           # script principal end-to-end
├── features.py                        # funções de feature reusáveis
├── filter.py                          # design e aplicação dos filtros
├── test_features.py                   # testes unitários mínimos
├── dt_500hz.pkl                       # modelo final (joblib)
└── results/
    ├── metrics.txt                    # top 5 configs + a vencedora
    ├── confusion_matrix.{png,svg}     # da config vencedora (absoluta + normalizada)
    ├── decision_tree.{png,svg}        # da config vencedora
    └── feature_importance.{png,svg}   # da config vencedora

prediction.py (raiz)                   ← REGENERADO ao fim do train.py
                                       # mantém esqueleto MicroPython (ADC, loop)
                                       # bloco modelo (features + tree) vem do treino
```

**Por que essa separação**:
- `train.py` é o "entry point" — você executa, gera tudo.
- `features.py` e `filter.py` separam funções reusáveis e testáveis do orchestrator.
- `results/` separa código de saída.
- `prediction.py` continua na raiz para deployment MicroPython na Pico (não muda o fluxo de deployment).

## 6. Pipeline de processamento

### 6.1 Filtragem

Igual ao TCC, **offline, zero-phase, scipy**:

```python
from scipy.signal import iirnotch, butter, filtfilt, sosfiltfilt

def filter_emg(signal, fs=500):
    # 1. Notch 60 Hz (Q=30) via filtfilt
    b_notch, a_notch = iirnotch(60.0, Q=30.0, fs=fs)
    s1 = filtfilt(b_notch, a_notch, signal)
    # 2. Passa-faixa 20–240 Hz, Butterworth 4ª ordem, via sosfiltfilt
    sos = butter(4, [20, 240], btype="bandpass", fs=fs, output="sos")
    return sosfiltfilt(sos, s1)
```

Aplicado em cada CSV inteiro antes do janelamento.

### 6.2 Janelamento e rotulagem

| Parâmetro | Valor |
|---|---|
| Tamanho da janela | **100 amostras = 200 ms** (igual ao `prediction.py` deployado) |
| Sobreposição | **50%** → step = 50 amostras = 100 ms |
| Margem de transição | **500 ms** descartados antes e depois de cada mudança de rótulo |

Janelas que cobrem mais de um rótulo (devido ao step deslizante) são descartadas. Sobra ~4 s de dados "puros" por intervalo de 5 s.

Rótulos: `0 = aberta` (intervalos 0-5s, 10-15s, 20-25s), `1 = fechada` (intervalos 5-10s, 15-20s, 25-30s).

Estimativa de quantidade de janelas: 6 intervalos × ~4 s puros × (1 s / 0.1 s step) = ~240 janelas/CSV × 10 CSVs = **~2 400 janelas totais**.

### 6.3 Feature extraction

Implementadas em `features.py`:

```python
def rms(x):            return np.sqrt(np.mean(x**2))
def mav(x):            return np.mean(np.abs(x))
def sd(x):             return np.std(x, ddof=0)
def wl(x):             return np.sum(np.abs(np.diff(x)))
def zc(x, thresh=0):   # zero crossings com deadzone
    return np.sum((x[:-1] * x[1:] < 0) & (np.abs(x[1:] - x[:-1]) > thresh))
def ssc(x, thresh=0):  # slope sign changes com deadzone
    d = np.diff(x)
    return np.sum((d[:-1] * d[1:] < 0) & (np.abs(d[1:] - d[:-1]) > thresh))
def var(x):            return np.var(x, ddof=0)
def wamp(x, thresh):   return np.sum(np.abs(np.diff(x)) > thresh)
```

Thresholds começam em 0 (sem deadzone). Ajustáveis se ZC/SSC ficarem dominados por ruído.

### 6.4 Treinamento

`sklearn.tree.DecisionTreeClassifier` com `random_state=42` (matching TCC).

### 6.5 Validação cruzada

**Leave-One-Group-Out (LOGO)** onde cada CSV é um group. 10 folds:

```
fold 1:  treina em CSV 2..10,  testa em CSV 1
fold 2:  treina em CSV 1,3..10, testa em CSV 2
...
fold 10: treina em CSV 1..9,    testa em CSV 10
```

Métrica primária: **acurácia média ± desvio padrão** entre os 10 folds.

Por que LOGO em vez do 80/20 do TCC: o 80/20 single-split pode embaralhar janelas do mesmo CSV no treino e teste (vazamento intra-gravação). LOGO força generalização entre gravações — mais conservador, mais honesto.

## 7. Experimentos (sweep)

Combinação cartesiana de:

**Conjuntos de features testados**:

| ID | Features |
|----|----------|
| baseline | RMS, MAV, SD, WL (= TCC @ 500 Hz) |
| +ZC | RMS, MAV, SD, WL, ZC |
| +SSC | RMS, MAV, SD, WL, SSC |
| +ZC+SSC | RMS, MAV, SD, WL, ZC, SSC |
| +VAR | RMS, MAV, SD, WL, VAR |
| +WAMP | RMS, MAV, SD, WL, WAMP |
| tcc-1000hz | RMS, MAV, WL, SSC, ZC (= TCC @ 1000 Hz, testado a 500 Hz) |

**`max_depth`**: 3, 5, 7, 10, None (unbounded)

Total: 7 × 5 = 35 configs.

Cada config roda LOGO completo (10 folds). Saída: acurácia média ± std.

## 8. Critério de seleção da config vencedora

Maior acurácia média no LOGO CV. Em caso de empate (mesma acurácia média ± 0.5%):

1. **Menor desvio padrão** entre folds (= mais estável).
2. **Menos features** (= mais interpretável).
3. **Menor `max_depth`** (= menos overfit, mais simples).

A "config vencedora" é re-treinada no **dataset inteiro** (todos os 10 CSVs) e essa árvore é exportada.

## 9. Métricas reportadas

No `metrics.txt`:

- Top 5 configs do sweep + a vencedora.
- Para a vencedora: acurácia, precision, recall, F1 (por classe e macro), matriz de confusão (absoluta + normalizada por linha).
- Header com: timestamp, número total de janelas, número total de configs testadas.

## 10. Artefatos produzidos

| Arquivo | Quando regerado | Conteúdo |
|---|---|---|
| `tcc/treinamento/dt_500hz.pkl` | Toda vez que `train.py` roda | Modelo sklearn da config vencedora, treinado em todos os 10 CSVs. |
| `tcc/treinamento/results/metrics.txt` | Idem | Top 5 + vencedora + métricas extras. |
| `tcc/treinamento/results/confusion_matrix.{png,svg}` | Idem | Matriz da vencedora (absoluta + normalizada lado a lado). |
| `tcc/treinamento/results/decision_tree.{png,svg}` | Idem | Visualização via `sklearn.tree.plot_tree`. |
| `tcc/treinamento/results/feature_importance.{png,svg}` | Idem | Barchart de importância de cada feature da vencedora. |
| `prediction.py` (raiz) | Idem | **Sobrescrito** com features corretas + tree inline. |

Todas as figuras: PNG + SVG (vetorial pra LaTeX). Espectrograma-style rasterização não se aplica (essas figuras são leves, full vector).

## 11. Regeneração do `prediction.py`

`train.py` reescreve `prediction.py` no final do treino, baseado em um template embutido.

### 11.1 O que muda vs o que fica

- **Esqueleto MicroPython estável** (não muda): imports de `machine`, ADC setup, loop de amostragem, prints `Mão FECHADA` / `Mão ABERTA`, `TAMANHO_FILTRO = 5`.
- **Bloco modelo regenerado**:
  - `NUM_AMOSTRAS` (igual ao window size do treino).
  - Funções de feature usadas (subset de rms/mav/sd/wl/zc/ssc/var/wamp).
  - `prever_movimento(...)` com assinatura matching as features da config vencedora.
  - Corpo de `prever_movimento` é a árvore convertida pra if/else aninhado.

### 11.2 Conversão da árvore para if/else

`sklearn.tree.export_text` dá texto bruto da árvore. Convertemos manualmente pra MicroPython if/else (sem dependência de sklearn na placa).

### 11.3 Header de auditoria

`prediction.py` regerado começa com:

```python
# AUTO-GENERATED by tcc/treinamento/train.py at 2026-05-23 16:42:00
# Model: DecisionTreeClassifier, max_depth=7, random_state=42
# Features: rms, mav, sd, wl, zc, ssc
# LOGO CV accuracy: 86.2% ± 2.4%
# Trained on: rec_emg/new_emg_data{1..10}.csv
```

Você bate o olho no header e sabe qual versão está flashada.

## 12. Testes

`test_features.py` cobre o caso crítico: **MAV ≠ mean** (o bug do `prediction.py` atual).

```python
def test_mav_uses_abs():
    assert mav(np.array([-2, 2])) == 2.0     # MAV correto
    assert np.mean(np.array([-2, 2])) == 0   # mean simples — diferente
```

Demais testes: sanidade nas funções (rms, wl, zc, ssc) com inputs conhecidos.

Rodar: `pytest tcc/treinamento/test_features.py`.

## 13. Dependências novas em `requirements.txt`

- `scikit-learn` — DT, métricas, plot_tree, export_text.
- `joblib` — serialização (transitiva de sklearn, declaro explícito).
- `pytest` — opcional, pra rodar os testes.

`scipy`, `numpy`, `pandas`, `matplotlib` já estão presentes.

## 14. Tratamento de erros

`train.py` valida na entrada e falha alto/claro:

- `rec_emg/` precisa existir e ter ≥1 CSV → senão `SystemExit`.
- Cada CSV precisa ter coluna `EMG_Value` → senão `SystemExit`.
- CSVs com tamanho diferente de 15 000 amostras: warning, mas processa.
- Se nenhuma janela válida sobrar após corte de transições: `SystemExit`.
- Se nenhum config conseguir treinar (ex: features constantes): `SystemExit`.

## 15. Critério de sucesso

**Mínimo**: pipeline rodando end-to-end, gerando todos os artefatos, com acurácia LOGO mensurável (mesmo que abaixo de 83%).

**Esperado**: acurácia LOGO da config vencedora **≥ baseline do TCC (83%)**, com a ressalva de que LOGO é mais conservador que 80/20 single-split, então ficar em 80-82% ainda é defensável e cientificamente honesto.

**Bom**: acurácia LOGO **acima de 85%** com config diferente do baseline (= ganho real do sweep).

Em qualquer caso, o pipeline é reproduzível e o `prediction.py` deployado fica alinhado ao modelo treinado.

## 16. Riscos e questões em aberto

1. **Discrepância de número de sessões** (TCC menciona 5, repo tem 10). Resolução: usar todos os 10. Não bloqueia.

2. **A acurácia LOGO pode ficar abaixo dos 83% do TCC**, simplesmente porque LOGO é mais conservador. Isso não é um "fail" — é informação científica honesta. Documentar no `metrics.txt`.

3. **Importance dos thresholds de ZC/SSC**: comecei com 0 (sem deadzone). Pode ser que os números fiquem dominados por ruído de quantização. Plano B: setar threshold como ~5% da amplitude máxima do sinal filtrado. Decidir empiricamente no primeiro run.

4. **Tamanho da janela**: 100 amostras (200 ms) é o que o `prediction.py` deployado usa. Não vamos sweepar isso na primeira iteração — manter alinhado com o deployment. Se acurácia ficar baixa, considerar sweep de janela como segunda rodada.

5. **Regeneração do `prediction.py` pode quebrar deployment** se a interface mudar. Mitigação: manter `NUM_AMOSTRAS=100`, manter sample rate 500 Hz, manter o esqueleto MicroPython idêntico. Só o bloco modelo muda.

6. **Train/inference filter mismatch — herdado do TCC**. O treino aplica `filtfilt` zero-phase (notch + passa-faixa 20–240 Hz), mas o `prediction.py` na Pico só roda média móvel de 5 amostras como filtro. Isso significa que as features extraídas durante inferência não vêm do mesmo sinal usado no treino. O TCC tem o mesmo gap e mesmo assim reporta 87%, então tomamos como aceitável para "alinhamento". A correção fica para iteração futura (filtro IIR causal on-device, viável no ESP32-C5).

## 17. Trabalhos futuros (fora desta spec)

- Pipeline equivalente a 1000 Hz (precisa recuperar os 4 CSVs faltantes ou regravar).
- Pipeline a 2 kHz no ESP32-C5 (depende da nova coleta).
- 3 classes (relaxada / aberta rígida / fechada rígida).
- Filtro causal on-device (alinha treino offline com inferência runtime).
- Validação cruzada inter-sujeito (precisa de dados de outras pessoas).
