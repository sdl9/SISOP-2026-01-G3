"""
Premissas do escalonador:
  - Quantum de fila ALTA       : 2 ticks
  - Quantum de fila BAIXA      : 4 ticks
  - Número máximo de processos : definido pelo CSV de entrada
  - Faixa de tempo de CPU      : 4–12 ticks (a definir no gerador de CSV)
  - Duração de I/O — DISCO     : 4 ticks - retorna à fila BAIXA
  - Duração de I/O — FITA      : 6 ticks - retorna à fila ALTA
  - Duração de I/O — IMPRESSORA: 3 ticks - retorna à fila ALTA
  - Critério de finalização    : filas de CPU e I/O vazias e CPU livre
  - Semente aleatória          : N/A (processos definidos em CSV)
"""

import os
import sys

# Garante que o diretório src/ esteja no path quando main.py
# for executado a partir da raiz do projeto
sys.path.insert(0, os.path.dirname(__file__))

from scheduler import Scheduler


# Duração (em ticks) de cada dispositivo de I/O.
# O quantum é definido no Scheduler conforme a prioridade da fila:
# Fila ALTA = 2 ticks | Fila BAIXA = 4 ticks
#
# Regras de retorno são definidas no io_manager.py:
# DISCO retorna à fila BAIXA
# FITA e IMPRESSORA retornam à fila ALTA
IO_DURATIONS = {
    "DISCO": 4,
    "FITA": 6,
    "IMPRESSORA": 3,
}

# Caminho para o arquivo CSV com os processos a escalonar
INPUT_FILE = os.path.join("input", "processes.csv")


def main():
    """Inicializa e executa o escalonador."""

    sched = Scheduler(io_durations=IO_DURATIONS)
    sched.load_processes_from_csv(INPUT_FILE)
    sched.run()


if __name__ == "__main__":
    main()