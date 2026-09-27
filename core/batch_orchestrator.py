"""
core/batch_orchestrator.py
Dynamic Sliding Window Store Concurrency Orchestrator.
Maintains up to N active stores concurrently (default: 5 stores from frontend bulk mode).
Enforces a hard ceiling of max 100 simultaneous till SSH connections globally across all stores.
When stores finish, new stores are immediately admitted without waiting for stragglers.
Dispatches thread-safe events into a Queue for reactive UI updates.
"""
import time
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Callable, Optional, Set
from models.target import StoreRecord, TillTarget
from models.result import AuditResult, AuditSummary, AuditStatus
from core.ssh_worker import execute_till_probe

class BatchOrchestrator:
    def __init__(
        self,
        username: str,
        password: str,
        operation_mode: str,
        config_params: Dict[str, Any],
        store_concurrency: int = 5,
        max_workers_per_store: int = 16,
        max_total_ssh_connections: int = 100,
        timeout: int = 5,
        event_callback: Optional[Callable[[str, Any], None]] = None
    ):
        self.username = username
        self.password = password
        self.operation_mode = operation_mode
        self.config_params = config_params
        self.store_concurrency = max(1, store_concurrency)
        self.max_workers_per_store = max(1, max_workers_per_store)
        self.max_total_ssh_connections = max(10, max_total_ssh_connections)
        self.timeout = timeout
        self.event_callback = event_callback

        self.event_queue: queue.Queue = queue.Queue()
        self.stop_requested = threading.Event()
        self.pause_requested = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        self.summary = AuditSummary()
        self.all_results: List[AuditResult] = []
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self.active_stores: Dict[str, int] = {}
        self.active_connections: int = 0

    def post_event(self, event_type: str, data: Any):
        """Put event in queue and invoke callback if registered."""
        self.event_queue.put((event_type, data))
        if self.event_callback:
            try:
                self.event_callback(event_type, data)
            except Exception:
                pass

    def pause(self):
        self.pause_requested.set()
        self.post_event("paused", True)

    def resume(self):
        self.pause_requested.clear()
        self.post_event("resumed", True)

    def stop(self):
        self.stop_requested.set()
        self.pause_requested.clear()
        with self._cond:
            self._cond.notify_all()
        self.post_event("stopped", True)

    def is_running(self) -> bool:
        return self._worker_thread is not None and self._worker_thread.is_alive()

    def start_async(self, stores: List[StoreRecord], specific_tills_str: str = ""):
        """Start dynamic sliding window batch audit in background thread."""
        if self.is_running():
            return
        self.stop_requested.clear()
        self.pause_requested.clear()
        self._worker_thread = threading.Thread(
            target=self._run_orchestration,
            args=(stores, specific_tills_str),
            daemon=True
        )
        self._worker_thread.start()

    def _run_orchestration(self, stores: List[StoreRecord], specific_tills_str: str):
        start_clock = time.perf_counter()
        self.post_event("started", {"store_count": len(stores)})

        # Expand all targets upfront to compute total till count
        all_targets: List[TillTarget] = []
        store_targets_map: Dict[str, List[TillTarget]] = {}
        for s in stores:
            t_list = s.resolve_targets(specific_tills_str)
            store_targets_map[s.store_code] = t_list
            all_targets.extend(t_list)

        self.summary.total_tills = len(all_targets)
        self.post_event("target_summary", {"total_tills": len(all_targets)})

        # Pending stores queue to schedule
        pending_stores = list(stores)
        with self._cond:
            self.active_stores.clear()
            self.active_connections = 0

        # Global executor capped at max 100 simultaneous SSH connections
        executor_cap = min(self.max_total_ssh_connections, max(10, self.store_concurrency * self.max_workers_per_store))
        executor = ThreadPoolExecutor(max_workers=executor_cap)

        try:
            while not self.stop_requested.is_set():
                while self.pause_requested.is_set() and not self.stop_requested.is_set():
                    time.sleep(0.2)

                with self._cond:
                    # Dynamic sliding window admission:
                    # Keep active stores filled up to store_concurrency (default 5),
                    # as long as total active SSH connections do not exceed 100!
                    while pending_stores and len(self.active_stores) < self.store_concurrency:
                        next_store = pending_stores[0]
                        needed_tills = store_targets_map.get(next_store.store_code, [])
                        needed_conns = len(needed_tills)

                        # Enforce connection budget (if no stores running, admit at least 1)
                        if self.active_connections + needed_conns <= self.max_total_ssh_connections or len(self.active_stores) == 0:
                            pending_stores.pop(0)
                            self.active_stores[next_store.store_code] = needed_conns
                            self.active_connections += needed_conns

                            self.post_event("store_admitted", {
                                "store_code": next_store.store_code,
                                "till_count": needed_conns,
                                "active_stores": len(self.active_stores),
                                "active_connections": self.active_connections
                            })

                            # Submit all tills of this admitted store to executor
                            for target in needed_tills:
                                executor.submit(
                                    self._worker_execute_till,
                                    target,
                                    next_store.store_code
                                )
                        else:
                            # Admitting next store would exceed the 100 connection ceiling.
                            # Hold this store until running tills finish!
                            break

                    # If all stores have been processed and no active tills remain, we are done!
                    if not pending_stores and len(self.active_stores) == 0:
                        break

                    # Wait for a till to complete before evaluating next admission
                    self._cond.wait(timeout=0.3)

        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        self.summary.elapsed_seconds = round(time.perf_counter() - start_clock, 1)
        self.post_event("completed", {
            "summary": self.summary,
            "results": self.all_results
        })

    def _worker_execute_till(self, target: TillTarget, store_code: str):
        """Worker thread for one till. Runs SSH probe and notifies condition variable on finish."""
        try:
            if self.stop_requested.is_set():
                return
            while self.pause_requested.is_set() and not self.stop_requested.is_set():
                time.sleep(0.2)

            res = execute_till_probe(
                target=target,
                username=self.username,
                password=self.password,
                operation_mode=self.operation_mode,
                config_params=self.config_params,
                timeout=self.timeout
            )
            self._record_result(res)
        except Exception as e:
            err_res = AuditResult(
                store_code=target.store_code,
                till_name=target.till_name,
                till_num=target.till_num,
                ip=target.ip,
                store_order_index=target.store_order_index,
                operation_mode=self.operation_mode,
                status=AuditStatus.ERROR,
                preview_output=f"Worker exception: {e}",
                full_output=str(e)
            )
            self._record_result(err_res)
        finally:
            with self._cond:
                self.active_connections = max(0, self.active_connections - 1)
                if store_code in self.active_stores:
                    self.active_stores[store_code] -= 1
                    if self.active_stores[store_code] <= 0:
                        del self.active_stores[store_code]
                self._cond.notify_all()

    def _record_result(self, result: AuditResult):
        with self._lock:
            self.all_results.append(result)
            self.summary.completed_tills += 1

            if result.status == AuditStatus.SUCCESS:
                self.summary.success_count += 1
            elif result.status == AuditStatus.SIZE_MISMATCH:
                self.summary.size_mismatch_count += 1
            elif result.status == AuditStatus.VERSION_MISMATCH:
                self.summary.version_mismatch_count += 1
            elif result.status == AuditStatus.BOTH_MISMATCH:
                self.summary.both_mismatch_count += 1
            elif result.status == AuditStatus.FILE_MISSING:
                self.summary.missing_count += 1
            elif result.status in (AuditStatus.OFFLINE, AuditStatus.TIMEOUT):
                self.summary.offline_count += 1
            else:
                self.summary.error_count += 1

        self.post_event("result", result)
