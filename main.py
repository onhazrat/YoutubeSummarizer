from youtube_transcript_api._api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig
import argparse

def fetch_transcript(video_id, languages=None, proxy_uri=None):
    if proxy_uri:
        ytt_api = YouTubeTranscriptApi(proxy_config=GenericProxyConfig(http_url=proxy_uri))
    else:
        ytt_api = YouTubeTranscriptApi()
    if languages:
        return ytt_api.fetch(video_id, languages=languages)
    else:
        return ytt_api.get_transcript(video_id)

def format_transcript(transcript):
    return '\n'.join([f"[{item['start']:.2f}] {item['text']}" for item in transcript])

def main():
    parser = argparse.ArgumentParser(description='Fetch YouTube video transcript')
    parser.add_argument('video_id', help='YouTube video ID to fetch transcript for')
    parser.add_argument('-l', '--languages', help='Comma-separated list of language codes (e.g., en,fa,de)')
    parser.add_argument('-o', '--output', help='Output file path to save the transcript (default: print to terminal)', default=None)
    parser.add_argument('--proxy', help='HTTP proxy URI (default: no proxy)', default=None)
    args = parser.parse_args()
    languages = [lang.strip() for lang in args.languages.split(',')] if args.languages else None
    transcript = fetch_transcript(args.video_id, languages, args.proxy)
    formatted = format_transcript(transcript)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(formatted)
    else:
        print(formatted)

if __name__ == "__main__":
    main()
