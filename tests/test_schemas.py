from debugger.artifacts.schemas import IterationEnvelope, RunStatus


def test_iteration_schema_minimal():
    obj = {
        "schema_version": 1,
        "track": "A",
        "iteration": 1,
        "status_signal": "CONTINUE",
        "hypothesis": "x",
        "confidence": 0.5,
        "experiments": [],
        "proposed_changes": {"has_patch": False},
        "risks": [],
    }
    IterationEnvelope.model_validate(obj)


def test_run_status_schema():
    RunStatus(run_id="r", mode="debug", status="OK")
