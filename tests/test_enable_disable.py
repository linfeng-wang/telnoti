"""Tests for telnoti.disable() / telnoti.enable()."""

from unittest.mock import patch, MagicMock

import telnoti
import telnoti.core as core


def _reset():
    core._state["token"] = "fake-token"
    core._state["chat_id"] = "12345"
    core._state["initialized"] = True
    core._state["enabled"] = True


# ---------------------------------------------------------------------------
# disable / enable state
# ---------------------------------------------------------------------------

def test_disable_sets_state():
    _reset()
    telnoti.disable()
    assert core._state["enabled"] is False


def test_enable_sets_state():
    _reset()
    telnoti.disable()
    telnoti.enable()
    assert core._state["enabled"] is True


def test_enabled_by_default():
    # Fresh import already has enabled=True; after a full reset it should too.
    _reset()
    assert core._state["enabled"] is True


# ---------------------------------------------------------------------------
# send / done / error suppressed while disabled
# ---------------------------------------------------------------------------

@patch("telnoti.core.requests.post")
def test_send_suppressed_when_disabled(mock_post):
    _reset()
    telnoti.disable()
    telnoti.send("should not be sent")
    mock_post.assert_not_called()


@patch("telnoti.core.requests.post")
def test_done_suppressed_when_disabled(mock_post):
    _reset()
    telnoti.disable()
    telnoti.done("all good")
    mock_post.assert_not_called()


@patch("telnoti.core.requests.post")
def test_error_suppressed_when_disabled(mock_post):
    _reset()
    telnoti.disable()
    telnoti.error(ValueError("oops"))
    mock_post.assert_not_called()


@patch("telnoti.core.requests.post")
def test_send_image_suppressed_when_disabled(mock_post, tmp_path):
    _reset()
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG\r\n")
    telnoti.disable()
    telnoti.send_image(str(img))
    mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# messages are sent after re-enable
# ---------------------------------------------------------------------------

@patch("telnoti.core.requests.post")
def test_send_works_after_enable(mock_post):
    _reset()
    telnoti.disable()
    telnoti.enable()
    telnoti.send("hello")
    mock_post.assert_called_once()


@patch("telnoti.core.requests.post")
def test_send_image_works_after_enable(mock_post, tmp_path):
    _reset()
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG\r\n")
    telnoti.disable()
    telnoti.enable()
    telnoti.send_image(str(img))
    mock_post.assert_called_once()


# ---------------------------------------------------------------------------
# idempotency
# ---------------------------------------------------------------------------

@patch("telnoti.core.requests.post")
def test_double_disable_idempotent(mock_post):
    _reset()
    telnoti.disable()
    telnoti.disable()
    telnoti.send("nope")
    mock_post.assert_not_called()


@patch("telnoti.core.requests.post")
def test_double_enable_idempotent(mock_post):
    _reset()
    telnoti.enable()
    telnoti.enable()
    telnoti.send("yes")
    mock_post.assert_called_once()
