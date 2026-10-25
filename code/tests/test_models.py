from __future__ import annotations

import os
from pathlib import Path

import pytest

from erasecase import models


def test_root_env_does_not_override_existing_value(monkeypatch, tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OPENROUTER_API_KEY=file-value\n", encoding="utf-8")
    monkeypatch.setattr(models, "ROOT", tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "environment-value")

    assert models.load_local_environment() == env_path
    assert os.environ["OPENROUTER_API_KEY"] == "environment-value"


def test_synthetic_probe_image_is_inline_png() -> None:
    assert models.synthetic_probe_image().startswith("data:image/png;base64,")


def test_probe_cost_reserves_request_tokens_and_image() -> None:
    model = {
        "pricing": {
            "request": "0.001",
            "prompt": "0.000002",
            "completion": "0.000004",
            "image": "0.002",
        }
    }
    assert models.estimate_probe_cost(
        model, input_tokens=100, output_tokens=10, images=1
    ) == pytest.approx(0.00324)


def test_probe_cost_fails_closed_without_required_pricing() -> None:
    with pytest.raises(models.ProviderError, match="omitted pricing"):
        models.estimate_probe_cost({}, input_tokens=1, output_tokens=1)
