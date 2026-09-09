# Translator Live

Aplicativo desktop (janela nativa, sem navegador) para **legendas ao vivo** e **tradução local** entre inglês e português.

Tudo roda no seu computador: Whisper reconhece a fala na GPU, o NLLB traduz na CPU e os falantes aparecem como **Pessoa 1**, **Pessoa 2**, …

## O que ele faz

- **Inglês → Português**: transcreve em inglês e traduz para português
- **Português → Inglês**: transcreve em português e traduz para inglês
- **Só legenda**: transcreve no idioma escolhido, sem traduzir
- Identifica mais de uma pessoa na conversa (microfone e áudio do sistema ficam separados)
- Overlay de legendas sempre visível, arrastável
- Campo para traduzir um texto colado, com o mesmo modelo local

Latência típica: cerca de **1 a 3 segundos** para a linha final. Isso é normal em modelo local.

## Hardware previsto

Pensado para um Vivobook com **24 GB de RAM**, **i5** e **RTX 2050 4 GB**:

| Peça | Modelo | Onde |
|---|---|---|
| Fala | Whisper `large-v3-turbo` (int8), com fallback `small` | GPU |
| Tradução | NLLB-200 distilled 600M (CTranslate2 int8) | CPU |
| Falantes | SpeechBrain ECAPA + agrupamento | CPU |

Se a VRAM não aguentar o Turbo, o app cai sozinho para o Small.

## Como iniciar

1. Instale **Python 3.11+** e o driver NVIDIA recente. As bibliotecas CUDA 12 (cuBLAS/cuDNN) entram via pip — não precisa do toolkit completo.
2. Dê um duplo clique em `iniciar.bat` (ou rode no terminal).
3. Na primeira execução, o app baixa os modelos para `%LOCALAPPDATA%\TranslatorLive\models` (fora do OneDrive).
4. Escolha o modo, ligue microfone e/ou áudio do sistema e clique em **Iniciar escuta**.

Atalho: `Ctrl+Shift+L` mostra ou esconde o overlay.

Para só baixar os modelos no terminal:

```bat
.venv\Scripts\python.exe scripts\download_models.py
```

## Áudio do sistema (outras pessoas na call)

O app usa loopback WASAPI. Se a call ficar muda no overlay:

- Desative o **modo exclusivo** do dispositivo de reprodução no Windows
- Headset Bluetooth aumenta o atraso
- Confira se o dispositivo de loopback certo está selecionado no painel

## Testes

```bat
.venv\Scripts\python.exe -m pytest
```

Os testes cobrem resample, modos, clustering de falantes, VAD/streaming e persistência. Não exigem GPU.

## Licenças dos modelos

- Whisper / faster-whisper: MIT
- NLLB-200: CC-BY-NC 4.0 (uso pessoal/pesquisa)
- SpeechBrain ECAPA: Apache 2.0
