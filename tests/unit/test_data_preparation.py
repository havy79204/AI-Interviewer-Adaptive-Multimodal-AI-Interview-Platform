import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from rag.chunking import extract_with_docling, run_indexing


SAMPLE_MARKDOWN = {
    "cv": "# [CV 01]\n**ỨNG VIÊN: SAMPLE CANDIDATE**\nPython engineer.",
    "jd": "# [JD 01]: Sample Engineer\nPython and distributed systems.",
    "company": "# [DOC 01]: Sample Company\nEngineering handbook.",
    "knowledge": "# [TÀI LIỆU 01]: Sample Interview Guide\nUse evidence-based questions.",
}


class FakeConverter:
    def convert(self, source: str) -> SimpleNamespace:
        category = Path(source).parent.name
        return SimpleNamespace(
            document=SimpleNamespace(
                export_to_markdown=lambda: SAMPLE_MARKDOWN[category]
            )
        )


def _create_sample_inputs(origin: Path) -> None:
    for category in SAMPLE_MARKDOWN:
        folder = origin / category
        folder.mkdir(parents=True)
        (folder / f"{category}.pdf").write_bytes(b"sample-only")


def test_data_preparation_requires_confirmation_before_processing(tmp_path, monkeypatch):
    origin = tmp_path / "data_origin"
    parser = tmp_path / "data_parser"
    _create_sample_inputs(origin)
    converter_calls = []
    monkeypatch.setattr(
        extract_with_docling,
        "get_optimized_docling_converter",
        lambda: converter_calls.append(True),
    )

    result = extract_with_docling.process_data_origin_pipeline(
        origin, parser, is_confirmed=False
    )

    assert result["status"] == "waiting_confirmation"
    assert len(result["files"]) == len(SAMPLE_MARKDOWN)
    assert converter_calls == []
    assert not parser.exists()


def test_data_preparation_extracts_sample_documents_by_category(tmp_path, monkeypatch):
    origin = tmp_path / "data_origin"
    parser = tmp_path / "data_parser"
    _create_sample_inputs(origin)
    monkeypatch.setattr(
        extract_with_docling,
        "get_optimized_docling_converter",
        FakeConverter,
    )

    result = extract_with_docling.process_data_origin_pipeline(
        origin, parser, is_confirmed=True
    )

    assert result["status"] == "success"
    assert result["total_files"] == len(SAMPLE_MARKDOWN)
    for category, expected_markdown in SAMPLE_MARKDOWN.items():
        outputs = list((parser / category).glob("*.md"))
        assert len(outputs) == 1
        assert outputs[0].read_text(encoding="utf-8") == expected_markdown


def test_indexing_processes_sample_documents_for_all_four_categories(tmp_path, monkeypatch):
    parser = tmp_path / "data_parser"
    indexed = tmp_path / "indexed"
    for category, content in SAMPLE_MARKDOWN.items():
        folder = parser / category
        folder.mkdir(parents=True)
        (folder / f"{category}_sample.md").write_text(content, encoding="utf-8")
        (folder / f"context_{category}_sample.md").write_text(
            content, encoding="utf-8"
        )
    unsupported = parser / "unrecognized"
    unsupported.mkdir()
    (unsupported / "ignored.md").write_text("Not an indexing category.")

    indexed_types = []

    def sample_llm(_system_prompt, user_prompt, schema):
        doc_type = re.search(r"Loại tài liệu: (\w+)", user_prompt).group(1)
        indexed_types.append(doc_type)
        lines = [
            int(line_number)
            for line_number in re.findall(
                r"^\[L(\d+)\]", user_prompt, flags=re.MULTILINE
            )
        ]
        chunk_model = schema.model_fields["chunks"].annotation.__args__[0]
        chunk = chunk_model(start_line=min(lines), end_line=max(lines))
        return schema(chunks=[chunk])

    monkeypatch.setattr(run_indexing, "make_llm_call", lambda: sample_llm)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_indexing.py", str(parser), "--out", str(indexed)],
    )

    run_indexing.main()

    assert set(indexed_types) == set(SAMPLE_MARKDOWN)
    assert len(indexed_types) == len(SAMPLE_MARKDOWN)
    for category, source in SAMPLE_MARKDOWN.items():
        output = indexed / category / f"{category}_sample.json"
        result = json.loads(output.read_text(encoding="utf-8"))
        assert result["doc_type"] == category
        assert len(result["chunks"]) == 1
        assert result["chunks"][0]["text"] == source
    assert not (indexed / "unrecognized").exists()


def test_local_indexing_builds_lexical_chunks_without_calling_llm(tmp_path, monkeypatch):
    parser = tmp_path / "data_parser"
    indexed = tmp_path / "indexed"
    cv_folder = parser / "cv"
    cv_folder.mkdir(parents=True)
    markdown = (
        "# Candidate Profile\n"
        "Python engineer with Kubernetes production experience.\n"
        "\n"
        "## Work History\n"
        "Built AWS services and maintained PostgreSQL databases."
    )
    (cv_folder / "selected_cv.md").write_text(markdown, encoding="utf-8")
    (cv_folder / "context_selected_cv.md").write_text(
        "This context file must be skipped.", encoding="utf-8"
    )
    monkeypatch.setattr(
        run_indexing,
        "make_llm_call",
        lambda: pytest.fail("local indexing must not initialize an LLM client"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_indexing.py",
            str(parser),
            "--out",
            str(indexed),
            "--local",
            "--chunk-words",
            "9",
        ],
    )

    run_indexing.main()

    output = indexed / "cv" / "selected_cv.json"
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["doc_type"] == "cv"
    assert result["metadata"]["indexing_mode"] == "local_lexical"
    assert result["warnings"]
    assert len(result["chunks"]) == 2
    assert [chunk["start_line"] for chunk in result["chunks"]] == [1, 4]
    assert all(chunk["text"] for chunk in result["chunks"])
    assert any("python" in chunk["metadata"]["keywords"] for chunk in result["chunks"])
    assert not (indexed / "cv" / "context_selected_cv.json").exists()
