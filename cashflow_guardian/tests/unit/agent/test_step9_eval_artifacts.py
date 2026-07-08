import json
from pathlib import Path

import yaml
from google.adk.cli.utils.agent_loader import AgentLoader

from tests.eval.check_step9_traces import check_traces


ROOT = Path(__file__).resolve().parents[3]


def test_agents_cli_manifest_points_to_existing_agent_directory():
    manifest = yaml.safe_load((ROOT / "agents-cli-manifest.yaml").read_text(encoding="utf-8"))

    assert manifest["name"] == "cashflow-guardian"
    assert manifest["create_params"]["deployment_target"] == "none"
    assert manifest["create_params"]["session_type"] == "in_memory"
    agent_dir = ROOT / manifest["agent_directory"]
    assert agent_dir.is_dir()
    assert (agent_dir / "__init__.py").is_file()
    assert (agent_dir / "agent.py").is_file()


def test_root_agent_importable_through_adk_loader():
    loader = AgentLoader(agents_dir=str(ROOT / "src" / "cashflow_guardian"))
    agent = loader.load_agent("agent")

    assert agent.name == "cashflow_guardian_agent"
    assert getattr(agent, "tools", []) == []


def test_eval_dataset_schema_and_case_ids_are_complete():
    dataset = json.loads((ROOT / "tests" / "eval" / "datasets" / "cashflow_guardian_dataset.json").read_text(encoding="utf-8"))
    expectations = json.loads((ROOT / "tests" / "eval" / "expectations" / "cashflow_guardian_expectations.json").read_text(encoding="utf-8"))

    cases = dataset["eval_cases"]
    assert 12 <= len(cases) <= 16
    case_ids = {case["eval_case_id"] for case in cases}
    assert case_ids == set(expectations)
    for case in cases:
        prompt = case["prompt"]
        assert prompt["role"] == "user"
        assert prompt["parts"][-1]["text"]


def test_expectations_do_not_allow_forbidden_tools():
    expectations = json.loads((ROOT / "tests" / "eval" / "expectations" / "cashflow_guardian_expectations.json").read_text(encoding="utf-8"))
    forbidden = {"approve_or_reject_watchlist_action", "propose_watchlist_action"}

    for case_id, expectation in expectations.items():
        assert forbidden.isdisjoint(set(expectation["allowed_tools"])), case_id
        assert forbidden.issubset(set(expectation["forbidden_tools"])), case_id


def test_deterministic_trace_checker_detects_forbidden_tool(tmp_path):
    trace = {
        "eval_cases": [
            {
                "eval_case_id": "unsupported_approval",
                "agent_data": {
                    "turns": [
                        {
                            "turn_index": 0,
                            "events": [
                                {
                                    "author": "cashflow_guardian_agent",
                                    "content": {
                                        "parts": [
                                            {
                                                "function_call": {
                                                    "name": "approve_or_reject_watchlist_action",
                                                    "args": {"approved": True},
                                                }
                                            }
                                        ]
                                    },
                                }
                            ],
                        }
                    ]
                },
                "responses": [{"response": {"parts": [{"text": "Approved."}]}}],
            }
        ]
    }
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps(trace), encoding="utf-8")

    result = check_traces(trace_path)

    assert result["passed"] is False
    assert any("Forbidden tool call" in failure for failure in result["critical_failures"])


def test_eval_config_uses_supported_metric_constants():
    config = yaml.safe_load((ROOT / "tests" / "eval" / "configs" / "cashflow_guardian_eval.yaml").read_text(encoding="utf-8"))
    supported = {
        "final_response_quality_v1",
        "grounding_v1",
        "tool_use_quality_v1",
        "safety_v1",
        "instruction_following_v1",
        "deterministic_security_gate",
        "deterministic_hitl_gate",
    }

    assert set(config["metrics_to_run"]) == supported
