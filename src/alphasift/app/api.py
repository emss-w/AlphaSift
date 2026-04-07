from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request

from alphasift.app.db import MetadataStore
from alphasift.app.schemas import (
    CreatePaperSessionRequest,
    CreateSmaExperimentRequest,
    HealthResponse,
)
from alphasift.app.services import AppServices
from alphasift.config import Config, load_config


def create_app(config: Config | None = None) -> FastAPI:
    """Create a configured FastAPI app for local AlphaSift workflows."""
    cfg = config or load_config()
    store = MetadataStore(cfg.app_db_path)
    services = AppServices(cfg, store)

    app = FastAPI(title="AlphaSift Local API", version="0.1.0")
    app.state.services = services

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/system/info")
    def system_info(request: Request):
        return _services(request).system_info()

    @app.get("/strategies")
    def list_strategies(request: Request):
        return _services(request).list_strategies()

    @app.get("/strategies/{strategy_id}")
    def get_strategy(strategy_id: str, request: Request):
        strategy = _services(request).get_strategy(strategy_id)
        if strategy is None:
            raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
        return strategy

    @app.post("/experiments/sma-cross")
    def run_sma_experiment(payload: CreateSmaExperimentRequest, request: Request):
        return _run_with_bad_request(lambda: _services(request).run_sma_experiment(payload))

    @app.get("/experiments")
    def list_experiments(request: Request):
        return _services(request).list_experiment_runs()

    @app.get("/experiments/{run_id}")
    def get_experiment(run_id: str, request: Request):
        run = _services(request).get_experiment_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Experiment run not found: {run_id}")
        return run

    @app.post("/paper/sessions")
    def start_paper_session(payload: CreatePaperSessionRequest, request: Request):
        return _run_with_bad_request(lambda: _services(request).start_paper_session(payload))

    @app.get("/paper/sessions")
    def list_paper_sessions(request: Request):
        return _services(request).list_paper_sessions()

    @app.get("/paper/sessions/{session_id}")
    def get_paper_session(session_id: str, request: Request):
        session = _services(request).get_paper_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail=f"Paper session not found: {session_id}")
        return session

    @app.get("/artifacts")
    def list_artifacts(request: Request):
        return _services(request).list_artifacts()

    @app.get("/artifacts/{artifact_id}")
    def get_artifact(artifact_id: str, request: Request):
        artifact = _services(request).get_artifact(artifact_id)
        if artifact is None:
            raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")
        return artifact

    return app


def _services(request: Request) -> AppServices:
    return request.app.state.services


def _run_with_bad_request(fn):
    try:
        return fn()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
