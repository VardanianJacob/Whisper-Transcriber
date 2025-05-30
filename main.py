import os
import argparse
import json
from api.whisper import transcribe_audio
from utils.save import save_transcript_to_file
from config import (
    DEFAULT_LANGUAGE,
    DEFAULT_RESPONSE_FORMAT,
    DEFAULT_TIMESTAMP_GRANULARITIES
)

def str2bool(v):
    return str(v).lower() in ("yes", "true", "t", "1")

def main():
    parser = argparse.ArgumentParser(description="🎙️ Transcribe audio using Lemonfox Whisper-compatible API")

    parser.add_argument("file", nargs="?", help="Path to the audio file")
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, help="Language of the audio")
    parser.add_argument("--prompt", help="Custom prompt for the model")
    parser.add_argument("--speaker_labels", type=str2bool, nargs="?", const=True, default=True, help="Enable speaker labeling")
    parser.add_argument("--translate", type=str2bool, nargs="?", const=True, default=False, help="Translate output to English")
    parser.add_argument("--response_format", default=DEFAULT_RESPONSE_FORMAT, choices=["json", "text", "srt", "verbose_json"], help="Format of response")
    parser.add_argument("--timestamp_granularities", nargs="+", default=DEFAULT_TIMESTAMP_GRANULARITIES, help="Timestamp detail level: segment, word")
    parser.add_argument("--callback_url", help="Webhook URL for async processing")
    parser.add_argument("--min_speakers", type=int, help="Minimum number of speakers")
    parser.add_argument("--max_speakers", type=int, help="Maximum number of speakers")

    args = parser.parse_args()

    if not args.file:
        args.file = input("📁 Enter path to audio file: ").strip()

    if not os.path.exists(args.file):
        print("❌ File does not exist.")
        return

    file_size = os.path.getsize(args.file) / (1024 * 1024)
    if file_size > 100:
        print(f"⚠️ File size is {file_size:.2f} MB, which exceeds the 100MB upload limit.")
        return

    print("📡 Uploading to Whisper API...")

    try:
        result = transcribe_audio(
            file_path=args.file,
            language=args.language,
            prompt=args.prompt,
            speaker_labels=args.speaker_labels,
            translate=args.translate,
            response_format=args.response_format,
            timestamp_granularities=args.timestamp_granularities,
            callback_url=args.callback_url,
            min_speakers=args.min_speakers,
            max_speakers=args.max_speakers
        )

        print("\n📦 API Response:")
        if isinstance(result, dict):
            print(json.dumps(result, indent=2)[:3000])  # truncate if huge
        else:
            print(result[:1000])  # for plain text or srt

        print("\n📝 Saving transcript...")
        paths = save_transcript_to_file(result, args.file, args.response_format)

        if isinstance(paths, tuple):
            print(f"✅ Markdown saved: {paths[0]}")
            print(f"🌐 HTML saved: {paths[1]}")
        else:
            print(f"✅ Transcript saved: {paths}")

        if isinstance(result, dict) and "segments" in result:
            print("\n📑 Speaker Segments:")
            for seg in result["segments"]:
                print(f"- {seg.get('speaker', 'Speaker')} [{seg.get('start', 0):.2f} – {seg.get('end', 0):.2f}]: {seg.get('text', '')}")

    except Exception as e:
        print(f"❌ Failed to transcribe: {e}")

if __name__ == "__main__":
    main()
