"""Audit — the format-anomaly detector in manager.py.

Synthetic tests over a sandbox: feed JSONL files with known anomalies and check
the auditor flags them, classifies them in the right bucket, and that a clean
chat yields no findings. The auditor only reads `source_path`; never touches
real user data.
"""

import json

import pytest


@pytest.fixture
def audit_sandbox(tmp_path):
    base = tmp_path
    source_dir = base / "projects"
    output_dir = base / "output"
    source_dir.mkdir()
    output_dir.mkdir()
    proj = source_dir / "C--Users-demo-proj"
    proj.mkdir()
    config = {
        "_resolved": {"output_path": output_dir, "source_path": source_dir},
        "output": {"index_filename": "CCV-Dashboard.html"},
        "time_format": "12h",
    }
    return config, proj, output_dir


def _write(proj, name, records):
    (proj / name).write_text(
        "\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


# ====== Detection by category ======

def test_detecta_tipo_contenido_nuevo(mgr, audit_sandbox):
    config, proj, _ = audit_sandbox
    _write(proj, "a1.jsonl", [
        {"type": "assistant", "message": {"role": "assistant",
         "content": [{"type": "narration", "text": "prosa de un formato futuro"}]}},
    ])
    findings = mgr.audit_chats(config, "all")
    assert "narration" in findings["unknown_content_types"]
    assert findings["unknown_content_types"]["narration"]["count"] == 1


def test_detecta_tipo_mensaje_nuevo(mgr, audit_sandbox):
    config, proj, _ = audit_sandbox
    _write(proj, "a2.jsonl", [{"type": "weird-new-type", "foo": "bar"}])
    findings = mgr.audit_chats(config, "all")
    assert "weird-new-type" in findings["unknown_message_types"]


def test_detecta_thinking_vacio(mgr, audit_sandbox):
    config, proj, _ = audit_sandbox
    _write(proj, "a3.jsonl", [
        {"type": "assistant", "message": {"role": "assistant",
         "content": [{"type": "thinking", "thinking": ""}]}},
    ])
    findings = mgr.audit_chats(config, "all")
    assert findings["empty_thinking"]["count"] == 1


def test_detecta_parse_error(mgr, audit_sandbox):
    config, proj, _ = audit_sandbox
    (proj / "a4.jsonl").write_text('{"type":"user"}\n{ esto no es json }\n', encoding="utf-8")
    findings = mgr.audit_chats(config, "all")
    assert len(findings["parse_errors"]) == 1
    assert findings["parse_errors"][0]["line"] == 2


def test_registra_tools(mgr, audit_sandbox):
    config, proj, _ = audit_sandbox
    _write(proj, "a5.jsonl", [
        {"type": "assistant", "message": {"role": "assistant",
         "content": [{"type": "tool_use", "name": "Bash", "id": "t", "input": {"command": "ls"}}]}},
    ])
    findings = mgr.audit_chats(config, "all")
    assert findings["tool_names"].get("Bash") == 1


def test_metadata_conocida_no_se_marca(mgr, audit_sandbox):
    # Entradas de metadata/estado de sesión: conocidas, no son mensajes — el
    # auditor NO debe gritarlas como cambio de formato (calibración real).
    config, proj, _ = audit_sandbox
    _write(proj, "meta.jsonl", [
        {"type": "attachment", "sessionId": "s", "uuid": "u"},
        {"type": "agent-name", "agentName": "Tester", "sessionId": "s"},
        {"type": "permission-mode", "permissionMode": "default", "sessionId": "s"},
        {"type": "ai-title", "aiTitle": "Un titulo", "sessionId": "s"},
    ])
    findings = mgr.audit_chats(config, "all")
    assert not findings["unknown_message_types"]


# ====== Clean chat ======

def test_chat_limpio_sin_findings(mgr, audit_sandbox):
    config, proj, _ = audit_sandbox
    _write(proj, "clean.jsonl", [
        {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "hola"}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "ok"}]}},
        {"type": "summary", "summary": "resumen"},
    ])
    findings = mgr.audit_chats(config, "all")
    assert not findings["unknown_message_types"]
    assert not findings["unknown_content_types"]
    assert findings["empty_thinking"]["count"] == 0
    assert not findings["parse_errors"]
    assert mgr._audit_has_findings(findings) is False


# ====== Scan scope ======

def test_scan_count_limita(mgr, audit_sandbox):
    config, proj, _ = audit_sandbox
    for i in range(3):
        _write(proj, f"c{i}.jsonl", [
            {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "x"}]}}])
    findings = mgr.audit_chats(config, "2")
    assert findings["scanned"] == 2


def test_scan_all(mgr, audit_sandbox):
    config, proj, _ = audit_sandbox
    for i in range(3):
        _write(proj, f"d{i}.jsonl", [
            {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "x"}]}}])
    findings = mgr.audit_chats(config, "all")
    assert findings["scanned"] == 3
    assert findings["scan_all"] is True


# ====== HTML report ======

def test_genera_informe_con_hallazgo(mgr, audit_sandbox):
    config, proj, output_dir = audit_sandbox
    _write(proj, "a.jsonl", [
        {"type": "assistant", "message": {"role": "assistant",
         "content": [{"type": "narration", "text": "x"}]}},
    ])
    path, findings = mgr.generate_audit_view(config, "all")
    assert path.exists()
    assert path.name.startswith("CCV-Audit ")
    html = path.read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")
    assert "Format Audit" in html
    assert "narration" in html
    assert "Possible format changes" in html
    # CTA de feedback presente cuando hay hallazgos.
    assert "open an issue" in html


def test_informe_all_clear(mgr, audit_sandbox):
    config, proj, output_dir = audit_sandbox
    _write(proj, "clean.jsonl", [
        {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "hola"}]}},
    ])
    path, findings = mgr.generate_audit_view(config, "all")
    html = path.read_text(encoding="utf-8")
    assert "All clear" in html


def test_informe_tiene_boton_copiar(mgr, audit_sandbox):
    config, proj, _ = audit_sandbox
    _write(proj, "x.jsonl", [
        {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "hola"}]}}])
    path, _ = mgr.generate_audit_view(config, "all")
    html = path.read_text(encoding="utf-8")
    assert "Copy report" in html
    assert "copyAuditReport" in html
    assert "audit-report-text" in html
