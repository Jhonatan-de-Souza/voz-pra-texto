# Instruções (PT-BR)

Este repositório contém um POC (prova de conceito) de um aplicativo de ditado local para Windows que:

- Fica em segundo plano com um ícone na tray (bandeja do sistema).
- Começa a gravar áudio enquanto um atalho global é pressionado (Ctrl+Shift).
- Ao soltar o atalho, transcreve o áudio usando OpenAI Whisper (local, via PyTorch) e cola a transcrição no campo de entrada ativo.

## Requisitos

- Windows 10/11
- Python 3.10+ (preferencialmente 3.11 ou 3.12)
- Microfone funcional
- Espaço em disco para modelos do Whisper (o modelo `small` tem centenas de MB; `base` é menor)

## Passos rápidos (PowerShell)

1. Abra o PowerShell na pasta do projeto (ex.: `C:\Users\Você\...\voz pra texto`).

2. Criar e ativar o ambiente virtual (opcional: use o `scripts\create_venv.ps1`):

```powershell
# Criar e ativar venv manualmente
python -m venv .venv
. .\.venv\Scripts\Activate.ps1

# ou usar o script fornecido:
# .\scripts\create_venv.ps1
```

3. Atualizar o pip e instalar dependências:

```powershell
python -m pip install -U pip
python -m pip install -r requirements.txt
```

> Observação: a instalação do `torch` pode baixar uma wheel grande; se você tiver GPU NVIDIA e quiser suporte CUDA, siga as instruções oficiais do PyTorch (https://pytorch.org/get-started/locally/) para instalar a versão adequada.

4. Rodar o aplicativo:

```powershell
python -m src.app
```

- Um ícone "STT" aparecerá na bandeja do sistema.
- Segure `Ctrl+Shift` para começar a gravar; solte `Ctrl+Shift` para parar a gravação e automaticamente transcrever e colar o texto.

## Configurações úteis

- Modelo Whisper: por padrão o POC carrega `small`. Para mudar edite `MODEL_NAME` em `src/app.py` ou exporte a variável de ambiente `WHISPER_MODEL`:

```powershell
$env:WHISPER_MODEL = 'base'
python -m src.app
```

Modelos disponíveis (exemplos): `tiny`, `base`, `small`, `medium`, `large`.

- Se quiser colar sem usar a área de transferência (simulando digitação), substitua a lógica de `pyperclip` + `keyboard.send('ctrl+v')` por `keyboard.write(text)` em `src/app.py`.

## Limitações e notas

- O POC usa `keyboard` para hooks globais; em alguns sistemas o módulo pode exigir execução com privilégios elevados ou permissões especiais.
- O app tenta restaurar o conteúdo anterior do clipboard após colar; contudo, há pequenas janelas de tempo nas quais o clipboard é alterado.
- Whisper em CPU pode ser lento em processadores fracos; modelos maiores trazem maior precisão mas usam mais RAM/CPU.
- Este POC não é um produto final — faltam opções de configuração, tratamento avançado de erros, e empacotamento como .exe.

## Remoção do ambiente

Para remover o ambiente virtual (se quiser limpar espaço):

```powershell
Remove-Item -Recurse -Force .\.venv
```

## Próximos passos sugeridos

- Adicionar uma GUI de configurações (atalho, modelo, microfone).
- Suporte a `whisper.cpp` (ggml) para reduzir uso de RAM/CPU e evitar dependência de PyTorch.
- Empacotar com `pyinstaller`/`nuitka` para distribuir como executável Windows.

---

Se quiser, eu crio também um README principal em PT-BR com resumo curto e link para este arquivo de instruções detalhadas.
