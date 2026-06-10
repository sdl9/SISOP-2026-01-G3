# Constantes para os tipos de I/O disponíveis no simulador.
# Usamos strings para facilitar leitura nos logs.
IO_NONE      = "NENHUM"
IO_DISCO     = "DISCO"
IO_FITA      = "FITA"
IO_IMPRESSORA = "IMPRESSORA"

# Mapeamento de código numérico (lido do CSV) para nome do dispositivo.
# Isso mantém compatibilidade com o CSV existente (coluna IO_TYPE inteiro).
IO_TYPE_MAP = {
    0: IO_NONE,
    1: IO_DISCO,
    2: IO_FITA,
    3: IO_IMPRESSORA,
}


class PCB:
    """
    Armazena o estado completo de um processo, incluindo identidade,
    estado de execução, informações de I/O e métricas de desempenho
    (turnaround, tempo de espera, etc.).
    """

    def __init__(self, pid: int, ppid: int, time_remaining: int, io_type: int):
        self.pid  = pid   # Identificador único do processo
        self.ppid = ppid  # PID do processo pai (0 = processo raiz)

        self.status   = "NEW" # Status possíveis: NEW, READY, RUNNING, WAITING, TERMINATED
        self.priority = "HIGH" # Prioridade controla em qual fila o processo está: HIGH ou LOW

        self.time_remaining = time_remaining  # Unidades de CPU ainda necessárias
        self.time_total_cpu = time_remaining  # Cópia imutável (usada em métricas)

        # Converte o código inteiro do CSV para o nome legível do dispositivo.
        # Ex.: io_type=1 → "DISCO", io_type=2 → "FITA", io_type=3 → "IMPRESSORA"
        self.io_device   = IO_TYPE_MAP.get(io_type, IO_NONE)
        self.io_wait_time = 0  # Contador regressivo: quanto falta para concluir o I/O atual

        # Flag que indica se o I/O já foi solicitado neste ciclo de execução.
        # Impede que o mesmo processo solicite I/O duas vezes sem executar CPU.
        self.io_requested = False

        self.arrival_time      = 0   # Instante em que o processo entrou no sistema
        self.start_time        = -1  # Instante em que recebeu CPU pela primeira vez
        self.finish_time       = -1  # Instante em que foi finalizado
        self.waiting_time      = 0   # Acumulador: ticks esperando em fila (não em CPU)
        self.preemptions       = 0   # Contador de preempções por quantum expirado
        self.io_events         = 0   # Total de eventos de I/O realizados


    @property
    def turnaround(self) -> int:
        """
        Tempo de turnaround = finish_time − arrival_time.
        Só faz sentido após o processo ser TERMINADO.
        """
        if self.finish_time < 0:
            return -1
        return self.finish_time - self.arrival_time


    def __str__(self) -> str:
        return (
            f"[PID:{self.pid} | Status:{self.status} | "
            f"Prioridade:{self.priority} | TempoRestante:{self.time_remaining} | "
            f"I/O:{self.io_device}]"
        )
