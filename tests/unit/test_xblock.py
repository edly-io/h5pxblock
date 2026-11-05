"""
Tests for h5pxblock.h5pxblock.H5PPlayerXBlock.
"""
import importlib.util
import json
import sys
import types
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

import pytest
from django.core.files.storage import FileSystemStorage
from webob import Request
from xblock.exceptions import JsonHandlerError

from conftest import block_module

KEY = "h5pxblockmedia/org/course/blk"


def json_request(payload):
    return Request.blank("/", method="POST", body=json.dumps(payload).encode("utf8"))


def form(**overrides):
    params = {
        "display_name": "Quiz",
        "show_frame": "true",
        "show_copyright": "false",
        "show_h5p": "1",
        "show_fullscreen": "True",
        "is_scorable": "true",
        "save_freq": "5",
        "points": "10",
        "weight": "1,5",
        "h5p_content_bundle": "",
        "h5_content_path": "",
    }
    params.update(overrides)
    return SimpleNamespace(params=params)


def bundle():
    return SimpleNamespace(file=SimpleNamespace(name="pkg.h5p", size=42))


def test_fallback_import_paths():
    """Older releases ship ResourceLoader as xblockutils.resources."""
    legacy = types.ModuleType("xblockutils.resources")
    legacy.ResourceLoader = mock.Mock()
    patched = {
        "xblock.utils.resources": None,
        "xblockutils": types.ModuleType("xblockutils"),
        "xblockutils.resources": legacy,
    }
    spec = importlib.util.spec_from_file_location("h5pxblock_legacy", block_module.__file__)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, patched):
        spec.loader.exec_module(module)
    assert module.ResourceLoader is legacy.ResourceLoader


def test_fields_and_scoring(block):
    assert block.max_score() == 100
    assert block.get_context_studio()["h5p_xblock"] is block
    assert block.get_context_studio()["points"] is block.fields["points"]


def test_storage_paths(block):
    assert block.get_block_path_prefix == "org/course/blk"
    assert block.h5p_content_url.endswith("h5pxblockmedia/org/course/blk")
    assert block.local_storage_path.endswith("h5pxblockmedia/org/course/blk")
    assert block.cloud_storage_path == KEY


def test_workbench_uses_usage_id(block):
    class WorkbenchRuntime(type(block.runtime)):
        pass

    block.runtime.__class__ = WorkbenchRuntime
    assert block.get_block_path_prefix == str(block.scope_ids.usage_id)


def test_store_content_on_local_fs(block, monkeypatch, tmp_path):
    assert block.store_content_on_local_fs is False
    monkeypatch.setattr(block_module, "H5P_STORAGE", FileSystemStorage(location=str(tmp_path)))
    assert block.store_content_on_local_fs is True


def test_player_url_local_fs_passes_through(block, monkeypatch, tmp_path):
    monkeypatch.setattr(block_module, "H5P_STORAGE", FileSystemStorage(location=str(tmp_path)))
    block.h5p_content_json_path = f"https://old.example.com/{KEY}"
    assert block.h5p_player_content_url == f"https://old.example.com/{KEY}"


def test_player_url_without_storage_key_passes_through(block):
    block.h5p_content_json_path = "https://h5p.org/h5p/embed/123"
    assert block.h5p_player_content_url == "https://h5p.org/h5p/embed/123"


def test_player_url_rebuilt_against_current_storage(block):
    block.h5p_content_json_path = f"https://old-bucket.s3.amazonaws.com/{KEY}"
    assert block.h5p_player_content_url == f"https://cdn.example.com/{KEY}"


def test_resource_string_reads_packaged_file(block):
    assert block.resource_string("static/css/studio.css").strip()


def test_resource_string_falls_back_to_package_when_module_is_not_a_package(block, monkeypatch):
    """Python < 3.12 and the importlib_resources backport reject a plain module anchor."""
    real_files = block_module.importlib_resources.files

    def files(anchor):
        if anchor == block_module.__name__:
            raise TypeError("not a package")
        return real_files(anchor)

    monkeypatch.setattr(block_module.importlib_resources, "files", files)
    assert block.resource_string("static/css/studio.css").strip()


def test_studio_view_renders_real_template(block):
    frag = block.studio_view()
    assert frag.content.strip()
    assert frag.js_init_fn == "H5PStudioXBlock"
    assert frag.json_init_args["uploading_txt"] == "Uploading"


def test_student_view_passes_player_config(block):
    block.h5p_content_json_path = f"https://old.s3.amazonaws.com/{KEY}"
    block.save_freq = 30
    args = block.student_view().json_init_args
    assert args["h5pJsonPath"] == f"https://cdn.example.com/{KEY}"
    assert args["saveFreq"] == 30
    assert args["user_full_name"] == "Jane Doe"
    assert args["user_email"] == "jane@example.com"
    assert args["player_id"] == block.player_id


def test_student_view_without_autosave(block):
    assert block.student_view().json_init_args["saveFreq"] is False


def test_user_interaction_data_saves_post(block):
    request = Request.blank("/", method="POST", POST={"data": "state"})
    assert json.loads(block.user_interaction_data(request).body) == {"success": True}
    assert block.interaction_data == "state"


def test_user_interaction_data_ignores_get(block):
    request = Request.blank("/", method="GET")
    assert json.loads(block.user_interaction_data(request).body) == {"success": False}
    assert block.interaction_data is None


def test_user_interaction_data_logs_failure(block, caplog):
    request = Request.blank("/", method="POST", POST={})
    assert json.loads(block.user_interaction_data(request).body) == {"success": False}
    assert "Error while saving learner interaction data" in caplog.text


def test_studio_submit_settings_only(block):
    response = block.studio_submit(form())
    assert json.loads(response.body) == {"result": "success"}
    assert (block.display_name, block.show_frame, block.show_copyright) == ("Quiz", True, False)
    assert (block.show_h5p, block.show_fullscreen, block.has_score) == (True, True, True)
    assert (block.points, block.weight, block.icon_class) == (10, 1.5, "problem")
    assert block.h5p_content_json_path is None


def test_studio_submit_unscored_icon(block):
    block.studio_submit(form(is_scorable="false"))
    assert block.icon_class == "h5p"


def test_studio_submit_external_content_path(block):
    block.studio_submit(form(h5_content_path="https://h5p.org/h5p/embed/1"))
    assert block.h5p_content_json_path == "https://h5p.org/h5p/embed/1"


def test_studio_submit_upload_to_cloud(block):
    with mock.patch.object(block_module, "unpack_and_upload_on_cloud") as upload:
        block.studio_submit(form(h5p_content_bundle=bundle()))
    assert upload.call_args.args[1:] == (block_module.H5P_STORAGE, KEY)
    assert block.h5p_content_json_path == f"https://cdn.example.com/{KEY}"
    assert block.h5p_content_meta["name"] == "pkg.h5p"
    assert block.h5p_content_meta["size"] == 42
    assert "upload_time" in block.h5p_content_meta


def test_studio_submit_upload_to_local_fs(block, monkeypatch, tmp_path):
    monkeypatch.setattr(block_module, "H5P_STORAGE", FileSystemStorage(location=str(tmp_path)))
    monkeypatch.setattr(block_module, "H5P_ROOT", str(tmp_path))
    monkeypatch.setattr(block_module, "H5P_URL", "/media/h5pxblockmedia")
    with mock.patch.object(block_module, "unpack_package_local_path") as unpack:
        block.studio_submit(form(h5p_content_bundle=bundle()))
    assert unpack.call_args.args[1] == str(tmp_path / "org/course/blk")
    assert block.h5p_content_json_path == "/media/h5pxblockmedia/org/course/blk"


@pytest.mark.parametrize("points, weight, message", [
    ("abc", "1", "Points must be an integer"),
    ("-1", "1", "Points must be a positive integer"),
    ("1", "abc", "Weight must be a decimal number"),
    ("1", "-0.5", "Weight must be a positive decimal number"),
])
def test_validate_score_rejects(points, weight, message):
    with pytest.raises(JsonHandlerError) as exc:
        block_module.H5PPlayerXBlock.validate_score(points, weight)
    assert exc.value.status_code == 400
    assert exc.value.message == message


@pytest.mark.parametrize("points, weight, expected", [
    ("5", "2.5", (5, 2.5)),
    ("5", "2,5", (5, 2.5)),
    ("0", "", (0, "")),
])
def test_validate_score_accepts(points, weight, expected):
    assert block_module.H5PPlayerXBlock.validate_score(points, weight) == expected


def result(raw, maximum):
    return {"result": {"score": {"raw": raw, "max": maximum}}}


def call_result(block, payload):
    return json.loads(block.result_handler(json_request(payload)).body)["result"]


def test_result_handler_completion_without_score(block):
    assert call_result(block, result(1, 1)) == {"save_completion": True, "save_score": False}
    assert block.submission_status == "Completed"
    assert block.runtime.published[0][0] == "completion"


def test_result_handler_completion_failure_is_logged(block, caplog):
    block.runtime.publish_errors["completion"] = RuntimeError
    assert call_result(block, result(1, 1)) == {"save_completion": False, "save_score": False}
    assert "Error while marking completion" in caplog.text
    assert block.submission_status == "Not attempted"


def test_result_handler_past_due_skips_grading(block):
    block.has_score = True
    block.due = datetime.now(timezone.utc) - timedelta(days=1)
    assert call_result(block, result(1, 1)) == {"save_completion": True, "save_score": False}
    assert [event for event, _ in block.runtime.published] == ["completion"]


def test_result_handler_before_due_still_grades(block):
    block.has_score = True
    block.due = datetime.now(timezone.utc) + timedelta(days=1)
    assert call_result(block, result(1, 2))["save_score"] is True


def test_result_handler_publishes_weighted_grade(block):
    block.has_score = True
    block.points = 10
    assert call_result(block, result(3, 4)) == {"save_completion": True, "save_score": True}
    assert block.runtime.published[-1] == (
        "grade", {"value": 7.5, "max_value": 10, "only_if_higher": True}
    )
    assert block.weighted_score == 7.5


def test_result_handler_keeps_higher_weighted_score(block):
    block.has_score = True
    block.points = 10
    block.weighted_score = 9
    call_result(block, result(1, 2))
    assert block.weighted_score == 9


def test_result_handler_zero_max_scores_zero(block):
    block.has_score = True
    call_result(block, result(0, 0))
    assert block.runtime.published[-1][1]["value"] == 0


@pytest.mark.parametrize("payload", [{"result": None}, {"result": {"score": None}}])
def test_result_handler_without_score_data(block, payload):
    block.has_score = True
    assert call_result(block, payload)["save_score"] is False


def test_result_handler_unscored_block_never_grades(block):
    call_result(block, result(1, 1))
    assert [event for event, _ in block.runtime.published] == ["completion"]


def test_result_handler_retries_grade_for_old_runtime(block):
    block.has_score = True
    calls = []

    def publish(_block, event_type, data):
        calls.append((event_type, dict(data)))
        if event_type == "grade" and data["only_if_higher"]:
            raise TypeError("unexpected keyword")

    block.runtime.publish = publish
    assert call_result(block, result(1, 1))["save_score"] is True
    assert calls[-1][1]["only_if_higher"] is False


def test_result_handler_grade_failure_is_logged(block, caplog):
    block.has_score = True
    block.runtime.publish_errors["grade"] = RuntimeError
    assert call_result(block, result(1, 1)) == {"save_completion": True, "save_score": False}
    assert "Error while publishing score" in caplog.text


def test_is_past_due(block):
    assert block.is_past_due is False
    block.due = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert block.is_past_due is True


def test_workbench_scenarios():
    scenarios = block_module.H5PPlayerXBlock.workbench_scenarios()
    assert [name for name, _ in scenarios] == ["H5PPlayerXBlock", "Multiple H5PPlayerXBlock"]
