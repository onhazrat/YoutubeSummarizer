from typing import List, Dict, Any, Union
import pytest
from unittest.mock import patch, MagicMock
from main import fetch_transcript
from requests.exceptions import Timeout as RequestsTimeout
from requests.exceptions import RequestException  # Added
import main as cli_main  # Added
import argparse  # Added
import logging  # Added for logging level constants
from youtube_transcript_api import (  # Corrected import path
    VideoUnavailable,
    TranscriptsDisabled,
    NoTranscriptFound,
    RequestBlocked,
)

# from youtube_transcript_api import FetchedTranscript # Not strictly needed for tests if using Any


# Define a type for transcript items for clarity in tests
TranscriptItem = Dict[str, Union[str, float]]
MockTranscriptResult = List[TranscriptItem]


# Default args for mocking parse_args
def_args_dict = {  # Reformatted to be multi-line
    "video_id": "test_id",
    "languages": None,
    "output": None,
    "proxy": None,
    "timeout": None,
    "log_level": "WARNING",
    "log_level_flag": None,
}


# Helper to create Namespace, so we can easily override parts for specific tests
def create_args_namespace(**overrides: Any) -> argparse.Namespace:
    return argparse.Namespace(**{**def_args_dict, **overrides})


sample_transcript_data: MockTranscriptResult = [  # Added type hint
    {"text": "Hello world", "start": 0.0, "duration": 1.0}
]
formatted_sample_transcript: str = "[0.00] Hello world"  # Added type hint


# Test for timeout occurrence
@patch("main.YouTubeTranscriptApi")
def test_fetch_transcript_timeout_occurs(mock_ytt_api_class: MagicMock) -> None:
    """
    Tests that fetch_transcript raises a Timeout exception (or a wrapped one)
    when the YouTubeTranscriptApi().get_transcript() or .fetch() call times out.
    """
    mock_api_instance: MagicMock = MagicMock()
    # Simulate the timeout occurring during the actual transcript fetch call
    timeout_message: str = "Simulated transcript fetch timeout"
    mock_api_instance.get_transcript.side_effect = RequestsTimeout(timeout_message)
    mock_api_instance.fetch.side_effect = RequestsTimeout(timeout_message)
    mock_ytt_api_class.return_value = mock_api_instance

    video_id: str = (
        "any_video_id"  # This ID won't be used by the mock to fetch real data
    )

    with pytest.raises(RequestsTimeout):
        fetch_transcript(video_id, timeout=0.1)  # Trigger code path that uses timeout

    # Also test the path where languages are provided
    with pytest.raises(RequestsTimeout):
        fetch_transcript(video_id, languages=["en"], timeout=0.1)


@patch("main.YouTubeTranscriptApi")
def test_fetch_transcript_successful_with_timeout(
    mock_ytt_api_class: MagicMock,
) -> None:
    """
    Tests that fetch_transcript returns a transcript successfully when a timeout is provided
    and the operation completes within the timeout.
    """
    mock_api_instance: MagicMock = MagicMock()
    dummy_transcript: MockTranscriptResult = [
        {"text": "hello", "start": 0.0, "duration": 1.0}
    ]
    mock_api_instance.get_transcript.return_value = dummy_transcript
    mock_api_instance.fetch.return_value = (
        dummy_transcript  # for when languages are specified
    )
    mock_ytt_api_class.return_value = mock_api_instance

    video_id: str = "test_video_id_success"
    # The actual return type from main.fetch_transcript is
    # Union[FetchedTranscript, List[Dict[str, Union[str, float]]]].
    # For testing purposes, we often use Any if the exact structure
    # isn't crucial for the test's assertions, or a simplified version
    # if we're mocking the return value.
    transcript: Any
    transcript = fetch_transcript(video_id, timeout=5)

    assert transcript is not None
    # Assuming transcript is list-like and contains dicts with "text"
    assert transcript[0]["text"] == "hello"
    # Check if YouTubeTranscriptApi was initialized with an http_client
    # (our session)
    args, kwargs = mock_ytt_api_class.call_args
    assert "http_client" in kwargs
    assert kwargs["http_client"] is not None
    assert hasattr(kwargs["http_client"], "timeout")
    assert kwargs["http_client"].timeout == 5


@patch("main.YouTubeTranscriptApi")
def test_fetch_transcript_successful_without_timeout(
    mock_ytt_api_class: MagicMock,
) -> None:
    """
    Tests that fetch_transcript returns a transcript successfully when no timeout is provided.
    """
    mock_api_instance: MagicMock = MagicMock()
    dummy_transcript: MockTranscriptResult = [
        {"text": "world", "start": 0.0, "duration": 1.0}
    ]
    mock_api_instance.get_transcript.return_value = dummy_transcript
    mock_api_instance.fetch.return_value = dummy_transcript
    mock_ytt_api_class.return_value = mock_api_instance

    video_id: str = "test_video_id_no_timeout"
    transcript: Any = fetch_transcript(video_id)  # No timeout argument

    assert transcript is not None
    assert transcript[0]["text"] == "world"
    # Check if YouTubeTranscriptApi was initialized *without* an http_client (no session explicitly passed)
    # if no timeout is given, and no proxy, it should be called with no args.
    args, kwargs = mock_ytt_api_class.call_args
    assert "http_client" not in kwargs or kwargs["http_client"] is None


@patch("main.YouTubeTranscriptApi")
@patch("main.Session")
def test_fetch_transcript_with_proxy_and_timeout(
    mock_session_class: MagicMock, mock_ytt_api_class: MagicMock
) -> None:
    """
    Tests that fetch_transcript configures session with proxy when both proxy
    and timeout are given.
    """
    mock_api_instance: MagicMock = MagicMock()
    dummy_transcript: MockTranscriptResult = [
        {"text": "proxy test", "start": 0.0, "duration": 1.0}
    ]
    mock_api_instance.get_transcript.return_value = dummy_transcript
    mock_ytt_api_class.return_value = mock_api_instance

    mock_session_instance: MagicMock = MagicMock()
    mock_session_class.return_value = mock_session_instance

    video_id: str = "test_video_proxy_timeout"
    proxy_uri: str = "http://localhost:8080"
    timeout_val: int = 10

    transcript: Any = fetch_transcript(
        video_id, proxy_uri=proxy_uri, timeout=timeout_val
    )

    assert transcript is not None
    mock_session_class.assert_called_once()  # Session should be created
    mock_ytt_api_class.assert_called_once()

    # Check that the session instance was configured with proxies
    assert mock_session_instance.proxies == {"http": proxy_uri, "https": proxy_uri}
    # Check that this session instance was passed to YouTubeTranscriptApi
    http_client_arg = mock_ytt_api_class.call_args.kwargs.get(
        "http_client"
    )  # noqa: E501
    assert http_client_arg == mock_session_instance
    assert mock_ytt_api_class.call_args.kwargs.get("proxy_config") is None


@patch("main.YouTubeTranscriptApi")
@patch("main.Session")
def test_fetch_transcript_with_proxy_only(
    mock_session_class: MagicMock, mock_ytt_api_class: MagicMock
) -> None:
    """
    Tests that fetch_transcript uses GenericProxyConfig when only proxy is given.
    """
    mock_api_instance: MagicMock = MagicMock()
    dummy_transcript: MockTranscriptResult = [
        {"text": "proxy only", "start": 0.0, "duration": 1.0}
    ]
    mock_api_instance.get_transcript.return_value = dummy_transcript
    mock_ytt_api_class.return_value = mock_api_instance

    video_id: str = "test_video_proxy_only"
    proxy_uri: str = "http://localhost:8080"

    transcript: Any = fetch_transcript(video_id, proxy_uri=proxy_uri)

    assert transcript is not None
    mock_session_class.assert_called_once()  # Session IS now created due to refactor
    mock_ytt_api_class.assert_called_once()

    # Check that YouTubeTranscriptApi was called with http_client (the session)
    # and NOT with proxy_config
    call_kwargs = mock_ytt_api_class.call_args.kwargs
    assert call_kwargs.get("http_client") is not None  # Session should be passed
    assert call_kwargs.get("proxy_config") is None
    # Further check if session passed has the proxy configured (optional here, but good for completeness)
    assert call_kwargs.get("http_client").proxies == {
        "http": proxy_uri,
        "https": proxy_uri,
    }


# --- Tests for main() function ---
# Imports moved to the top
# Old def_args removed, sample_transcript_data and formatted_sample_transcript are already defined with type hints above.


@patch("argparse.ArgumentParser.parse_args")
@patch("main.fetch_transcript")
def test_main_video_unavailable(
    mock_fetch_transcript: MagicMock,
    mock_parse_args: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_parse_args.return_value = create_args_namespace()
    mock_fetch_transcript.side_effect = VideoUnavailable(def_args_dict["video_id"])
    with pytest.raises(SystemExit) as e_info:
        cli_main.main()
    assert e_info.value.code == 1
    # Assuming DEBUG logs from main() might also be present if default test level is low enough
    assert len(caplog.records) >= 1
    error_record = next(
        r for r in reversed(caplog.records) if r.levelname == "ERROR"
    )  # Get the last ERROR
    assert "Video 'test_id' is unavailable" in error_record.message
    assert "Please check the video ID" in error_record.message


@patch("argparse.ArgumentParser.parse_args")
@patch("main.fetch_transcript")
def test_main_transcripts_disabled(
    mock_fetch_transcript: MagicMock,
    mock_parse_args: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_parse_args.return_value = create_args_namespace()
    mock_fetch_transcript.side_effect = TranscriptsDisabled(def_args_dict["video_id"])
    with pytest.raises(SystemExit) as e_info:
        cli_main.main()
    assert e_info.value.code == 1
    assert len(caplog.records) >= 1
    error_record = next(r for r in reversed(caplog.records) if r.levelname == "ERROR")
    assert "Transcripts are disabled for video 'test_id'" in error_record.message
    assert "disabled by the uploader" in error_record.message


@patch("argparse.ArgumentParser.parse_args")
@patch("main.fetch_transcript")
def test_main_no_transcript_found(
    mock_fetch_transcript: MagicMock,
    mock_parse_args: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_parse_args.return_value = create_args_namespace()
    mock_fetch_transcript.side_effect = NoTranscriptFound(
        def_args_dict["video_id"], ["en"], {}
    )
    with pytest.raises(SystemExit) as e_info:
        cli_main.main()
    assert e_info.value.code == 1
    assert len(caplog.records) >= 1
    error_record = next(r for r in reversed(caplog.records) if r.levelname == "ERROR")
    assert "Could not find a transcript for video 'test_id'" in error_record.message


@patch("argparse.ArgumentParser.parse_args")
@patch("main.fetch_transcript")
def test_main_no_transcript_found_with_langs(
    mock_fetch_transcript: MagicMock,
    mock_parse_args: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    video_id = "test_id_langs"
    langs = ["es", "fr"]
    mock_parse_args.return_value = create_args_namespace(
        video_id=video_id, languages=",".join(langs)
    )
    mock_fetch_transcript.side_effect = NoTranscriptFound(video_id, langs, {})
    with pytest.raises(SystemExit) as e_info:
        cli_main.main()
    assert e_info.value.code == 1
    assert len(caplog.records) >= 1
    error_record = next(r for r in reversed(caplog.records) if r.levelname == "ERROR")
    assert f"Could not find a transcript for video '{video_id}'" in error_record.message
    assert f"Tried languages: {', '.join(langs)}." in error_record.message


@patch("argparse.ArgumentParser.parse_args")
@patch("main.fetch_transcript")
def test_main_network_timeout(
    mock_fetch_transcript: MagicMock,
    mock_parse_args: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_parse_args.return_value = create_args_namespace()
    mock_fetch_transcript.side_effect = RequestsTimeout("Connection timed out")
    with pytest.raises(SystemExit) as e_info:
        cli_main.main()
    assert e_info.value.code == 1
    assert len(caplog.records) >= 1
    error_record = next(r for r in reversed(caplog.records) if r.levelname == "ERROR")
    assert "A network issue occurred" in error_record.message
    assert "Connection timed out" in error_record.message


@patch("argparse.ArgumentParser.parse_args")
@patch("main.fetch_transcript")
def test_main_network_request_exception(
    mock_fetch_transcript: MagicMock,
    mock_parse_args: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_parse_args.return_value = create_args_namespace()
    mock_fetch_transcript.side_effect = RequestException("Some other network problem")
    with pytest.raises(SystemExit) as e_info:
        cli_main.main()
    assert e_info.value.code == 1
    assert len(caplog.records) >= 1
    error_record = next(r for r in reversed(caplog.records) if r.levelname == "ERROR")
    assert "A network issue occurred" in error_record.message
    assert "Some other network problem" in error_record.message


@patch("argparse.ArgumentParser.parse_args")
@patch("main.fetch_transcript")
def test_main_request_blocked(  # Renamed test
    mock_fetch_transcript: MagicMock,
    mock_parse_args: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_parse_args.return_value = create_args_namespace()
    mock_fetch_transcript.side_effect = RequestBlocked(def_args_dict["video_id"])
    with pytest.raises(SystemExit) as e_info:
        cli_main.main()
    assert e_info.value.code == 1
    assert len(caplog.records) >= 1
    error_record = next(r for r in reversed(caplog.records) if r.levelname == "ERROR")
    assert "Your request was blocked by YouTube" in error_record.message


@patch("argparse.ArgumentParser.parse_args")
@patch("main.fetch_transcript")
def test_main_generic_exception(
    mock_fetch_transcript: MagicMock,
    mock_parse_args: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_parse_args.return_value = create_args_namespace()
    mock_fetch_transcript.side_effect = Exception("A very generic error")
    with pytest.raises(SystemExit) as e_info:
        cli_main.main()
    assert e_info.value.code == 1
    assert len(caplog.records) >= 1
    error_record = next(r for r in reversed(caplog.records) if r.levelname == "ERROR")
    assert error_record.levelname == "ERROR"
    assert "An unexpected error occurred." in error_record.message
    assert "A very generic error" in error_record.message


@patch("argparse.ArgumentParser.parse_args")
@patch("main.fetch_transcript")
def test_main_successful_stdout(
    mock_fetch_transcript: MagicMock,
    mock_parse_args: MagicMock,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,  # Added caplog
) -> None:
    mock_parse_args.return_value = create_args_namespace()  # Use helper
    mock_fetch_transcript.return_value = sample_transcript_data

    # No SystemExit is raised for success
    cli_main.main()

    captured = capsys.readouterr()
    assert captured.out.strip() == formatted_sample_transcript

    # Check logs based on default log level (WARNING)
    cli_log_records = [r for r in caplog.records if r.name == "youtube_transcript_cli"]
    assert not any(r.levelno < logging.WARNING for r in cli_log_records)


@patch("argparse.ArgumentParser.parse_args")
@patch("main.fetch_transcript")
@patch("builtins.open", new_callable=MagicMock)
def test_main_successful_file_output(
    mock_open: MagicMock,
    mock_fetch_transcript: MagicMock,
    mock_parse_args: MagicMock,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    video_id = "test_id_file"
    output_file = "out.txt"
    # Set log_level_flag to INFO to ensure the "saved" message is logged and captured
    mock_parse_args.return_value = create_args_namespace(
        video_id=video_id, output=output_file, log_level_flag="INFO"
    )
    mock_fetch_transcript.return_value = sample_transcript_data

    # Configure mock_open explicitly for context manager behavior
    mock_f_object = MagicMock()
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = mock_f_object
    mock_open.return_value = mock_context_manager

    cli_main.main()

    mock_open.assert_called_once_with(output_file, "w", encoding="utf-8")
    mock_f_object.write.assert_called_once_with(formatted_sample_transcript)

    # Check log for success message
    # Expect DEBUG for args, INFO for fetching, INFO for saved (if log level is INFO)
    assert (
        len(caplog.records) >= 3
    )  # DEBUG Parsed args, DEBUG Effective log level, INFO Fetching, INFO Saved

    cli_log_records = [r for r in caplog.records if r.name == "youtube_transcript_cli"]
    info_records = [r for r in cli_log_records if r.levelname == "INFO"]

    assert (
        len(info_records) == 2
    )  # "Fetching..." and "Transcript successfully saved..."
    assert (
        f"Fetching transcript for video ID: [bold]{video_id}[/bold]"
        in info_records[0].message
    )
    assert (
        f"Transcript successfully saved to [cyan]{output_file}[/cyan]"
        in info_records[1].message
    )

    # Check stdout is empty
    captured_stdout = capsys.readouterr().out
    assert captured_stdout == ""


# Corrected and de-duplicated verbosity tests start here (lines after the removed block)
# Tests for different verbosity levels
@patch("argparse.ArgumentParser.parse_args")
@patch("main.fetch_transcript")
def test_main_log_level_default_warning(
    mock_fetch_transcript: MagicMock,
    mock_parse_args: MagicMock,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_parse_args.return_value = create_args_namespace(
        log_level="WARNING", log_level_flag=None
    )
    mock_fetch_transcript.return_value = sample_transcript_data

    cli_main.main()

    cli_log_records = [r for r in caplog.records if r.name == "youtube_transcript_cli"]
    for record in cli_log_records:
        assert record.levelno >= logging.WARNING

    mock_fetch_transcript.side_effect = VideoUnavailable(def_args_dict["video_id"])
    with pytest.raises(SystemExit):
        caplog.clear()
        cli_main.main()
    assert any(
        r.levelname == "ERROR" and "Video 'test_id' is unavailable" in r.message
        for r in caplog.records
        if r.name == "youtube_transcript_cli"  # Ensure we check our logger
    )

    captured = capsys.readouterr()  # From the first successful cli_main.main() call
    assert captured.out.strip() == formatted_sample_transcript


@patch("argparse.ArgumentParser.parse_args")
@patch("main.fetch_transcript")
def test_main_log_level_verbose_info(
    mock_fetch_transcript: MagicMock,
    mock_parse_args: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_parse_args.return_value = create_args_namespace(log_level_flag="INFO")
    mock_fetch_transcript.return_value = sample_transcript_data
    cli_main.main()
    cli_logs = [r for r in caplog.records if r.name == "youtube_transcript_cli"]
    assert any(
        r.levelname == "INFO" and "Fetching transcript for video ID:" in r.message
        for r in cli_logs
    )
    assert not any(
        r.levelname == "DEBUG" and "Fetching transcript for video_id=" in r.message
        for r in cli_logs
    )
    assert not any(
        r.levelname == "DEBUG"
        and ("Parsed arguments:" in r.message or "Effective log level" in r.message)
        for r in cli_logs
    )


@patch("argparse.ArgumentParser.parse_args")
@patch("main.fetch_transcript")
def test_main_log_level_debug(
    mock_fetch_transcript: MagicMock,
    mock_parse_args: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_parse_args.return_value = create_args_namespace(log_level_flag="DEBUG")
    mock_fetch_transcript.return_value = sample_transcript_data
    cli_main.main()
    cli_logs = [r for r in caplog.records if r.name == "youtube_transcript_cli"]
    assert any(
        r.levelname == "DEBUG" and "Parsed arguments:" in r.message for r in cli_logs
    )
    assert any(
        r.levelname == "DEBUG" and "Effective log level set to: DEBUG" in r.message
        for r in cli_logs
    )
    assert any(
        r.levelname == "DEBUG" and "Fetching transcript for video_id=" in r.message
        for r in cli_logs
    )
    assert any(
        r.levelname == "INFO" and "Fetching transcript for video ID:" in r.message
        for r in cli_logs
    )
