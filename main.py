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
from rich.console import Console


console = Console()
error_console = Console(stderr=True)


def fetch_transcript(
    video_id: str,
    languages: Optional[List[str]] = None,
    proxy_uri: Optional[str] = None,
    timeout: Optional[float] = None,  # Changed int to float
) -> Union[FetchedTranscript, List[Dict[str, Union[str, float]]]]:
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
    parser = argparse.ArgumentParser(description="Fetch YouTube video transcript")
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
        type=int,
    )
    args: argparse.Namespace = parser.parse_args()

    video_id_arg: str = args.video_id
    languages_arg: Optional[str] = args.languages
    # output_arg: Optional[str] = args.output # Not used directly in logic that mypy checks strictly
    proxy_arg: Optional[str] = args.proxy
    timeout_arg: Optional[float] = args.timeout  # Changed to float

    languages_list: Optional[List[str]] = (
        [lang.strip() for lang in languages_arg.split(",")] if languages_arg else None
    )

    # Define a type alias for the complex return type of fetch_transcript
    TranscriptReturnType: TypeAlias = Union[
        FetchedTranscript,
        List[Dict[str, Union[str, float]]],
    ]
    try:
        transcript_data: TranscriptReturnType = fetch_transcript(
            video_id_arg, languages_list, proxy_arg, timeout_arg
        )

        # Pass transcript_data directly as its type is now part of the Union for format_transcript
        formatted: str = format_transcript(transcript_data)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(formatted)
            console.print(
                f"Transcript saved to [cyan]{args.output}[/cyan]", style="green"
            )
        else:
            console.print(formatted)

    except VideoUnavailable:
        msg = (
            f"Error: Video '{video_id_arg}' is unavailable. "
            "This might mean it has been deleted or set to private. "
            "Please check the video ID and its public accessibility."
        )
        error_console.print(msg, style="bold red")
        sys.exit(1)
    except TranscriptsDisabled:
        msg = (
            f"Error: Transcripts are disabled for video '{video_id_arg}'. "
            "Subtitles may not be available or were disabled by the uploader."
        )
        error_console.print(msg, style="bold red")
        sys.exit(1)
    except NoTranscriptFound as e:
        msg = (
            f"Error: Could not find a transcript for video '{video_id_arg}' "
            "in the requested language(s)."
        )
        error_console.print(msg, style="bold red")
        if languages_list:
            error_console.print(
                f"  Attempted languages: {', '.join(languages_list)}", style="yellow"
            )
        error_console.print(f"  Details: {e}", style="dim")
        sys.exit(1)
    except (Timeout, RequestException) as e:
        msg = (
            "Error: A network issue occurred (e.g., timeout or connection problem). "
            "Please check your internet connection and try again."
        )
        error_console.print(msg, style="bold red")
        error_console.print(f"  Details: {e}", style="dim")
        sys.exit(1)
    except RequestBlocked:  # Changed from TooManyRequests
        msg = (
            "Error: Your request was blocked by YouTube. "
            "This may be due to too many requests or an IP block. "
            "Please try again later or use a proxy."
        )
        error_console.print(msg, style="bold red")
        sys.exit(1)
    except Exception as e:
        msg = f"An unexpected error occurred. Details: {e}"
        error_console.print(msg, style="bold red")
        sys.exit(1)


if __name__ == "__main__":
    main()
