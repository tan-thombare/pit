"""Asynchronous test execution engine with background thread execution."""

import asyncio
import logging
import threading
import time
from typing import Callable

from pit.attacks.models import Attack
from pit.config.models import AppConfig
from pit.evaluator.base import ResponseEvaluator
from pit.evaluator.models import EvaluationContext, EvaluationResult, Verdict
from pit.providers.base import LLMProvider, LLMResponse
from pit.storage.results import SingleTestResult, SuiteSummary

logger = logging.getLogger(__name__)


class RunnerCallbacks:
    """Callbacks dispatched to the UI during a test run."""

    def __init__(
        self,
        on_start: Callable[[int], None] | None = None,
        on_progress: Callable[[int, int, Attack], None] | None = None,
        on_attack_complete: Callable[[SingleTestResult, int, int], None] | None = None,
        on_complete: Callable[[SuiteSummary, list[SingleTestResult]], None] | None = None,
        on_cancelled: Callable[[list[SingleTestResult]], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self.on_start = on_start or (lambda total: None)
        self.on_progress = on_progress or (lambda idx, total, attack: None)
        self.on_attack_complete = on_attack_complete or (lambda res, idx, total: None)
        self.on_complete = on_complete or (lambda summary, results: None)
        self.on_cancelled = on_cancelled or (lambda results: None)
        self.on_error = on_error or (lambda err: None)


class TestEngine:
    """Orchestrates security attack execution against the LLM provider."""

    def __init__(self) -> None:
        self._is_running = False
        self._cancel_event = threading.Event()
        self._worker_thread: threading.Thread | None = None
        self._completed_results: list[SingleTestResult] = []

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(
        self,
        attacks: list[Attack],
        provider: LLMProvider,
        evaluator: ResponseEvaluator,
        config: AppConfig,
        callbacks: RunnerCallbacks,
    ) -> None:
        """Start running attacks in a dedicated background worker thread."""
        if self._is_running:
            logger.warning("Test run is already in progress.")
            return

        self._is_running = True
        self._cancel_event.clear()
        self._completed_results = []

        self._worker_thread = threading.Thread(
            target=self._run_thread_worker,
            args=(attacks, provider, evaluator, config, callbacks),
            daemon=True,
            name="PIT-Runner-Worker",
        )
        self._worker_thread.start()

    def stop(self) -> None:
        """Signal the engine to halt future attacks and preserve completed results."""
        if self._is_running:
            logger.info("Cancellation requested by user.")
            self._cancel_event.set()

    def _run_thread_worker(
        self,
        attacks: list[Attack],
        provider: LLMProvider,
        evaluator: ResponseEvaluator,
        config: AppConfig,
        callbacks: RunnerCallbacks,
    ) -> None:
        """Entry point for the background thread, running an asyncio loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                self._execute_suite_async(attacks, provider, evaluator, config, callbacks)
            )
        except Exception as e:
            logger.exception("Unexpected error in runner worker: %s", e)
            callbacks.on_error(str(e))
        finally:
            loop.close()
            self._is_running = False

    async def _execute_suite_async(
        self,
        attacks: list[Attack],
        provider: LLMProvider,
        evaluator: ResponseEvaluator,
        config: AppConfig,
        callbacks: RunnerCallbacks,
    ) -> None:
        total = len(attacks)
        callbacks.on_start(total)

        concurrency = max(1, min(config.concurrency, 5))
        delay = max(0.0, config.delay_seconds)

        if concurrency == 1:
            # Sequential execution (default)
            for idx, attack in enumerate(attacks, start=1):
                if self._cancel_event.is_set():
                    logger.info("Test stopped early at test %d of %d", idx, total)
                    callbacks.on_cancelled(self._completed_results)
                    return

                callbacks.on_progress(idx, total, attack)
                result = await self._execute_single_attack(attack, provider, evaluator, config)
                self._completed_results.append(result)
                callbacks.on_attack_complete(result, idx, total)

                if delay > 0 and idx < total and not self._cancel_event.is_set():
                    await asyncio.sleep(delay)
        else:
            # Concurrent execution with Semaphore
            sem = asyncio.Semaphore(concurrency)
            counter = [0]

            async def worker(attack: Attack):
                if self._cancel_event.is_set():
                    return
                async with sem:
                    if self._cancel_event.is_set():
                        return
                    counter[0] += 1
                    current_idx = counter[0]
                    callbacks.on_progress(current_idx, total, attack)

                    res = await self._execute_single_attack(attack, provider, evaluator, config)
                    self._completed_results.append(res)
                    callbacks.on_attack_complete(res, current_idx, total)

                    if delay > 0:
                        await asyncio.sleep(delay)

            tasks = [asyncio.create_task(worker(a)) for a in attacks]
            await asyncio.gather(*tasks, return_exceptions=True)

        if self._cancel_event.is_set():
            callbacks.on_cancelled(self._completed_results)
        else:
            summary = SuiteSummary.calculate(
                self._completed_results,
                target_model=config.api.model,
                provider=config.api.provider.value,
            )
            callbacks.on_complete(summary, self._completed_results)

    async def _execute_single_attack(
        self,
        attack: Attack,
        provider: LLMProvider,
        evaluator: ResponseEvaluator,
        config: AppConfig,
    ) -> SingleTestResult:
        """Send prompt to API, capture response, and evaluate locally."""
        try:
            # 1. API Call
            llm_response: LLMResponse = await provider.generate(
                prompt=attack.prompt,
                system_prompt=config.api.system_prompt,
            )

            # 2. Local Evaluation Context
            ctx = EvaluationContext(
                system_prompt=config.api.system_prompt,
                raw_response=llm_response.raw_response,
                api_latency_ms=llm_response.latency_ms,
                api_error=llm_response.error,
                target_model=config.api.model,
            )

            # 3. Local Evaluation
            eval_result: EvaluationResult = evaluator.evaluate(
                attack=attack,
                response=llm_response.content,
                context=ctx,
            )

            return SingleTestResult.from_run(attack, llm_response, eval_result)

        except Exception as e:
            logger.exception("Failure running attack %s: %s", attack.id, e)
            error_llm_response = LLMResponse(
                content="",
                status_code=500,
                error=f"Runner execution exception: {str(e)}",
            )
            err_result = EvaluationResult(
                verdict=Verdict.ERROR,
                risk_score=0.0,
                confidence=1.0,
                signals=[],
                reasoning=f"System execution exception: {str(e)}",
                evaluator_device="CPU",
                evaluation_latency_ms=0.0,
            )
            return SingleTestResult.from_run(attack, error_llm_response, err_result)
