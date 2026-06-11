"""
Responsável por:
  1. Receber processos que solicitaram operações de I/O (disco, fita, impressora).
  2. Controlar o tempo de espera de cada dispositivo de forma independente.
  3. Liberar processos ao término do I/O e direcioná-los à fila correta,
       - DISCO      - fila de BAIXA prioridade
       - FITA       - fila de ALTA prioridade
       - IMPRESSORA - fila de ALTA prioridade
"""

from pcb import PCB, IO_DISCO, IO_FITA, IO_IMPRESSORA, IO_NONE


# Estes valores podem ser sobrescritos na instanciação do IOManager,
# permitindo configuração flexível conforme as premissas do grupo.
DEFAULT_IO_DURATION = {
    IO_DISCO:      4,   # Disco: operação mais lenta, penaliza com rebaixamento
    IO_FITA:       6,   # Fita magnética: mais lenta ainda, mas recompensa com alta prioridade
    IO_IMPRESSORA: 3,   # Impressora: duração intermediária, recompensa com alta prioridade
}

# Regra de retorno: define para qual fila cada dispositivo devolve o processo
# "HIGH" = fila de alta prioridade "LOW" = fila de baixa prioridade
IO_RETURN_QUEUE = {
    IO_DISCO:      "LOW",   # Disco: processo volta à fila baixa (operação penalizante)
    IO_FITA:       "HIGH",  # Fita: processo volta à fila alta (prioridade restaurada)
    IO_IMPRESSORA: "HIGH",  # Impressora: processo volta à fila alta (prioridade restaurada)
}


class IOManager:
    """
    Gerenciador de I/O com filas separadas por dispositivo.
    Mantém três filas independentes (disco, fita, impressora),
    decrementando o contador de espera de cada processo a cada tick
    e retornando-os à fila correta quando o I/O conclui.
    """

    def __init__(self, durations: dict = None):

        # Mescla os padrões com quaisquer valores customizados recebidos.
        # Isso garante que premissas do grupo possam ser definidas no Scheduler
        # sem alterar este arquivo.
        self.durations = {**DEFAULT_IO_DURATION, **(durations or {})}

        # Filas de I/O — uma por dispositivo
        # Permite logs mais detalhados e controle independente de cada fila.
        self.queue_disco:      list[PCB] = []
        self.queue_fita:       list[PCB] = []
        self.queue_impressora: list[PCB] = []

        # Acumulador de estatísticas — quantos eventos de I/O ocorreram por dispositivo
        self.stats = {
            IO_DISCO:      0,
            IO_FITA:       0,
            IO_IMPRESSORA: 0,
        }

    def request_io(self, pcb: PCB) -> bool:
        """
        Registra uma solicitação de I/O para o processo `pcb`.

        O dispositivo é determinado pelo atributo `pcb.io_device`.
        Se o processo não tiver I/O pendente (IO_NONE), retorna False
        e o processo não é bloqueado.

        Retorna True se o processo foi bloqueado com sucesso.
        """
        device = pcb.io_device

        # Processo sem I/O definido: não bloqueia
        if device == IO_NONE:
            return False

        # Define o tempo de espera conforme o dispositivo
        pcb.io_wait_time = self.durations[device]
        pcb.status = "WAITING"
        pcb.io_requested = True  # Marca que o I/O foi solicitado (evita reentrada)
        pcb.io_events += 1        # Contabiliza o evento nas métricas do processo

        # Encaminha para a fila do dispositivo correto
        self._get_queue(device).append(pcb)

        # Atualiza estatística global do gerenciador
        self.stats[device] += 1

        return True

    def tick(self, clock: int) -> list[tuple[PCB, str]]:
        """
        Avança um tick de tempo em todas as filas de I/O.

        Para cada processo aguardando I/O, decrementa seu contador.
        Quando o contador chega a zero, o processo está pronto para retornar
        ao escalonador.

        Parâmetros
        clock : int
            Instante atual da simulação.

        Retorna
        list[tuple[PCB, str]]
            Lista de tuplas (processo, fila_destino) para cada processo
            que concluiu seu I/O neste tick.
            fila_destino é "HIGH" ou "LOW" conforme IO_RETURN_QUEUE.
        """
        completed = []  # Processos que terminaram o I/O neste tick

        # Itera sobre cada dispositivo e sua fila correspondente
        for device in (IO_DISCO, IO_FITA, IO_IMPRESSORA):
            queue = self._get_queue(device)

            # Usa list() para criar cópia: podemos remover itens durante a iteração
            for pcb in list(queue):
                pcb.io_wait_time -= 1  # Decrementa o contador regressivo

                if pcb.io_wait_time <= 0:
                    # I/O concluído: remove da fila de espera
                    queue.remove(pcb)

                    # Atualiza estado do processo
                    pcb.status = "READY"

                    # Determina para qual fila o processo deve retornar
                    # conforme a regra do dispositivo
                    destination_queue = IO_RETURN_QUEUE[device]
                    pcb.priority = destination_queue  # Sincroniza prioridade com destino

                    completed.append((pcb, destination_queue, device))

        return completed

    def is_empty(self) -> bool:
        """Retorna True se não há nenhum processo aguardando I/O."""
        return (
            len(self.queue_disco) == 0
            and len(self.queue_fita) == 0
            and len(self.queue_impressora) == 0
        )

    def total_waiting(self) -> int:
        """Retorna o total de processos atualmente bloqueados por I/O."""
        return (
            len(self.queue_disco)
            + len(self.queue_fita)
            + len(self.queue_impressora)
        )

    def snapshot(self) -> dict:
        """
        Retorna um dicionário com o estado atual de todas as filas.
        Útil para logging detalhado no loop principal.
        """
        return {
            IO_DISCO:      [(p.pid, p.io_wait_time) for p in self.queue_disco],
            IO_FITA:       [(p.pid, p.io_wait_time) for p in self.queue_fita],
            IO_IMPRESSORA: [(p.pid, p.io_wait_time) for p in self.queue_impressora],
        }

    def _get_queue(self, device: str) -> list:
        """
        Retorna a fila interna correspondente ao dispositivo informado.
        Centraliza o mapeamento device-fila para evitar repetição de if/elif.
        """
        if device == IO_DISCO:
            return self.queue_disco
        elif device == IO_FITA:
            return self.queue_fita
        elif device == IO_IMPRESSORA:
            return self.queue_impressora
        else:
            # Dispositivo desconhecido: nunca deve ocorrer se o CSV for válido
            raise ValueError(f"Dispositivo de I/O desconhecido: '{device}'")