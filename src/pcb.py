class PCB:
    """Estrutura do Bloco de Controle de Processo (PCB)."""
    def __init__(self, pid: int, ppid: int, time_remaining: int, io_type: int):
        self.pid = pid
        self.ppid = ppid
        self.status = "NEW"
        self.priority = "HIGH"
        self.time_remaining = time_remaining
        self.io_type = io_type
        self.io_wait_time = 0

    def __str__(self):
        return f"[PID:{self.pid} | Status:{self.status} | Prioridade:{self.priority} | TempoRestante:{self.time_remaining}]"
