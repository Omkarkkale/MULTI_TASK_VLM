#!/usr/bin/env python3
"""Run or dry-run a reproducible local Qwen two-image zero-shot evaluation."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

from crusher_dataset import CrusherExample, load_examples
from experiment_logging import write_run_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREDICTION_FIELDS = [
    "eval_index", "source_dataset", "recording_id", "sample_id", "true_fill_level",
    "prediction", "absolute_error", "status", "raw_output", "parsed_output", "narrow_image",
    "wide_image", "error_message",
]


def parse_percentage(text: str | None) -> float | None:
    """Accept exactly one numeric percentage in the inclusive range 0–100."""
    if text is None:
        return None
    matches = re.findall(r"-?\d+(?:\.\d+)?", str(text).strip())
    if len(matches) != 1:
        return None
    try:
        value = float(matches[0])
    except ValueError:
        return None
    return value if 0.0 <= value <= 100.0 else None


def final_response(raw_output: str) -> str:
    """Return only Qwen's final answer when its default thinking block is present."""
    if "</think>" in raw_output:
        return raw_output.rsplit("</think>", maxsplit=1)[1].strip()
    return raw_output.strip()


def load_config(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "PyYAML is required. In the project venv run `uv pip install -r training/requirements.txt`."
        ) from error
    config = yaml.safe_load(path.read_text())
    if not isinstance(config, dict):
        raise ValueError(f"Configuration is not a mapping: {path}")
    return config


def project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_source_roots(path: Path | None) -> dict[str, Path] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text())
    return {name: (path.parent / root).resolve() for name, root in payload.items()}


def example_key(example: CrusherExample) -> tuple[str, str, str]:
    return (example.source_dataset or "", example.recording_id, example.sample_id)


def completed_keys(path: Path) -> set[tuple[str, str, str]]:
    if not path.is_file():
        return set()
    with path.open(newline="") as handle:
        return {
            (row.get("source_dataset", ""), row["recording_id"], row["sample_id"])
            for row in csv.DictReader(handle)
        }


def build_messages(example: CrusherExample, prompt: str) -> list[dict[str, Any]]:
    return [{"role": "user", "content": [
        {"type": "image", "image": str(example.narrow_path)},
        {"type": "image", "image": str(example.wide_path)},
        {"type": "text", "text": prompt},
    ]}]


def load_model(model_id: str, model_config: dict[str, Any]):
    """Load Qwen only for a real run; dry-runs do not import GPU packages."""
    import torch
    from transformers import AutoProcessor, BitsAndBytesConfig, Qwen3_5ForConditionalGeneration

    quantization = BitsAndBytesConfig(
        load_in_4bit=bool(model_config.get("load_in_4bit", True)),
        bnb_4bit_quant_type=model_config.get("quantization_type", "nf4"),
        bnb_4bit_use_double_quant=bool(model_config.get("double_quantization", True)),
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    processor = AutoProcessor.from_pretrained(model_id)
    model = Qwen3_5ForConditionalGeneration.from_pretrained(
        model_id,
        quantization_config=quantization,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    model.eval()
    return model, processor


def predict(
    model: Any,
    processor: Any,
    example: CrusherExample,
    prompt: str,
    max_new_tokens: int,
    enable_thinking: bool,
) -> str:
    import torch

    inputs = processor.apply_chat_template(
        build_messages(example, prompt), tokenize=True, add_generation_prompt=True,
        return_dict=True, return_tensors="pt", enable_thinking=enable_thinking,
    ).to(model.device)
    with torch.inference_mode():
        generated_ids = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    generated_ids = generated_ids[:, inputs.input_ids.shape[1] :]
    return processor.batch_decode(
        generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )[0]


def prediction_row(index: int, example: CrusherExample, raw_output: str, error: str = "") -> dict[str, str]:
    parsed_output = final_response(raw_output) if not error else ""
    value = parse_percentage(parsed_output) if not error else None
    status = "valid" if value is not None else ("error" if error else "invalid")
    absolute_error = abs(value - example.fill_level) if value is not None else ""
    return {
        "eval_index": str(index), "source_dataset": example.source_dataset or "",
        "recording_id": example.recording_id, "sample_id": example.sample_id,
        "true_fill_level": f"{example.fill_level:g}",
        "prediction": "" if value is None else f"{value:g}",
        "absolute_error": "" if value is None else f"{absolute_error:g}",
        "status": status, "raw_output": raw_output, "parsed_output": parsed_output,
        "narrow_image": str(example.narrow_path), "wide_image": str(example.wide_path),
        "error_message": error,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true", help="Validate config/data only; never load Qwen.")
    parser.add_argument("--max-samples", type=int, help="Optional cap for a smoke test; record it as non-final.")
    parser.add_argument("--overwrite", action="store_true", help="Refuse existing prediction output rather than overwrite it.")
    args = parser.parse_args()

    config_path = project_path(str(args.config))
    config = load_config(config_path)
    dataset = config["dataset"]
    metadata_csv = project_path(dataset["metadata_csv"])
    image_root = project_path(dataset["image_root"])
    roots_json = dataset.get("source_roots_json")
    source_roots = load_source_roots(project_path(roots_json)) if roots_json else None
    examples = load_examples(metadata_csv, image_root, source_roots)
    if args.max_samples is not None:
        examples = examples[: args.max_samples]
    if not examples:
        raise ValueError("No examples selected.")

    experiment, model_config, prompt_config = config["experiment"], config["model"], config["prompt"]
    output_root = project_path(config["output"]["root"])
    prediction_path = output_root / "predictions.csv"
    print(f"Experiment: {experiment['id']}")
    print(f"Examples selected: {len(examples)}")
    print(f"Dataset metadata: {metadata_csv}")
    print(f"Model: {model_config['id']}")
    if args.dry_run:
        print("Dry run passed: config and all selected image paths are valid. Qwen was not loaded.")
        return
    if not experiment.get("allow_run", False):
        raise SystemExit(
            "Blocked by configuration: set experiment.allow_run to true only when you intend "
            "to download/load Qwen and begin this exploratory run."
        )
    if args.overwrite and prediction_path.exists():
        raise SystemExit("Refusing to overwrite predictions. Choose a new output directory instead.")

    output_root.mkdir(parents=True, exist_ok=True)
    write_run_manifest(
        output_root / "run_manifest.json", experiment_id=experiment["id"],
        command=[sys.executable, *sys.argv], config_path=config_path, project_root=PROJECT_ROOT,
        extra={"dataset_row_count_selected": len(examples), "model_id": model_config["id"]},
    )
    done = completed_keys(prediction_path)
    pending = [example for example in examples if example_key(example) not in done]
    print(f"Already recorded: {len(done)} | Remaining: {len(pending)}")
    model, processor = load_model(model_config["id"], model_config)
    new_file = not prediction_path.exists()
    with prediction_path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PREDICTION_FIELDS)
        if new_file:
            writer.writeheader()
        for index, example in enumerate(pending, start=len(done) + 1):
            try:
                row = prediction_row(index, example, predict(
                    model, processor, example, prompt_config["text"],
                    int(prompt_config["max_new_tokens"]),
                    bool(prompt_config.get("enable_thinking", True)),
                ))
            except Exception as error:
                row = prediction_row(index, example, "", f"{type(error).__name__}: {error}")
            writer.writerow(row)
            handle.flush()
            print(f"[{index}/{len(examples)}] {row['status']}: {row['prediction'] or row['error_message']}")


if __name__ == "__main__":
    main()
