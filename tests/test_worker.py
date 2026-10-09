import threading

from backend.worker import SimulationWorker


class Adapter:
    def __init__(self):
        self.calls = []

    def step(self):
        self.calls.append(('step', threading.get_ident()))
        return len([c for c in self.calls if c[0] == 'step'])

    def execute(self, command):
        self.calls.append((command, threading.get_ident()))

    def close(self):
        self.calls.append(('close', threading.get_ident()))


def test_one_writer_order_pause_and_idempotency():
    adapter = Adapter()
    worker = SimulationWorker(lambda: adapter)
    worker.start()
    try:
        worker.submit('pause', 'pause').result(2)
        frozen = worker.sim_time_s
        worker.submit('a', 'extend_green').result(2)
        worker.submit('a', 'extend_green').result(2)
        worker.submit('b', 'reroute').result(2)
        assert worker.sim_time_s == frozen
        assert [c[0] for c in adapter.calls if c[0] != 'step'] == ['extend_green', 'reroute']
        worker.submit('resume', 'resume').result(2)
    finally:
        worker.stop()
    assert len({c[1] for c in adapter.calls}) == 1
    assert adapter.calls[0][1] != threading.get_ident()
    assert SimulationWorker(lambda: Adapter()).run_id != worker.run_id
