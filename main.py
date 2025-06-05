import sys
from typing import List, Optional, Dict, Union, Any, cast, TypeAlias
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    FetchedTranscript,
    VideoUnavailable,
    RequestBlocked,  # Changed from TooManyRequests
    TranscriptsDisabled,
    NoTranscriptFound,
)

# youtube_transcript_api.errors is not the correct import path for exceptions
from requests.exceptions import RequestException, Timeout
from requests import Session
import argparse
import logging
from rich.console import Console
from rich.logging import RichHandler  # Added


console = Console()
# error_console removed as it's no longer used. Logging handles errors.
logger = logging.getLogger("youtube_transcript_cli")


def fetch_transcript(
    video_id: str,
    languages: Optional[List[str]] = None,
    proxy_uri: Optional[str] = None,
    timeout: Optional[float] = None,
) -> Union[FetchedTranscript, List[Dict[str, Union[str, float]]]]:
    logger.debug(
        f"Fetching transcript for video_id='{video_id}', languages={languages}, "
        f"proxy_uri='{proxy_uri}', timeout={timeout}"
    )
    http_client_args: Dict[str, Any] = {}
    session: Optional[Session] = None

    if timeout is not None or proxy_uri:
        session = Session()
        if timeout is not None:
            session.timeout = float(timeout)  # type: ignore[attr-defined]
        if proxy_uri:
            session.proxies = {"http": proxy_uri, "https": proxy_uri}
        http_client_args["http_client"] = session

    # If only proxy_uri is provided and no timeout, YouTubeTranscriptApi
    # can handle GenericProxyConfig itself. However, to unify, if we create a session
    # for proxy, we use it. If proxy_uri is given but timeout is not,
    # the above logic already correctly creates a session and sets proxies.
    # If neither timeout nor proxy_uri, http_client_args remains empty.

    # The only case not explicitly covered by session is when proxy_uri is set
    # but timeout is NOT. The original code used GenericProxyConfig for that.
    # Let's refine: if only proxy_uri, we can let ytt_api handle it internally
    # or use our session. For consistency and to manage session lifecycle in one place,
    # using our session is cleaner if any session-related param (timeout, proxy) is given.

    if (
        not http_client_args and proxy_uri
    ):  # Should not happen with current logic, but defensive
        # This case is if we decided *not* to create a session just for proxy
        # ytt_api = YouTubeTranscriptApi(proxy_config=GenericProxyConfig(http_url=proxy_uri))
        # However, the unified logic above now always creates a session if proxy_uri is present.
        pass

    ytt_api = YouTubeTranscriptApi(**http_client_args)

    # Deprecation note: get_transcript is deprecated, fetch is preferred.
    # The original code used get_transcript if no languages were specified.
    # ytt_api.fetch() can handle empty/None languages to get default.
    if languages:
        result: FetchedTranscript = ytt_api.fetch(video_id, languages=languages)
        return result
    else:
        raw_result: List[Dict[str, Union[str, float]]] = ytt_api.get_transcript(
            video_id
        )
        return raw_result


def format_transcript(
    transcript_items: Union[FetchedTranscript, List[Dict[str, Any]]],
) -> str:
    # This function now expects an iterable of dictionaries that must contain 'start' and 'text'.
    # Both FetchedTranscript items and get_transcript items will satisfy this.
    # Note: FetchedTranscript is directly iterable.
    return "\n".join(
        [
            f"[{cast(Dict[str, Any], item)['start']:.2f}] {cast(Dict[str, Any], item)['text']}"
            for item in transcript_items
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch YouTube video transcript",
        formatter_class=argparse.RawTextHelpFormatter,  # To better format help text
    )
    parser.add_argument(
        "video_id", type=str, help="YouTube video ID to fetch transcript for"
    )
    parser.add_argument(
        "-l",
        "--languages",
        help="Comma-separated list of language codes (e.g., en,fa,de)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path to save the transcript (default: print to terminal)",
        default=None,
    )
    parser.add_argument(
        "--proxy", help="HTTP proxy URI (default: no proxy)", default=None
    )
    parser.add_argument(
        "--timeout",
        help="Timeout for fetching transcript in seconds",
        default=None,
        type=int,  # argparse will handle conversion to int
    )

    # Logging verbosity arguments
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: WARNING).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_const",
        const="INFO",
        dest="log_level_flag",
        help="Enable verbose output (INFO level).",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_const",
        const="DEBUG",
        dest="log_level_flag",
        help="Enable debug output (DEBUG level). Overrides -v and --log-level.",
    )

    args: argparse.Namespace = parser.parse_args()

    # Determine effective log level
    log_level_str: str = args.log_level_flag if args.log_level_flag else args.log_level
    numeric_log_level = getattr(logging, log_level_str.upper(), logging.WARNING)

    # Configure the named logger with RichHandler
    logger.setLevel(logging.DEBUG)  # Set logger to lowest level, handler filters
    logger.handlers.clear()  # Remove any default or basicConfig handlers
    rich_handler = RichHandler(
        level=numeric_log_level,
        rich_tracebacks=True,
        markup=True,  # Allow rich markup in log messages
        show_path=False,
        log_time_format="[%X]",  # Time only HH:MM:SS
    )
    logger.addHandler(rich_handler)

    # No need to set level on logger.handlers[0] specifically if clearing and adding new one.
    # The RichHandler's level will control what it emits.

    logger.debug(f"Parsed arguments: {args}")  # Will use % formatting if changed below
    logger.debug(
        f"Effective log level set to: {log_level_str} ({numeric_log_level})"
    )  # Same

    video_id_arg: str = args.video_id
    languages_arg: Optional[str] = args.languages
    proxy_arg: Optional[str] = args.proxy
    timeout_arg: Optional[float] = args.timeout

    languages_list: Optional[List[str]] = (
        [lang.strip() for lang in languages_arg.split(",")] if languages_arg else None
    )

    TranscriptReturnType: TypeAlias = Union[
        FetchedTranscript, List[Dict[str, Union[str, float]]]
    ]

    try:
        logger.info("Fetching transcript for video ID: [bold]%s[/bold]", video_id_arg)
        transcript_data: TranscriptReturnType = fetch_transcript(
            video_id_arg, languages_list, proxy_arg, timeout_arg
        )

        formatted: str = format_transcript(transcript_data)

        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(formatted)
                # Use markup with logger.info (extra={"markup": True} is redundant due to handler setting)
                logger.info(
                    "Transcript successfully saved to [cyan]%s[/cyan]", args.output
                )
            except IOError as e:
                logger.error(
                    "Failed to write transcript to file %s: %s", args.output, e
                )
                sys.exit(1)
        else:
            console.print(formatted)

    except VideoUnavailable:
        msg = (
            f"Video '{video_id_arg}' is unavailable. "
            "This might mean it has been deleted or set to private. "
            "Please check the video ID and its public accessibility."
        )
        logger.error(msg)
        sys.exit(1)
    except TranscriptsDisabled:
        msg = (
            f"Transcripts are disabled for video '{video_id_arg}'. "
            "Subtitles may not be available or were disabled by the uploader."
        )
        logger.error(msg)
        sys.exit(1)
    except NoTranscriptFound as e:
        msg = (
            f"Could not find a transcript for video '{video_id_arg}' "
            "in the requested language(s)."
        )
        details = str(e)
        if languages_list:
            # Example of using markup in log parts if desired, though RichHandler style is often enough
            # Break long line for flake8
            languages_str = ", ".join(languages_list)
            part1 = msg
            part2 = f" Tried languages: [yellow]{languages_str}[/yellow]."
            part3 = f" Details: [dim]{details}[/dim]"
            full_log_msg = f"{part1}{part2}{part3}"
            logger.error(full_log_msg)  # extra={"markup": True} is redundant
        else:
            logger.error(
                "%s Details: [dim]%s[/dim]", msg, details
            )  # extra={"markup": True} is redundant
        sys.exit(1)
    except (Timeout, RequestException) as e:
        msg = (
            "A network issue occurred (e.g., timeout or connection problem). "
            "Please check your internet connection and try again."
        )
        logger.error(
            "%s Details: [dim]%s[/dim]", msg, e
        )  # extra={"markup": True} is redundant
        sys.exit(1)
    except RequestBlocked:
        msg = (
            "Your request was blocked by YouTube. "
            "This may be due to too many requests or an IP block. "
            "Please try again later or use a proxy."
        )
        logger.error(msg)
        sys.exit(1)
    except Exception as e:
        msg = "An unexpected error occurred."
        logger.exception("%s Details: %s", msg, e)  # logger.exception handles traceback
        sys.exit(1)


if __name__ == "__main__":
    main()
