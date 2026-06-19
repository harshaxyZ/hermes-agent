import os
import pytest
from unittest.mock import patch, MagicMock
import tools.approval as approval_mod
from tools.approval import check_all_command_guards, check_dangerous_command

@pytest.fixture(autouse=True)
def clean_state():
    approval_mod._command_denylist_cached = None
    saved = {}
    for k in ("HERMES_INTERACTIVE", "HERMES_GATEWAY_SESSION", "HERMES_EXEC_ASK", "HERMES_YOLO_MODE"):
        if k in os.environ:
            saved[k] = os.environ.pop(k)
    yield
    approval_mod._command_denylist_cached = None
    for k, v in saved.items():
        os.environ[k] = v
    for k in ("HERMES_INTERACTIVE", "HERMES_GATEWAY_SESSION", "HERMES_EXEC_ASK", "HERMES_YOLO_MODE"):
        os.environ.pop(k, None)

def test_container_mode_skip(monkeypatch):
    """When approvals.container_mode is 'skip' (default), containers bypass all checks."""
    monkeypatch.setattr(approval_mod, "_get_container_approval_mode", lambda: "skip")
    # Even hardline is bypassed
    r1 = check_dangerous_command("rm -rf /", "docker")
    assert r1["approved"] is True
    r2 = check_all_command_guards("rm -rf /", "docker")
    assert r2["approved"] is True

def test_container_mode_warn(monkeypatch):
    """When approvals.container_mode is 'warn', containers do NOT bypass hardline/denylist/sudo guards."""
    monkeypatch.setattr(approval_mod, "_get_container_approval_mode", lambda: "warn")
    
    # Hardline is blocked
    r1 = check_dangerous_command("rm -rf /", "docker")
    assert r1["approved"] is False
    assert r1.get("hardline") is True
    
    # Sudo stdin is blocked
    r2 = check_all_command_guards("sudo -S whoami", "docker")
    assert r2["approved"] is False

def test_container_mode_enforce(monkeypatch):
    """When approvals.container_mode is 'enforce', containers are treated as normal interactive environments."""
    monkeypatch.setattr(approval_mod, "_get_container_approval_mode", lambda: "enforce")
    os.environ["HERMES_INTERACTIVE"] = "1"
    
    # Dangerous commands require approval
    cb = MagicMock(return_value="deny")
    r1 = check_dangerous_command("rm -rf /tmp/foo", "docker", approval_callback=cb)
    assert r1["approved"] is False
    cb.assert_called_once()

def test_custom_command_denylist(monkeypatch):
    """Custom denylist blocks matching commands unconditionally."""
    monkeypatch.setattr(approval_mod, "_load_command_denylist", lambda: ["docker run *", "kubectl delete *"])
    
    r1 = check_dangerous_command("docker run -it alpine", "local")
    assert r1["approved"] is False
    assert "denylist" in r1["message"]

    # Survives YOLO
    os.environ["HERMES_YOLO_MODE"] = "1"
    r2 = check_all_command_guards("kubectl delete pod foo", "local")
    assert r2["approved"] is False
