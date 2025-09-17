# VozPraTexto 

Protótipo mínimo para Windows: grava áudio enquanto um atalho global é mantido pressionado e, ao soltar, transcreve e cola o texto no campo ativo.

## Principais componentes

- Python
- Captura de áudio: `sounddevice`
- Transcrição: `openai-whisper` (PyTorch)
- Hotkey / digitação: `keyboard`
- Ícone na tray: `pystray`
- Área de transferência: `pyperclip`

## Requisitos

- Python 3.10+ (recomendado)
- Espaço suficiente para instalar PyTorch e modelos do Whisper

## Instalação (rápido)

1. Criar e ativar o ambiente virtual (PowerShell):

```powershell
# na raiz do projeto
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Instalar dependências:

```powershell
python -m pip install -U pip
python -m pip install -r requirements.txt
```

3. Rodar o protótipo:

```powershell
python -m src.app
```

## Uso básico

- Segure `Ctrl+Shift` para começar a gravar.
- Solte `Ctrl+Shift` para parar e transcrever.
- O texto é copiado para a área de transferência e colado com `Ctrl+V` no aplicativo com foco.

## Configuração rápida

- Para escolher outro modelo do Whisper, edite a variável `MODEL_NAME` em `src/app.py` ou exporte a variável de ambiente `WHISPER_MODEL` antes de rodar:

```powershell
setx WHISPER_MODEL "small"
```

## Observações e dicas

- `openai-whisper` usa PyTorch; em CPUs fracas escolha modelos menores (ex.: `tiny`, `base`, `small`) para melhor desempenho.
- Em alguns sistemas, `keyboard` pode exigir privilégios de administrador para hooks globais.
- O app usa o clipboard para colar o texto e tenta restaurar o conteúdo anterior.
- Este repositório contém um POC — é recomendável melhorar tratamento de erros e oferecer uma UI de configuração antes de distribuir.
