# Trabalho Final de Sistemas Operacionais

## Grupo
- Aluno 1: Fernando
- Aluno 2: Arthur
- Aluno 3: Matheus
- Aluno 4: Guilherme
- Aluno 5: Laíssa Salles
- Aluno 6: Nicolas

## Sobre o projeto
Simulador de escalonamento de processos com algoritmo Round Robin com Feedback,
desenvolvido como trabalho final da disciplina de Sistemas Operacionais — Feevale 2026/01.

O simulador implementa:
- Filas de alta e baixa prioridade
- Fila de I/O com disco, fita magnética e impressora
- Retorno dos processos às filas corretas após cada dispositivo de I/O
- Logs de evolução a cada evento relevante
- Métricas finais: turnaround, tempo de espera, preempções e CPU ociosa

## Linguagem utilizada
Python 3.x

## Convenção de código
Todo o código deve ser comentado. Cada função, bloco lógico e decisão
relevante deve ter um comentário explicando o que faz e por quê.
Isso facilita a leitura e revisão por todos os membros do grupo.

## Premissas do escalonador
- Quantum: (a definir)
- Número máximo de processos: (a definir)
- Faixa de tempo de serviço de CPU: (a definir)
- Faixa de tempo de I/O: (a definir)
- Duração de disco: (a definir) | fita: (a definir) | impressora: (a definir)
- Critério de geração dos processos: (a definir)
- Critério de finalização da simulação: (a definir)
- Semente aleatória: (a definir)

## Estrutura do repositório
SISOP-2026-01-G3/
├── src/          # Código-fonte do simulador
├── input/        # Arquivos de entrada com os processos
├── output/       # Saída gerada pelo simulador
├── docs/         # Relatório e documentação
├── Dockerfile
├── .dockerignore
└── README.md

> As pastas contêm um arquivo `.gitkeep` apenas para que o Git rastreie
> pastas vazias. O Git não versiona pastas sem arquivos, então o `.gitkeep`
> serve como placeholder e pode ser removido quando arquivos reais forem
> adicionados.
> Este README será atualizado conforme o progresso do trabalho.

## Fluxo de trabalho com Git

Cada membro deve criar uma branch própria antes de começar a codar.
Isso evita conflito de código entre as pessoas e mantém a main organizada.

```bash
# Clone o repositório (se ainda não fez)
git clone https://github.com/sdl9/SISOP-2026-01-G3.git
cd SISOP-2026-01-G3

# Crie sua branch com seu nome
git checkout -b nome-da-pessoa

# Trabalhe normalmente e faça commits na sua branch
git add .
git commit -m "descrição do que fez"
git push origin nome-da-pessoa
```

Quando uma parte estiver pronta, a junção com a main será feita em conjunto
para evitar conflitos.