import csv
import os

from pcb import PCB, IO_NONE
from io_manager import IOManager


class Scheduler:
    """
    Escalonador de Processos — Round Robin com Feedback e gerenciamento de I/O.

    Filas:
        queue_high  : processos de alta prioridade (novos e retornos privilegiados)
        queue_low   : processos de baixa prioridade (pós-preempção e retorno de disco)
        io_manager  : gerencia as filas de disco, fita e impressora separadamente

    Regras de feedback:
        Quantum expirado    → processo rebaixado para fila BAIXA
        Retorno de DISCO    → fila BAIXA
        Retorno de FITA     → fila ALTA
        Retorno de IMPRESSORA → fila ALTA
    """

    # Quantum por nível de prioridade
    QUANTUM_HIGH = 2
    QUANTUM_LOW  = 4

    def __init__(self, io_durations: dict = None):
        self.queue_high: list[PCB] = []   # Fila de alta prioridade
        self.queue_low:  list[PCB] = []   # Fila de baixa prioridade

        # IOManager encapsula as filas de disco, fita e impressora
        # e aplica as regras de retorno corretas a cada dispositivo
        self.io_manager = IOManager(durations=io_durations)

        self.running_process: PCB | None = None  # Processo atualmente na CPU
        self.current_quantum = 0                  # Ticks usados no quantum atual

        self.clock        = 0   # Relógio global da simulação (unidades de tempo)
        self.log_messages = []  # Histórico de eventos para salvar em arquivo

        # Métricas gerais
        self.idle_ticks        = 0   # Ticks em que a CPU ficou ociosa
        self.total_preemptions = 0   # Total de preempções por quantum expirado
        self.finished_processes: list[PCB] = []  # Processos finalizados

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------

    def _get_quantum(self, process: PCB) -> int:
        """Retorna o tamanho do quantum conforme a prioridade do processo."""
        return self.QUANTUM_HIGH if process.priority == "HIGH" else self.QUANTUM_LOW

    def log(self, message: str):
        """Registra e exibe um evento com timestamp."""
        msg = f"[t={self.clock:03d}] {message}"
        print(msg)
        self.log_messages.append(msg)

    # ------------------------------------------------------------------
    # Carregamento de processos
    # ------------------------------------------------------------------

    def load_processes_from_csv(self, filepath: str):
        """
        Lê o arquivo CSV e popula a fila de alta prioridade.

        Formato esperado do CSV:
            PID, PPID, TIME_REMAINING, IO_TYPE
            (IO_TYPE: 0=nenhum, 1=disco, 2=fita, 3=impressora)

        Todos os processos novos entram na fila ALTA conforme a política
        do algoritmo Round Robin com Feedback.
        """
        if not os.path.exists(filepath):
            self.log(f"ERRO: Arquivo '{filepath}' não encontrado.")
            return

        with open(filepath, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                pcb = PCB(
                    pid            = int(row['PID']),
                    ppid           = int(row['PPID']),
                    time_remaining = int(row['TIME_REMAINING']),
                    io_type        = int(row['IO_TYPE']),
                )
                pcb.status       = "READY"
                pcb.arrival_time = self.clock  # Momento de chegada do processo

                # Processos novos sempre entram na fila de alta prioridade
                self.queue_high.append(pcb)
                self.log(f"Processo criado — Fila ALTA: {pcb}")

    # ------------------------------------------------------------------
    # Etapas do loop principal
    # ------------------------------------------------------------------

    def _manage_io(self):
        """
        Avança um tick nas filas de I/O e reintegra processos que concluíram.

        Delega ao IOManager o controle dos contadores. O retorno segue a regra:
            DISCO      → fila BAIXA
            FITA       → fila ALTA
            IMPRESSORA → fila ALTA

        Chamado ANTES da troca de contexto para que processos liberados do I/O
        já estejam disponíveis para escalonamento no mesmo tick.
        """
        completed = self.io_manager.tick(self.clock)

        for pcb, destination_queue, device in completed:
            pcb.status = "READY"
            if destination_queue == "HIGH":
                self.queue_high.append(pcb)
                self.log(f"PID {pcb.pid} concluiu I/O [{device}] — retornou à Fila ALTA")
            else:
                self.queue_low.append(pcb)
                self.log(f"PID {pcb.pid} concluiu I/O [{device}] — retornou à Fila BAIXA")

    def _context_switch(self):
        """
        Seleciona o próximo processo para a CPU, se ela estiver livre.

        Política de seleção (FIFO dentro de cada fila):
            1. Fila ALTA tem prioridade absoluta sobre a fila BAIXA.
            2. Se ambas estiverem vazias, a CPU ficará ociosa.
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
            return  # Nenhum processo pronto; CPU ficará ociosa neste tick

        # Configura o quantum para o processo selecionado
        self.current_quantum = 0
        self.running_process.status = "RUNNING"

        # Registra o instante de início se for a primeira vez na CPU
        if self.running_process.start_time < 0:
            self.running_process.start_time = self.clock

        self.log(
            f"Troca de contexto — CPU para PID {self.running_process.pid} "
            f"(Fila: {self.running_process.priority} | "
            f"Quantum: {self._get_quantum(self.running_process)})"
        )

    def _execute_cpu(self):
        """
        Executa um tick de CPU e trata os eventos na seguinte ordem de prioridade:
            A) CPU ociosa (nenhum processo disponível)
            B) Processo finalizado (time_remaining chegou a zero)
            C) Bloqueio por I/O
            D) Preempção por quantum expirado
        """
        # Evento A: CPU ociosa
        if self.running_process is None:
            self.idle_ticks += 1
            self.log("CPU OCIOSA.")
            return

        quantum = self._get_quantum(self.running_process)

        # Executa um tick
        self.running_process.time_remaining -= 1
        self.current_quantum += 1

        self.log(
            f"Executando PID {self.running_process.pid} | "
            f"Resta: {self.running_process.time_remaining} | "
            f"Quantum: {self.current_quantum}/{quantum} | "
            f"I/O: {self.running_process.io_device}"
        )

        # Evento B: Processo finalizado
        if self.running_process.time_remaining <= 0:
            self._terminate_process(self.running_process)
            self.running_process = None
            return

        # Evento C: Solicitação de I/O
        # O processo possui dispositivo de I/O e ainda não solicitou neste ciclo
        if (
            self.running_process.io_device != IO_NONE
            and not self.running_process.io_requested
        ):
            self._block_for_io(self.running_process)
            self.running_process = None
            return

        # Evento D: Quantum expirado → preempção
        if self.current_quantum >= quantum:
            self._preempt_process(self.running_process)
            self.running_process = None

    def _increment_waiting_time(self):
        """
        Acumula tempo de espera para processos nas filas de CPU.
        Processos em I/O (status WAITING) não contam como tempo de espera de CPU.
        """
        for pcb in self.queue_high + self.queue_low:
            pcb.waiting_time += 1

    # ------------------------------------------------------------------
    # Eventos de processo
    # ------------------------------------------------------------------

    def _terminate_process(self, pcb: PCB):
        """Finaliza o processo: registra métricas e move para a lista de concluídos."""
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
        Delega ao IOManager, que define o tempo de espera e mantém a fila.
        """
        device  = pcb.io_device
        success = self.io_manager.request_io(pcb)

        if success:
            self.log(
                f"PID {pcb.pid} solicitou I/O [{device}] | "
                f"Bloqueado por {pcb.io_wait_time} ticks"
            )
        else:
            # Dispositivo inválido ou ausente: devolve à fila alta
            self.log(f"PID {pcb.pid}: solicitação de I/O inválida — devolvido à Fila ALTA.")
            pcb.status = "READY"
            self.queue_high.append(pcb)

    def _preempt_process(self, pcb: PCB):
        """
        Aplica a regra de feedback por quantum expirado:
            HIGH → rebaixado para LOW
            LOW  → permanece em LOW (Round Robin dentro da fila baixa)

        Em ambos os casos o processo vai para o FINAL da fila baixa.
        """
        pcb.status = "READY"
        pcb.preemptions += 1
        self.total_preemptions += 1

        if pcb.priority == "HIGH":
            # Penalizado: usou o quantum inteiro sem bloquear nem finalizar
            pcb.priority = "LOW"
            self.log(f"Quantum expirado. PID {pcb.pid} REBAIXADO → Fila BAIXA.")
        else:
            # Já estava em LOW: apenas rotaciona na fila
            self.log(f"Quantum expirado. PID {pcb.pid} retornou → Fila BAIXA.")

        self.queue_low.append(pcb)

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------

    def run(self):
        """
        Loop principal da simulação.

        A cada tick de tempo:
            1. Incrementa tempo de espera dos processos em fila
            2. Avança I/O e reintegra processos liberados
            3. Realiza troca de contexto se CPU estiver livre
            4. Executa um tick de CPU

        A simulação termina quando não há processos em nenhuma fila nem na CPU.
        """
        self.log("=" * 60)
        self.log("INICIANDO SIMULAÇÃO — Round Robin com Feedback + I/O")
        self.log(
            f"Quantum ALTA={self.QUANTUM_HIGH} | Quantum BAIXA={self.QUANTUM_LOW} | "
            f"Dispositivos: DISCO, FITA, IMPRESSORA"
        )
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
            self._increment_waiting_time()
            self._manage_io()
            self._context_switch()
            self._execute_cpu()

        # Encerramento
        self.log("=" * 60)
        self.log("FIM DA SIMULAÇÃO")
        self.log("=" * 60)

        self._print_metrics()
        self.save_log("output/execution_log.txt")

    # ------------------------------------------------------------------
    # Métricas e saída
    # ------------------------------------------------------------------

    def _print_metrics(self):
        """Exibe o relatório final com métricas agregadas e por processo."""
        total_time = self.clock
        n = len(self.finished_processes) or 1

        avg_turnaround = sum(p.turnaround    for p in self.finished_processes) / n
        avg_waiting    = sum(p.waiting_time  for p in self.finished_processes) / n
        cpu_idle_pct   = (self.idle_ticks / total_time * 100) if total_time > 0 else 0

        self.log("")
        self.log("──────────── MÉTRICAS FINAIS ────────────")
        self.log(f"Tempo total da simulação    : {total_time} ticks")
        self.log(f"Processos finalizados       : {len(self.finished_processes)}")
        self.log(f"Total de preempções         : {self.total_preemptions}")
        self.log(f"Eventos de I/O — DISCO      : {self.io_manager.stats.get('DISCO', 0)}")
        self.log(f"Eventos de I/O — FITA       : {self.io_manager.stats.get('FITA', 0)}")
        self.log(f"Eventos de I/O — IMPRESSORA : {self.io_manager.stats.get('IMPRESSORA', 0)}")
        self.log(f"Turnaround médio            : {avg_turnaround:.2f} ticks")
        self.log(f"Tempo médio de espera       : {avg_waiting:.2f} ticks")
        self.log(f"CPU ociosa                  : {cpu_idle_pct:.1f}%")
        self.log("─────────────────────────────────────────")

        # Tabela detalhada por processo
        self.log("")
        self.log("PID | Turnaround | Espera | Preempções | Eventos I/O | Dispositivo")
        self.log("-" * 65)
        for p in sorted(self.finished_processes, key=lambda x: x.pid):
            self.log(
                f"{p.pid:>3} | {p.turnaround:>10} | {p.waiting_time:>6} | "
                f"{p.preemptions:>10} | {p.io_events:>11} | {p.io_device}"
            )

    def save_log(self, filepath: str):
        """Salva todos os eventos da simulação em arquivo de texto."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            for line in self.log_messages:
                f.write(line + "\n")
        print(f"\nLog salvo em: {filepath}")