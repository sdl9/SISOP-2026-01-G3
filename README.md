# Trabalho Final de Sistemas Operacionais

## Grupo
- Aluno 1: Fernando Mueller
- Aluno 2: Arthur Duarte
- Aluno 3: Matheus Muller
- Aluno 4: Guilherme
- Aluno 5: Laíssa Salles
- Aluno 6: Nicolas Jahno

## Sobre o projeto

Simulador de escalonamento de processos com algoritmo **Round Robin com Feedback**,
desenvolvido como trabalho final da disciplina de Sistemas Operacionais — Feevale 2026/01.

O simulador implementa:
- Duas filas de prioridade (alta e baixa) com quantums distintos
- Três dispositivos de I/O independentes: disco, fita magnética e impressora
- Regras de retorno diferenciadas por dispositivo após conclusão do I/O
- Logs detalhados de cada evento por unidade de tempo
- Métricas finais: turnaround, tempo de espera, preempções e CPU ociosa

## Linguagem utilizada

Python 3.12 — sem dependências externas, apenas biblioteca padrão.

## Convenção de código

Todo o código deve ser comentado. Cada função, bloco lógico e decisão
relevante deve ter um comentário explicando o que faz e por quê.
Isso facilita a leitura e revisão por todos os membros do grupo.

## Premissas do escalonador

| Parâmetro | Valor |
|---|---|
| Quantum — Fila ALTA | 2 ticks |
| Quantum — Fila BAIXA | 4 ticks |
| Duração de I/O — DISCO | 4 ticks |
| Duração de I/O — FITA | 6 ticks |
| Duração de I/O — IMPRESSORA | 3 ticks |
| Retorno após DISCO | Fila BAIXA |
| Retorno após FITA | Fila ALTA |
| Retorno após IMPRESSORA | Fila ALTA |
| Processos novos | Entram sempre na Fila ALTA |
| Quantum expirado | Processo rebaixado para Fila BAIXA |
| Critério de finalização | Filas de CPU e I/O vazias e CPU livre |
| Semente aleatória | N/A — processos definidos via CSV |

## Estrutura do repositório

```
SISOP-2026-01-G3/
├── input/
│   ├── .gitkeep
│   └── processes.csv        # Arquivo de entrada com os processos a escalonar
├── output/
│   ├── .gitkeep
│   └── execution_log.txt    # Gerado automaticamente após a execução
├── src/
│   ├── .gitkeep
│   ├── io_manager.py        # Gerenciamento das filas de I/O por dispositivo
│   ├── main.py              # Ponto de entrada — define premissas e executa o escalonador
│   ├── pcb.py               # Estrutura do Bloco de Controle de Processo (PCB)
│   └── scheduler.py         # Loop principal, filas de CPU e lógica de escalonamento
├── .dockerignore            # Arquivos ignorados no contexto de build Docker
├── .gitignore               # Arquivos ignorados pelo Git
├── Dockerfile               # Configuração da imagem Docker do projeto
└── README.md                # Documentação principal do projeto
```

> As pastas contêm um arquivo `.gitkeep` apenas para que o Git rastreie
> pastas vazias. O Git não versiona pastas sem arquivos — o `.gitkeep`
> serve como placeholder e pode ser removido quando arquivos reais forem adicionados.

> Este README será atualizado conforme o progresso do trabalho.

## Formato do arquivo de entrada

O simulador lê os processos do arquivo `input/processes.csv`.

**Colunas:**

| Coluna | Tipo | Descrição |
|---|---|---|
| `PID` | inteiro | Identificador único do processo |
| `PPID` | inteiro | PID do processo pai (0 = processo raiz) |
| `TIME_REMAINING` | inteiro | Unidades de CPU necessárias para finalizar |
| `IO_TYPE` | inteiro | Dispositivo de I/O: `0`=nenhum `1`=disco `2`=fita `3`=impressora |

**Exemplo (`input/processes.csv`):**

```csv
PID,PPID,TIME_REMAINING,IO_TYPE
1,0,5,1
2,0,3,0
3,1,8,2
4,1,2,0
```

## Como executar

```bash
# A partir da raiz do projeto
python src/main.py
```

O simulador lê `input/processes.csv` e salva o log em `output/execution_log.txt`.

**Exemplo de saída:**

```
============================================================
[t=000] INICIANDO SIMULAÇÃO — Round Robin com Feedback + I/O
[t=000] Quantum ALTA=2 | Quantum BAIXA=4 | Dispositivos: DISCO, FITA, IMPRESSORA
[t=000] Durações de I/O: DISCO=4 | FITA=6 | IMPRESSORA=3
============================================================
[t=000] Processo criado — Fila ALTA: [PID:1 | Status:READY | Prioridade:HIGH | TempoRestante:5 | I/O:DISCO]
[t=000] Processo criado — Fila ALTA: [PID:2 | Status:READY | Prioridade:HIGH | TempoRestante:3 | I/O:NENHUM]
[t=001] Troca de contexto — CPU para PID 1 (Fila: HIGH | Quantum: 2)
[t=001] Executando PID 1 | Resta: 4 | Quantum: 1/2 | I/O: DISCO
[t=002] Executando PID 1 | Resta: 3 | Quantum: 2/2 | I/O: DISCO
[t=002] PID 1 solicitou I/O [DISCO] | Bloqueado por 4 ticks
...
[t=XXX] FIM DA SIMULAÇÃO
============================================================

──────────── MÉTRICAS FINAIS ────────────
Tempo total da simulação    : X ticks
Processos finalizados       : X
Total de preempções         : X
Turnaround médio            : X.XX ticks
Tempo médio de espera       : X.XX ticks
CPU ociosa                  : X.X%
─────────────────────────────────────────
```

## Como executar com Docker

O projeto pode ser executado com Docker, permitindo rodar o simulador em um ambiente isolado, sem necessidade de configurar manualmente o Python na máquina local.

### Pré-requisitos

* Docker instalado;
* No Windows, recomenda-se utilizar o Docker Desktop com integração WSL2 habilitada.

### Construir a imagem Docker

Na raiz do projeto, execute:

```bash
docker build -t so-escalonador-g3 .
```

Esse comando cria a imagem Docker do projeto a partir do `Dockerfile`, incluindo o código-fonte e os arquivos de entrada necessários para a execução do simulador.

### Executar o simulador

Após construir a imagem, execute:

```bash
docker run --rm so-escalonador-g3
```

Esse comando executa o simulador dentro do container e exibe o log da simulação no terminal.

O simulador lê os processos definidos em:

```txt
input/processes.csv
```

E gera o log da execução em:

```txt
output/execution_log.txt
```

### Executar persistindo o log na máquina local

Como o container é removido ao final da execução pelo parâmetro `--rm`, o log gerado dentro do ambiente do container não necessariamente fica disponível na pasta local do projeto.

Para garantir que o arquivo `execution_log.txt` seja salvo na pasta `output` da máquina local, pode-se executar o container com montagem de volume.

No Linux, macOS ou WSL2:

```bash
docker run --rm -v "$(pwd)/output:/app/output" so-escalonador-g3
```

No Windows PowerShell:

```powershell
docker run --rm -v "${PWD}/output:/app/output" so-escalonador-g3
```

Nesse comando, a pasta `output` do projeto local é vinculada à pasta `/app/output` dentro do container. Assim, o log gerado pela aplicação é gravado diretamente no projeto local, permitindo consultar o arquivo após a finalização do container.

### Comandos principais para teste

Execução simples:

```bash
docker build -t so-escalonador-g3 .
docker run --rm so-escalonador-g3
```

Execução com persistência do log no Linux, macOS ou WSL2:

```bash
docker run --rm -v "$(pwd)/output:/app/output" so-escalonador-g3
```

Execução com persistência do log no Windows PowerShell:

```powershell
docker run --rm -v "${PWD}/output:/app/output" so-escalonador-g3
```
