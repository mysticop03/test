"""
core/batch_orchestrator.py
Store-wise concurrency orchestrator.
Batches audits store-by-store (e.g. 2 stores at a time = ~20-26 tills concurrently)
to protect retail store WAN connections and office Wi-Fi routers.
Dispatches thread-safe events into a Queue for reactive 60fps UI updates.
"""
import time
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Optional
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
        store_concurrency: int = 2,
        max_workers_per_store: int = 16,
        timeout: int = 5,
        event_callback: Optional[Callable[[str, Any], None]] = None
    ):
        self.username = username
        self.password = password
        self.operation_mode = operation_mode
        self.config_params = config_params
        self.store_concurrency = max(1, store_concurrency)
        self.max_workers_per_store = max(1, max_workers_per_store)
        self.timeout = timeout
        self.event_callback = event_callback

        self.event_queue: queue.Queue = queue.Queue()
        self.stop_requested = threading.Event()
        self.pause_requested = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        self.summary = AuditSummary()
        self.all_results: List[AuditResult] = []

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
        self.post_event("stopped", True)

    def is_running(self) -> bool:
        return self._worker_thread is not None and self._worker_thread.is_alive()

    def start_async(self, stores: List[StoreRecord], specific_tills_str: str = ""):
        """Start batch audit in background thread."""
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

        # Expand all targets upfront to know total till count
        all_targets: List[TillTarget] = []
        store_targets_map: Dict[str, List[TillTarget]] = {}
        for s in stores:
            t_list = s.resolve_targets(specific_tills_str)
            store_targets_map[s.store_code] = t_list
            all_targets.extend(t_list)

        self.summary.total_tills = len(all_targets)
        self.post_event("target_summary", {"total_tills": len(all_targets)})

        # Batch stores in chunks of store_concurrency (e.g. 2 stores per batch)
        total_stores = len(stores)
        for i in range(0, total_stores, self.store_concurrency):
            if self.stop_requested.is_set():
                break

            batch_stores = stores[i : i + self.store_concurrency]
            batch_targets: List[TillTarget] = []
            for s in batch_stores:
                batch_targets.extend(store_targets_map.get(s.store_code, []))

            self.post_event("store_batch_start", {
                "batch_index": (i // self.store_concurrency) + 1,
                "stores": [s.store_code for s in batch_stores],
                "till_count": len(batch_targets)
            })

            # Execute tills in this store batch concurrently
            self._execute_target_batch(batch_targets)

            if self.stop_requested.is_set():
                break

        self.summary.elapsed_seconds = round(time.perf_counter() - start_clock, 1)
        self.post_event("completed", {
            "summary": self.summary,
            "results": self.all_results
        })

    def _execute_target_batch(self, targets: List[TillTarget]):
        if not targets:
            return

        concurrency = min(len(targets), self.store_concurrency * self.max_workers_per_store)
        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
            future_to_target = {
                executor.submit(
                    execute_till_probe,
                    t,
                    self.username,
                    self.password,
                    self.operation_mode,
                    self.config_params,
                    self.timeout
                ): t for t in targets
            }

            for future in as_completed(future_to_target):
                if self.stop_requested.is_set():
                    break
                while self.pause_requested.is_set() and not self.stop_requested.is_set():
                    time.sleep(0.2)

                try:
                    result: AuditResult = future.result()
                    self._record_result(result)
                except Exception as e:
                    t = future_to_target[future]
                    err_res = AuditResult(
                        store_code=t.store_code,
                        till_name=t.till_name,
                        till_num=t.till_num,
                        ip=t.ip,
                        store_order_index=t.store_order_index,
                        operation_mode=self.operation_mode,
                        status=AuditStatus.ERROR,
                        preview_output=f"Worker exception: {e}",
                        full_output=str(e)
                    )
                    self._record_result(err_res)

    def _record_result(self, result: AuditResult):
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
