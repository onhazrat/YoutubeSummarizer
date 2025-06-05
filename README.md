# YouTube Transcript CLI Tool

A simple command-line tool to fetch and save YouTube video transcripts (subtitles) in your preferred language(s).

## Features
- Fetches subtitles/transcripts for any public YouTube video
- Supports multiple languages (e.g., English, Farsi, German, etc.)
- If no language is specified, automatically fetches the main (default) subtitle
- Outputs transcript to the terminal or saves to a file
- Optional HTTP proxy support
- Includes a man page for command-line help

## Requirements
- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (for fast Python package management)
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) (installed via `uv`)

## Installation

1. Clone this repository or copy the files to your project directory.
2. Install dependencies using [uv](https://github.com/astral-sh/uv):

```sh
uv pip install -e .
```

This will install all dependencies specified in `pyproject.toml`.

## Usage

Run the script from the command line:

```sh
python main.py VIDEO_ID [options]
```

- `VIDEO_ID`: The YouTube video ID (e.g., `dQw4w9WgXcQ`)

### Options

- `-l`, `--languages`  
  Comma-separated list of language codes to try (e.g., `en,fa,de`). If omitted, the main (default) subtitle will be fetched.

- `-o`, `--output`  
  Output file path to save the transcript. If omitted, the transcript is printed to the terminal.

- `--proxy`  
  HTTP proxy URI. If omitted, no proxy is used.

### Examples

Fetch the main (default) subtitle and print to terminal:

```sh
python main.py dQw4w9WgXcQ
```

Fetch only German subtitles and print to terminal:

```sh
python main.py dQw4w9WgXcQ -l de
```

Fetch English subtitles and save to a file:

```sh
python main.py dQw4w9WgXcQ -l en -o transcript.txt
```

Fetch subtitles using a proxy:

```sh
python main.py dQw4w9WgXcQ --proxy http://127.0.0.1:2081
```

## Proxy Configuration

You can specify a proxy on the command line with the `--proxy` option. If not provided, the tool connects directly.

## Output Format

The transcript is formatted as:

```
[start_time] text
```

Example:

```
[0.00] Never gonna give you up
[3.50] Never gonna let you down
```

## Man Page

A man page (`youtube_transcript.1`) is included. To view it:

```sh
man ./youtube_transcript.1
```

To install it system-wide:

```sh
sudo cp youtube_transcript.1 /usr/local/share/man/man1/
man youtube_transcript
```

## License

MIT License
