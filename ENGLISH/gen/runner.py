from __future__ import annotations
import asyncio
import json
import logging
import os
import signal
import sys
import time
from typing import Any

from gen.config import Config
from gen.cost import CostLedger
from gen.holdout import run_holdout_split
from gen.integrity import check_file_sizes, run_integrity_scan
from gen.ledger import LockManager, SweepLedger
from gen.provider import create_provider
from gen.queue import build_queue, write_queue
from gen.slot_fill_run import run_slot_fill
from gen.worker import CellWorker

logger = logging.getLogger("gen.runner")


class GenerationRunner:
    """Main generation runner: plans queue, dispatches workers, manages lifecycle."""

    def __init__(self, config_path: str):
        self.config = Config.from_file(config_path)
        self._shutdown_requested = False
        self._active_tasks: set[asyncio.Task] = set()
        self._completed_cells = 0
        self._failed_cells = 0
        self._start_time: float = 0.0

        # Sweep + locks (must be before logging setup)
        self.sweep_dir = self.config.lang_path("sweep")
        os.makedirs(self.sweep_dir, exist_ok=True)

        # Setup logging
        self._setup_logging()

        self.lock_manager = LockManager(self.sweep_dir)

        # Cost ledger
        self.cost_ledger = CostLedger(
            os.path.join(self.sweep_dir, "cost_ledger.json"),
            self.config.active_provider_configs,
        )

    def _setup_logging(self) -> None:
        log_path = os.path.join(self.sweep_dir, "run.log")
        file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                              datefmt="%H:%M:%S")
        )

        root = logging.getLogger("gen")
        root.setLevel(logging.DEBUG)
        root.addHandler(file_handler)
        root.addHandler(console_handler)

    async def run(self, categories: list[str] | None = None) -> int:
        self._start_time = time.time()

        logger.info(
            "Generation run: %s (root=%s, workers=%d)",
            self.config.generation_run,
            self.config.lang_root,
            self.config.max_workers,
        )

        # Clear stale locks
        cleared = self._clear_stale_locks()
        if cleared > 0:
            logger.info("Cleared %d stale locks", cleared)

        # Build queue
        queue = build_queue(self.config, categories)
        if not queue:
            logger.info("No pending cells in queue — all caught up")
            return 0

        queue_path = os.path.join(self.sweep_dir, "queue.jsonl")
        write_queue(queue, queue_path)
        logger.info("Queue: %d pending cells written to %s", len(queue), queue_path)

        # Print dry-run summary
        self._print_summary(queue)

        if self.config.max_workers <= 0:
            logger.info("max_workers=0, dry run complete. Exiting.")
            return 0

        # Register signal handlers for graceful shutdown
        self._register_signal_handlers()

        # Dispatch workers
        provider_workers = _build_workers(self.config, self.cost_ledger)
        queue_chunks = _distribute(queue, provider_workers)

        tasks = []
        for worker, cell_chunk in zip(provider_workers, queue_chunks):
            task = asyncio.create_task(
                self._worker_loop(worker, cell_chunk, categories)
            )
            self._active_tasks.add(task)
            task.add_done_callback(self._active_tasks.discard)
            tasks.append(task)

        # Wait for all workers to finish
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Post-generation integrity scan
        await self._post_generation_scan(categories)

        elapsed = time.time() - self._start_time
        logger.info(
            "Run complete: %d cells generated, %d failed, %.1fs elapsed, $%.4f spent",
            self._completed_cells,
            self._failed_cells,
            elapsed,
            self.cost_ledger.total_spent,
        )
        return self._failed_cells

    async def _worker_loop(
        self,
        worker: CellWorker,
        cells: list[dict],
        categories: list[str] | None,
    ) -> None:
        logger.info("Worker started with %d cells", len(cells))
        for cell in cells:
            if self._shutdown_requested:
                logger.info("Shutdown requested, stopping worker loop")
                break

            cell_id = cell["cell_id"]
            category = cell["category"]

            # Try to acquire lock
            acquired = self.lock_manager.acquire(cell_id)
            if not acquired:
                logger.debug("%s: locked by another worker, skipping", cell_id)
                continue

            logger.info("%s: acquired lock, generating...", cell_id)

            try:
                ledger = SweepLedger(
                    os.path.join(self.sweep_dir, f"{category}.json"),
                    category,
                )
                cell_status = ledger.ensure_cell(
                    topic_id=cell["topic_id"],
                    subtype=cell["subtype"],
                    difficulty=cell["difficulty"],
                    abstr=cell["abstraction_level"],
                    target_count=cell["target_count"],
                )
                cell_status.status = "generating"

                success = await worker.generate_cell(cell, cell_status, ledger)
                if success:
                    self._completed_cells += 1
                else:
                    self._failed_cells += 1
            except Exception as e:
                logger.error("%s: worker error: %s", cell_id, e, exc_info=True)
                self._failed_cells += 1
            finally:
                self.lock_manager.release(cell_id)

    def _clear_stale_locks(self) -> int:
        count = 0
        categories_dir = os.path.join(self.config.lang_root, "schema")
        if not os.path.isdir(categories_dir):
            return 0
        for entry in os.listdir(categories_dir):
            entry_path = os.path.join(categories_dir, entry)
            if not os.path.isdir(entry_path):
                continue
            if not os.path.isfile(os.path.join(entry_path, "topics.jsonl")):
                continue
            ledger_path = os.path.join(self.sweep_dir, f"{entry}.json")
            if os.path.isfile(ledger_path):
                ledger = SweepLedger(ledger_path, entry)
                count += ledger.clear_stale_locks(self.config.lock_timeout_minutes)
        return count

    def _register_signal_handlers(self) -> None:
        try:
            loop = asyncio.get_event_loop()

            def _shutdown(sig: int) -> None:
                logger.info("Received signal %s, finishing current cell...", sig)
                self._shutdown_requested = True

            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(sig, lambda s=sig: _shutdown(s))
                except NotImplementedError:
                    # Windows doesn't support add_signal_handler
                    pass
        except RuntimeError:
            pass

    def _print_summary(self, queue: list[dict]) -> None:
        cats: dict[str, int] = {}
        for item in queue:
            cat = item["category"]
            cats[cat] = cats.get(cat, 0) + 1

        print(f"\n{'='*60}")
        print(f"Generation run: {self.config.generation_run}")
        print(f"Language root: {self.config.lang_root}")
        print(f"Active providers: {', '.join(self.config.active_providers)}")
        print(f"Workers: {self.config.max_workers}")
        print(f"Total pending cells: {len(queue)}")
        print(f"\n  Category breakdown:")
        for cat, count in sorted(cats.items()):
            print(f"    {cat}: {count}")
        print(f"{'='*60}\n")

    async def _post_generation_scan(
        self, categories: list[str] | None
    ) -> None:
        logger.info("Running post-generation integrity scan...")
        result = run_integrity_scan(self.config, categories)
        if result.errors:
            logger.warning("Integrity errors: %d", len(result.errors))
            for e in result.errors:
                logger.warning("  %s", e)
        if result.warnings:
            logger.info("Integrity warnings: %d", len(result.warnings))
            for w in result.warnings:
                logger.info("  %s", w)
        if result.passed:
            logger.info("Integrity scan: all checks passed")


def _build_workers(config: Config, cost_ledger: CostLedger) -> list[CellWorker]:
    workers = []
    provider_configs = config.active_provider_configs
    for pconf in provider_configs:
        for temp in config.temperature_sweep:
            provider = create_provider(pconf)
            worker = CellWorker(
                config=config,
                provider=provider,
                provider_config=pconf,
                cost_ledger=cost_ledger,
                temperature=temp,
            )
            workers.append(worker)
    if not workers:
        workers.append(
            CellWorker(
                config=config,
                provider=create_provider(provider_configs[0]),
                provider_config=provider_configs[0],
                cost_ledger=cost_ledger,
            )
        )
    return workers


def _distribute(
    cells: list[dict], workers: list[CellWorker]
) -> list[list[dict]]:
    """Round-robin distribute cells across workers."""
    chunks: list[list[dict]] = [[] for _ in workers]
    for i, cell in enumerate(cells):
        chunks[i % len(workers)].append(cell)
    return chunks


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Synthetic data generation runner"
    )
    parser.add_argument(
        "--config",
        default="gen/config.json",
        help="Path to config file (default: gen/config.json)",
    )
    parser.add_argument(
        "--categories",
        nargs="*",
        help="Limit generation to specific categories",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build queue and print summary without generating",
    )
    parser.add_argument(
        "--integrity",
        action="store_true",
        help="Run integrity scan only (no generation)",
    )
    parser.add_argument(
        "--fill-slots",
        action="store_true",
        help="Fill {{SLOT}} markers in all generated data files",
    )
    parser.add_argument(
        "--holdout",
        action="store_true",
        help="Split generated data into train/holdout sets",
    )
    args = parser.parse_args()

    if args.dry_run:
        config = Config.from_file(args.config)
        runner = GenerationRunner(args.config)
        queue = build_queue(config, args.categories)
        if queue:
            runner._print_summary(queue)
        else:
            print("No pending cells")
        return

    if args.integrity:
        config = Config.from_file(args.config)
        result = run_integrity_scan(config, args.categories)
        print(result)
        return

    if args.fill_slots:
        config = Config.from_file(args.config)
        result = run_slot_fill(config, args.categories, in_place=True)
        print(f"Filled {result.get('total_filled', 0)} variants")
        if result.get("total_unknown_slots", 0) > 0:
            print(f"  Unknown slot names found: {result['total_unknown_slots']}")
            print("  Add them to schema/slot_fills.json before training merge")
        return

    if args.holdout:
        config = Config.from_file(args.config)
        result = run_holdout_split(config, args.categories)
        total = result["total_train_variants"] + result["total_holdout_variants"]
        print(
            f"Split {total} variants: "
            f"{result['total_train_variants']} train, "
            f"{result['total_holdout_variants']} holdout"
        )
        return

    runner = GenerationRunner(args.config)
    asyncio.run(runner.run(args.categories))


if __name__ == "__main__":
    main()
