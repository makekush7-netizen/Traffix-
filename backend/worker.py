"""Single adapter owner. HTTP handlers submit commands, never access the adapter."""
import queue
import secrets
import threading
from concurrent.futures import Future


class SimulationWorker:
    def __init__(self, adapter_factory, tick_wall_s=1):
        self.run_id = 'run.' + secrets.token_hex(8)
        self._factory = adapter_factory
        self._queue = queue.Queue(maxsize=1024)
        self._thread = None
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._outcomes = {}
        self.sim_time_s = 0
        self.paused = True
        self.rate = 1
        self.tick_wall_s = tick_wall_s
        self.failure = None

    def start(self):
        if self._thread is not None:
            raise RuntimeError('worker_already_started')
        self._thread = threading.Thread(target=self._run, name='traffix-simulation-owner', daemon=True)
        self._thread.start()
        if not self._ready.wait(10):
            raise RuntimeError('adapter_start_timeout')
        if self.failure:
            raise RuntimeError('adapter_start_failed') from self.failure

    def submit(self, command_id, command):
        future = Future()
        if not self._thread or not self._thread.is_alive() or self._stop.is_set():
            future.set_exception(RuntimeError('worker_unavailable'))
            return future
        try:
            self._queue.put_nowait((command_id, command, future))
        except queue.Full:
            future.set_exception(RuntimeError('command_queue_full'))
        return future

    def _run(self):
        adapter = None
        try:
            adapter = self._factory()
            self._ready.set()
            while not self._stop.is_set():
                try:
                    command_id, command, future = self._queue.get(timeout=self.tick_wall_s / self.rate)
                except queue.Empty:
                    if not self.paused:
                        self.sim_time_s = adapter.step()
                    continue
                if future.cancelled():
                    continue
                if command_id in self._outcomes:
                    result, error = self._outcomes[command_id]
                else:
                    error = None
                    try:
                        if command == 'pause':
                            self.paused = True
                        elif command == 'resume':
                            self.paused = False
                        elif isinstance(command, dict) and command.get('action') == 'set_rate':
                            if command.get('rate') not in (1, 4, 8):
                                raise ValueError('invalid_rate')
                            self.rate = command['rate']
                        else:
                            adapter.execute(command)
                        result = dict(status='applied', command_id=command_id, sim_time_s=self.sim_time_s)
                    except Exception as exc:
                        result, error = None, exc
                    self._outcomes[command_id] = (result, error)
                if error:
                    future.set_exception(error)
                else:
                    future.set_result(result)
        except Exception as exc:
            self.failure = exc
        finally:
            self._ready.set()
            if adapter is not None:
                try:
                    adapter.close()
                except Exception as exc:
                    self.failure = self.failure or exc
            while not self._queue.empty():
                _, _, future = self._queue.get_nowait()
                if not future.done():
                    future.set_exception(RuntimeError('worker_stopped'))

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                raise RuntimeError('worker_stop_timeout')
