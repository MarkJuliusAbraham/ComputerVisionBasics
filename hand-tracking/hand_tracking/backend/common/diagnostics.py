"""Owned runtime logging and thread dumps for intermittent application hangs."""

from __future__ import annotations

import faulthandler
import logging
import math
import os
import sys
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType
from typing import Callable, TextIO

from hand_tracking.backend.common.project_paths import PROJECT_ROOT


LOGGER = logging.getLogger(__name__)


class RuntimeDiagnostics:
    """Keep diagnostic files and a UI-heartbeat watchdog alive for one runtime.

    Call ``heartbeat`` from a recurring UI timer. The watchdog
    stays unarmed until the first heartbeat and writes one stack dump per stall;
    a subsequent heartbeat arms it again. It never calls Tk or native UI APIs.
    """

    def __init__(
        self,
        log_directory: Path | None = None,
        *,
        stall_timeout_seconds: float = 10.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not math.isfinite(stall_timeout_seconds) or stall_timeout_seconds <= 0:
            raise ValueError("The stall timeout must be positive and finite.")
        self.log_directory = Path(log_directory) if log_directory is not None else PROJECT_ROOT / "logs"
        self._stall_timeout = stall_timeout_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._last_heartbeat: float | None = None
        self._reported_stall = False
        self._watchdog: threading.Thread | None = None
        self._handler: RotatingFileHandler | None = None
        self._dump_file: TextIO | None = None
        self._owns_faulthandler = False
        self._previous_sys_hook = None
        self._previous_thread_hook = None
        self._previous_log_level: int | None = None
        self._identity = ""

    def __enter__(self) -> RuntimeDiagnostics:
        if self._watchdog is not None:
            raise RuntimeError("Runtime diagnostics are already running.")
        self._identity = (
            f"PID {os.getpid()}; UI thread {threading.get_ident():#x}; "
            f"native thread {threading.get_native_id()}"
        )
        self._open_files()
        self._previous_sys_hook = sys.excepthook
        self._previous_thread_hook = threading.excepthook
        sys.excepthook = self._report_exception
        threading.excepthook = self._report_thread_exception
        self._stop.clear()
        self._watchdog = threading.Thread(
            target=self._watch_heartbeat, name="runtime-diagnostics", daemon=True,
        )
        try:
            self._watchdog.start()
        except Exception:
            self.close()
            raise
        LOGGER.info("Runtime diagnostics started (%s); logs: %s", self._identity, self.log_directory)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is not None and not issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            LOGGER.critical("Application exited unexpectedly", exc_info=(exc_type, exc_value, traceback))
        self.close()

    def heartbeat(self) -> None:
        """Mark fresh UI progress; this performs no file or native UI work."""
        with self._lock:
            self._last_heartbeat = self._clock()
            recovered = self._reported_stall
            self._reported_stall = False
        if recovered:
            LOGGER.info("UI heartbeat resumed after a stall")

    def close(self) -> None:
        """Stop the watchdog and restore only the global resources we installed."""
        self._stop.set()
        watchdog = self._watchdog
        if watchdog is None:
            return
        if watchdog.ident is not None:
            watchdog.join(timeout=1.0)
        watchdog_alive = watchdog.is_alive()
        # A blocked daemon may own the logging handler's lock or dump fd.
        # Detach its handler below, but leave both files owned by the daemon:
        # logging or closing either here could turn bounded shutdown into a hang.
        if sys.excepthook == self._report_exception:
            sys.excepthook = self._previous_sys_hook
        if threading.excepthook == self._report_thread_exception:
            threading.excepthook = self._previous_thread_hook
        if self._owns_faulthandler:
            faulthandler.disable()
            self._owns_faulthandler = False
        if not watchdog_alive and self._dump_file is not None:
            self._dump_file.close()
            self._dump_file = None
        handler = self._handler
        if handler is not None:
            root = logging.getLogger()
            root.removeHandler(handler)
            if not watchdog_alive:
                handler.close()
                self._handler = None
            if self._previous_log_level is not None:
                root.setLevel(self._previous_log_level)
        if not watchdog_alive:
            self._watchdog = None
        with self._lock:
            self._last_heartbeat = None
            self._reported_stall = False

    def _open_files(self) -> None:
        try:
            self.log_directory.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(
                self.log_directory / "application.log", maxBytes=2_000_000,
                backupCount=3, encoding="utf-8",
            )
            handler.setLevel(logging.INFO)
            handler.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s",
            ))
            root = logging.getLogger()
            self._previous_log_level = root.level
            root.setLevel(min(root.level, logging.INFO))
            root.addHandler(handler)
            self._handler = handler
        except OSError:
            LOGGER.warning("Could not create the application log", exc_info=True)
        try:
            self._dump_file = (self.log_directory / "thread-dumps.log").open("a", encoding="utf-8")
            if not faulthandler.is_enabled():
                faulthandler.enable(file=self._dump_file, all_threads=True)
                self._owns_faulthandler = True
        except (OSError, RuntimeError):
            LOGGER.warning("Could not enable persistent native fault dumps", exc_info=True)

    def _watch_heartbeat(self) -> None:
        interval = min(self._stall_timeout / 4, 1.0)
        while not self._stop.wait(interval):
            self._check_heartbeat()

    def _check_heartbeat(self) -> None:
        with self._lock:
            if self._last_heartbeat is None or self._reported_stall:
                return
            elapsed = self._clock() - self._last_heartbeat
            if elapsed < self._stall_timeout:
                return
            self._reported_stall = True
        LOGGER.error("UI heartbeat stalled for %.1f seconds; writing all thread stacks", elapsed)
        if self._dump_file is not None:
            try:
                self._dump_file.write(
                    f"\n{time.strftime('%Y-%m-%d %H:%M:%S')} {self._identity}: "
                    f"UI heartbeat stalled for {elapsed:.1f} seconds\n",
                )
                self._dump_file.flush()
                faulthandler.dump_traceback(file=self._dump_file, all_threads=True)
            except (OSError, RuntimeError):
                LOGGER.warning("Could not write stalled thread stacks", exc_info=True)

    def _report_exception(
        self, exc_type: type[BaseException], exc_value: BaseException, traceback: TracebackType | None,
    ) -> None:
        try:
            LOGGER.critical("Unhandled main-thread exception", exc_info=(exc_type, exc_value, traceback))
        finally:
            self._previous_sys_hook(exc_type, exc_value, traceback)

    def _report_thread_exception(self, args: threading.ExceptHookArgs) -> None:
        try:
            if args.exc_type is not SystemExit:
                LOGGER.critical(
                    "Unhandled exception in thread %s", args.thread.name if args.thread else "unknown",
                    exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
                )
        finally:
            self._previous_thread_hook(args)
