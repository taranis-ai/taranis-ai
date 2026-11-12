"""Evaluate the selected local corpus without writing application databases.

Run with the worker environment. Endpoint JSON contains extraction/embedding
LLMEndpoint objects; keep it outside Git. Output includes private evidence passages.
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path

from models.hrag import EMBEDDING_CONTENT_LIMIT, EXTRACTION_CONTENT_LIMIT, IndexJob, bounded_content, input_fingerprint
from models.llm import LLMEndpoint

from worker.hrag import infer


async def evaluate(args):
    sample = json.loads(args.sample.read_text())
    items = sample["items"]
    endpoints = {pipeline: LLMEndpoint.model_validate(value) for pipeline, value in json.loads(args.endpoints.read_text()).items()}
    if set(endpoints) != {"extraction", "embedding"}:
        raise ValueError("Supply extraction and embedding endpoint configurations")
    if endpoints["embedding"].api_format != "embeddings" or endpoints["extraction"].api_format not in {"responses", "chat_completions"}:
        raise ValueError("Endpoint capabilities do not match the evaluation tasks")
    if any(not endpoint.enabled or endpoint.processing_mode != "realtime" for endpoint in endpoints.values()):
        raise ValueError("Evaluation requires enabled realtime endpoints")
    args.output.mkdir(parents=True, exist_ok=True)
    summary = {
        "items": len(items),
        "sources": len({item["source_id"] for item in items}),
        "validated_extractions": 0,
        "validated_vectors": 0,
        "entities": 0,
        "relations": 0,
        "extraction_truncated": 0,
        "embedding_truncated": 0,
        "models": {pipeline: endpoint.model for pipeline, endpoint in endpoints.items()},
        "note": "Schema and passage validation are measured automatically. Existing NER tags are a baseline, not ground truth; review the private annotation file for semantic quality.",
    }
    with (args.output / "annotations.jsonl").open("w", encoding="utf-8") as output:
        for item in items:
            annotation = {
                "id": item["id"],
                "source_id": item["source_id"],
                "existing_tags": item.get("existing_tags"),
                "review": {"correct_entities": None, "correct_relations": None, "missed_assertions": None},
            }
            for pipeline, limit in (("extraction", EXTRACTION_CONTENT_LIMIT), ("embedding", EMBEDDING_CONTENT_LIMIT)):
                content = bounded_content(item["content"], limit)
                summary[f"{pipeline}_truncated"] += len(item["content"]) > limit
                job = IndexJob(
                    id=item["id"],
                    token="evaluation",
                    fingerprint=input_fingerprint(content, "evaluation"),
                    content=content,
                    pipeline=pipeline,
                    endpoint=endpoints[pipeline],
                    dimensions=args.dimensions,
                )
                try:
                    result = await infer(job)
                except Exception:
                    annotation[pipeline] = {"status": "failed"}
                    continue
                if pipeline == "extraction":
                    summary["validated_extractions"] += 1
                    summary["entities"] += len(result["entities"])
                    summary["relations"] += len(result["relations"])
                    annotation[pipeline] = result
                else:
                    summary["validated_vectors"] += 1
                    annotation[pipeline] = {"status": "valid", "dimensions": len(result["embedding"])}
            output.write(json.dumps(annotation, ensure_ascii=False) + "\n")
            output.flush()
    (args.output / "metrics.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--endpoints", type=Path, required=True)
    parser.add_argument("--dimensions", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    logging.getLogger("llm_bot").setLevel(logging.ERROR)
    asyncio.run(evaluate(args))


if __name__ == "__main__":
    main()
