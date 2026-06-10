import csv
import os

from pcb import PCB, IO_TYPE_MAP, IO_NONE
from io_manager import IOManager


class Scheduler:
    """
    Escalonador de Processos com Round Robin + Feedback e módulo de I/O.

    Filas:
      - queue_high : processos de alta prioridade (novos e retornos privilegiados)
      - queue_low  : processos de baixa prioridade (pós-preempção e retorno de disco)
      - io_manager : gerencia as filas de disco, fita e impressora separadamente

    Regras de feedback:
      - Quantum expirado       - rebaixado para fila BAIXA (se estava em ALTA)
      - Retorno de DISCO       - fila BAIXA
      - Retorno de FITA        - fila ALTA
      - Retorno de IMPRESSORA  - fila ALTA
    """

    def __init__(self, quantum: int = 2, io_durations: dict = None):

        self.queue_high: list[PCB] = []   # Fila de alta prioridade
        self.queue_low:  list[PCB] = []   # Fila de baixa prioridade

        # IOManager encapsula as filas de disco, fita e impressora e aplica
        # as regras de retorno corretas a cada dispositivo.
        self.io_manager = IOManager(durations=io_durations)

        self.running_process: PCB | None = None  # Processo atualmente na CPU
        self.quantum         = quantum            # Tamanho do quantum
        self.current_quantum = 0                  # Ticks usados no quantum atual

        self.clock        = 0   # Unidade de tempo global da simulação
        self.log_messages = []  # Histórico de todos os eventos para salvar em arquivo

        self.idle_ticks        = 0   # Ticks em que a CPU ficou ociosa
        self.total_preemptions = 0   # Total de preempções por quantum expirado
        self.finished_processes: list[PCB] = []  # Processos finalizados (para turnaround)


    def log(self, message: str):
        """Registra uma mensagem com timestamp e exibe no terminal."""
        msg = f"[t={self.clock:03d}] {message}"
        print(msg)
        self.log_messages.append(msg)


    def load_processes_from_csv(self, filepath: str):
        """
        Lê o arquivo CSV de processos e popula a fila de alta prioridade.

        Todos os processos entram na fila de ALTA prioridade (regra: processos
        novos sempre iniciam em HIGH, conforme documentação).
        """
        if not os.path.exists(filepath):
            self.log(f"ERRO: Arquivo '{filepath}' não encontrado.")
            return

        with open(filepath, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                pcb = PCB(
                    pid           = int(row['PID']),
                    ppid          = int(row['PPID']),
                    time_remaining= int(row['TIME_REMAINING']),
                    io_type       = int(row['IO_TYPE']),
                )
                pcb.status       = "READY"
                pcb.arrival_time = self.clock  # Registra quando o processo chegou

                # Processos novos entram SEMPRE na fila de alta prioridade
                self.queue_high.append(pcb)
                self.log(f"Processo criado - Fila ALTA: {pcb}")


    def _manage_io(self):
        """
        Avança um tick nas filas de I/O e reintegra processos que concluíram.

        Delega ao IOManager o controle dos contadores e a aplicação das
        regras de retorno por dispositivo:
          - DISCO      - fila BAIXA
          - FITA       - fila ALTA
          - IMPRESSORA - fila ALTA

        Este método é chamado ANTES da troca de contexto para garantir que
        processos liberados do I/O já estejam disponíveis para escalonamento
        no mesmo tick.
        """
        # Avança o relógio interno do IOManager; recebe a lista de processos prontos
        completed = self.io_manager.tick(self.clock)

        for pcb, destination_queue, device in completed:
            # Direciona o processo para a fila determinada pela regra do dispositivo
            if destination_queue == "HIGH":
                self.queue_high.append(pcb)
                self.log(
                    f"PID {pcb.pid} concluiu I/O [{device}] - retornou à Fila ALTA"
                )
            else:  # "LOW"
                self.queue_low.append(pcb)
                self.log(
                    f"PID {pcb.pid} concluiu I/O [{device}] - retornou à Fila BAIXA"
                )


    def _context_switch(self):
        """
        Seleciona o próximo processo a receber a CPU, se ela estiver livre.

        Política de seleção (Round Robin com Feedback):
          1. Fila ALTA tem prioridade absoluta sobre a fila BAIXA.
          2. Dentro de cada fila, o critério é FIFO (primeiro a chegar).

        Não faz nada se já houver um processo em execução.
        """
        # CPU ocupada: nenhuma troca necessária
        if self.running_process is not None:
            return

        # Seleciona da fila de maior prioridade disponível
        if self.queue_high:
            self.running_process = self.queue_high.pop(0)
        elif self.queue_low:
            self.running_process = self.queue_low.pop(0)
        else:
            return  # Nenhum processo pronto; CPU ficará ociosa

        self.running_process.status = "RUNNING"
        self.current_quantum = 0  # Zera o contador de quantum para o novo processo

        # Registra o instante de início se for a primeira vez na CPU
        if self.running_process.start_time < 0:
            self.running_process.start_time = self.clock

        self.log(
            f"Troca de contexto - CPU para PID {self.running_process.pid} "
            f"(Fila: {self.running_process.priority})"
        )


    def _execute_cpu(self):
        """
        Executa um tick de CPU no processo em execução e trata os eventos:
          A) Processo finalizado (time_remaining = 0)
          B) Bloqueio por I/O (processo possui dispositivo e ainda não solicitou)
          C) Preempção por quantum expirado

        A ordem de verificação segue a prioridade lógica dos eventos:
        finalização > bloqueio por I/O > preempção.
        """
        # CPU ociosa: nenhum processo disponível
        if self.running_process is None:
            self.idle_ticks += 1
            self.log("CPU OCIOSA.")
            return

        # Executa um tick
        self.running_process.time_remaining -= 1
        self.current_quantum += 1

        self.log(
            f"Executando PID {self.running_process.pid} | "
            f"Resta: {self.running_process.time_remaining} | "
            f"Quantum: {self.current_quantum}/{self.quantum} | "
            f"I/O: {self.running_process.io_device}"
        )

        # Evento A: Processo finalizado
        if self.running_process.time_remaining <= 0:
            self._terminate_process(self.running_process)
            self.running_process = None
            return

        # Evento B: Solicitação de I/O
        # Critério: processo tem um dispositivo de I/O definido E ainda não
        # solicitou neste ciclo de execução.
        # O bloqueio acontece após o primeiro tick de CPU (quando o processo
        # "encontra" a operação de I/O durante sua execução).
        if (
            self.running_process.io_device != IO_NONE
            and not self.running_process.io_requested
        ):
            self._block_for_io(self.running_process)
            self.running_process = None
            return

        # Evento C: Quantum expirado — preempção
        if self.current_quantum >= self.quantum:
            self._preempt_process(self.running_process)
            self.running_process = None


    def _terminate_process(self, pcb: PCB):
        """
        Finaliza o processo: registra métricas e move para a lista de concluídos.
        """
        pcb.status      = "TERMINATED"
        pcb.finish_time = self.clock

        self.finished_processes.append(pcb)
        self.log(
            f"PID {pcb.pid} FINALIZADO | "
            f"Turnaround: {pcb.turnaround} | "
            f"Espera: {pcb.waiting_time} | "
            f"Preempções: {pcb.preemptions} | "
            f"Eventos de I/O: {pcb.io_events}"
        )

    def _block_for_io(self, pcb: PCB):
        """
        Bloqueia o processo por I/O, enviando-o para o dispositivo correto.

        Delega ao IOManager, que define o tempo de espera conforme o dispositivo
        e mantém o processo na fila adequada até a conclusão.
        """
        device = pcb.io_device

        # Tenta registrar o I/O no gerenciador
        success = self.io_manager.request_io(pcb)

        if success:
            self.log(
                f"PID {pcb.pid} solicitou I/O [{device}] | "
                f"Bloqueado por {pcb.io_wait_time} ticks"
            )
        else:
            # Caso io_device era NONE ou inválido; devolve à fila
            self.log(f"PID {pcb.pid}: solicitação de I/O inválida — devolvido à fila.")
            pcb.status = "READY"
            self.queue_high.append(pcb)

    def _preempt_process(self, pcb: PCB):
        """
        Aplica a regra de feedback por quantum expirado:
          - Se estava em HIGH - rebaixa para LOW
          - Se já estava em LOW - permanece em LOW

        Em ambos os casos o processo vai para o FINAL da fila de baixa prioridade,
        garantindo a alternância entre processos.
        """
        pcb.status = "READY"
        pcb.preemptions += 1
        self.total_preemptions += 1

        if pcb.priority == "HIGH":
            # processo usou o quantum inteiro sem bloquear/finalizar
            #penalizado com rebaixamento para fila de baixa prioridade
            pcb.priority = "LOW"
            self.log(
                f"Quantum expirado. PID {pcb.pid} REBAIXADO - Fila BAIXA."
            )
        else:
            # Já estava em LOW: Round Robin dentro da fila baixa
            self.log(
                f"Quantum expirado. PID {pcb.pid} retornou - Fila BAIXA."
            )

        self.queue_low.append(pcb)


    def run(self):
        """
        Loop principal da simulação.

        A cada tick de tempo:
          1. Avança I/O e reintegra processos liberados (com destino correto)
          2. Realiza troca de contexto se CPU livre
          3. Executa um tick de CPU (finalização / bloqueio I/O / preempção)

        A simulação termina quando não há processos em nenhuma fila nem na CPU.
        """
        self.log("=" * 60)
        self.log("INICIANDO SIMULAÇÃO — Round Robin com Feedback + I/O")
        self.log(f"Quantum: {self.quantum} | Dispositivos: DISCO, FITA, IMPRESSORA")
        self.log(
            f"Durações de I/O: "
            f"DISCO={self.io_manager.durations['DISCO']} | "
            f"FITA={self.io_manager.durations['FITA']} | "
            f"IMPRESSORA={self.io_manager.durations['IMPRESSORA']}"
        )
        self.log("=" * 60)

        # Condição de parada: nenhuma fila tem processos e CPU está livre
        while (
            self.queue_high
            or self.queue_low
            or not self.io_manager.is_empty()
            or self.running_process
        ):
            self.clock += 1

            # Incrementa tempo de espera dos processos em fila
            self._increment_waiting_time()

            # Etapa 1: avança I/O e reintegra processos liberados
            self._manage_io()

            # Etapa 2: seleciona próximo processo se CPU estiver livre
            self._context_switch()

            # Etapa 3: executa tick de CPU
            self._execute_cpu()

        # Encerramento
        self.log("=" * 60)
        self.log("FIM DA SIMULAÇÃO")
        self.log("=" * 60)

        self._print_metrics()
        self.save_log("output/execution_log.txt")


    def _increment_waiting_time(self):
        """
        Acumula tempo de espera para processos em fila.
        Chamado uma vez por tick, antes da troca de contexto.
        Processos em fila de I/O (WAITING) NÃO contam como tempo de espera de CPU.
        """
        for pcb in self.queue_high + self.queue_low:
            pcb.waiting_time += 1

    def _print_metrics(self):
        """
        Exibe o relatório final de métricas da simulação:
    
        """
        total_time = self.clock

        # Calcula médias
        n = len(self.finished_processes) or 1
        avg_turnaround = sum(p.turnaround for p in self.finished_processes) / n
        avg_waiting    = sum(p.waiting_time for p in self.finished_processes) / n
        cpu_idle_pct   = (self.idle_ticks / total_time * 100) if total_time > 0 else 0

        self.log("")
        self.log("──────────── MÉTRICAS FINAIS ────────────")
        self.log(f"Tempo total da simulação   : {total_time} ticks")
        self.log(f"Processos finalizados      : {len(self.finished_processes)}")
        self.log(f"Total de preempções        : {self.total_preemptions}")
        self.log(f"Eventos de I/O — DISCO     : {self.io_manager.stats.get('DISCO', 0)}")
        self.log(f"Eventos de I/O — FITA      : {self.io_manager.stats.get('FITA', 0)}")
        self.log(f"Eventos de I/O — IMPRESSORA: {self.io_manager.stats.get('IMPRESSORA', 0)}")
        self.log(f"Turnaround médio           : {avg_turnaround:.2f} ticks")
        self.log(f"Tempo médio de espera      : {avg_waiting:.2f} ticks")
        self.log(f"CPU ociosa                 : {cpu_idle_pct:.1f}%")
        self.log("─────────────────────────────────────────")

        # Tabela por processo
        self.log("")
        self.log("PID | Turnaround | Espera | Preempções | Eventos I/O | Dispositivo")
        self.log("-" * 65)
        for p in sorted(self.finished_processes, key=lambda x: x.pid):
            self.log(
                f"{p.pid:>3} | {p.turnaround:>10} | {p.waiting_time:>6} | "
                f"{p.preemptions:>10} | {p.io_events:>11} | {p.io_device}"
            )


    def save_log(self, filepath: str):
        """
        Salva todos os eventos da simulação em arquivo de texto.
        Cria o diretório de saída automaticamente se não existir.
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            for line in self.log_messages:
                f.write(line + "\n")
        print(f"\nLog salvo em: {filepath}")
