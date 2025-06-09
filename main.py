#!/usr/bin/env python3
"""
🎙️ WhisperAPI CLI Tool
Command-line interface for audio transcription using Lemonfox Whisper API.
"""

import os
import sys
import json
import glob
import argparse
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

from api.whisper import transcribe_audio, validate_audio_file, MAX_FILE_SIZE, SUPPORTED_AUDIO_TYPES
from utils.save import save_transcript_to_file
from config import (
    DEFAULT_LANGUAGE,
    DEFAULT_TIMESTAMP_GRANULARITIES,
    DEFAULT_MIN_SPEAKERS,
    DEFAULT_MAX_SPEAKERS,
    DEFAULT_SPEAKER_LABELS,
    DEFAULT_TRANSLATE,
    DEFAULT_OUTPUT_FORMAT
)

# 🛠️ Load environment variables
load_dotenv(".env.local")


def str2bool(v) -> bool:
    """Convert string to boolean."""
    if isinstance(v, bool):
        return v
    return str(v).lower() in ("yes", "true", "t", "1", "on")


def validate_file_path(file_path: str) -> Path:
    """
    Validate and normalize file path.

    Args:
        file_path: Input file path

    Returns:
        Path: Validated path object

    Raises:
        ValueError: If path is invalid or unsafe
    """
    try:
        path = Path(file_path).resolve()

        # Security: Prevent path traversal
        if not str(path).startswith(str(Path.cwd().resolve())):
            # Allow absolute paths within reasonable bounds
            if not path.exists():
                raise ValueError(f"File not found: {path}")

        return path
    except Exception as e:
        raise ValueError(f"Invalid file path: {e}")


def find_audio_files(patterns: List[str]) -> List[Path]:
    """
    Find audio files matching the given patterns.

    Args:
        patterns: List of file patterns (can include wildcards)

    Returns:
        List of valid audio file paths
    """
    files = []
    for pattern in patterns:
        if '*' in pattern or '?' in pattern:
            # Handle wildcards
            matched = glob.glob(pattern)
            files.extend(matched)
        else:
            # Regular file
            files.append(pattern)

    validated_files = []
    for file_path in files:
        try:
            path = validate_file_path(file_path)
            # Check if it's likely an audio file
            if path.suffix.lower() in SUPPORTED_AUDIO_TYPES:
                validated_files.append(path)
            else:
                print(f"⚠️ Skipping unsupported file type: {path}")
        except ValueError as e:
            print(f"❌ {e}")

    return validated_files


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def print_transcription_summary(result: dict, file_path: Path):
    """Print a summary of the transcription results."""
    if not isinstance(result, dict):
        return

    segments = result.get("segments", [])
    if not segments:
        return

    print(f"\n📊 Transcription Summary for {file_path.name}:")
    print(f"   🕐 Duration: {segments[-1].get('end', 0):.1f} seconds")
    print(f"   🗣️ Speakers detected: {len(set(seg.get('speaker', 'Unknown') for seg in segments))}")
    print(f"   📝 Segments: {len(segments)}")

    # Show first few segments
    print("\n📑 First segments:")
    for i, seg in enumerate(segments[:3]):
        speaker = seg.get('speaker', 'Speaker')
        start = seg.get('start', 0)
        end = seg.get('end', 0)
        text = seg.get('text', '').strip()[:100]
        if len(seg.get('text', '')) > 100:
            text += "..."
        print(f"   {i + 1}. {speaker} [{start:.1f}s-{end:.1f}s]: {text}")

    if len(segments) > 3:
        print(f"   ... and {len(segments) - 3} more segments")


def transcribe_single_file(
        file_path: Path,
        args: argparse.Namespace,
        output_dir: Optional[Path] = None
) -> bool:
    """
    Transcribe a single audio file.

    Args:
        file_path: Path to audio file
        args: Command line arguments
        output_dir: Optional output directory

    Returns:
        bool: True if successful, False otherwise
    """
    print(f"\n🎵 Processing: {file_path.name}")

    try:
        # Validate file using the improved validation
        validated_path = validate_audio_file(file_path)

        file_size = file_path.stat().st_size
        print(f"📊 File size: {format_file_size(file_size)}")

        print("📡 Uploading to Whisper API...")

        result = transcribe_audio(
            file_path=str(validated_path),
            language=args.language,
            prompt=args.prompt,
            speaker_labels=args.speaker_labels,
            translate=args.translate,
            response_format="verbose_json",
            timestamp_granularities=args.timestamp_granularities,
            callback_url=args.callback_url,
            min_speakers=args.min_speakers,
            max_speakers=args.max_speakers
        )

        # Show truncated JSON response if verbose
        if args.verbose:
            print("\n📦 API Response (truncated):")
            if isinstance(result, dict):
                truncated = json.dumps(result, indent=2)[:1000]
                print(truncated)
                if len(json.dumps(result)) > 1000:
                    print("... (truncated)")

        # Save transcript
        print(f"📝 Saving transcript in {args.output_format} format...")

        # Use output directory if specified
        save_path = str(output_dir / file_path.name) if output_dir else str(file_path)

        paths = save_transcript_to_file(result, save_path, args.output_format)

        if isinstance(paths, tuple):
            print(f"✅ Markdown: {paths[0]}")
            print(f"🌐 HTML: {paths[1]}")
        else:
            print(f"✅ Saved: {paths}")

        # Print summary
        print_transcription_summary(result, file_path)

        return True

    except Exception as e:
        print(f"❌ Failed to transcribe {file_path.name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="🎙️ Transcribe audio files using Lemonfox Whisper API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s audio.mp3
  %(prog)s *.wav --language russian --speakers 3
  %(prog)s recordings/ --output-dir transcripts/ --format srt
  %(prog)s audio.mp3 --translate --min-speakers 2 --max-speakers 5
        """
    )

    # Input files
    parser.add_argument(
        "files",
        nargs="*",
        help="Audio file(s) or pattern (supports wildcards like *.mp3)"
    )

    # Transcription options
    parser.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        help=f"Language of the audio (default: {DEFAULT_LANGUAGE})"
    )
    parser.add_argument(
        "--prompt",
        help="Custom prompt to improve transcription accuracy"
    )
    parser.add_argument(
        "--speaker-labels", "--speakers",
        type=str2bool,
        nargs="?",
        const=True,
        default=DEFAULT_SPEAKER_LABELS,
        help="Enable speaker diarization (default: enabled)"
    )
    parser.add_argument(
        "--translate",
        type=str2bool,
        nargs="?",
        const=True,
        default=DEFAULT_TRANSLATE,
        help="Translate output to English"
    )
    parser.add_argument(
        "--timestamp-granularities",
        nargs="+",
        default=DEFAULT_TIMESTAMP_GRANULARITIES,
        choices=["segment", "word"],
        help="Timestamp detail level (default: segment)"
    )
    parser.add_argument(
        "--min-speakers",
        type=int,
        default=DEFAULT_MIN_SPEAKERS,
        help=f"Minimum number of speakers (default: {DEFAULT_MIN_SPEAKERS})"
    )
    parser.add_argument(
        "--max-speakers",
        type=int,
        default=DEFAULT_MAX_SPEAKERS,
        help=f"Maximum number of speakers (default: {DEFAULT_MAX_SPEAKERS})"
    )

    # Output options
    parser.add_argument(
        "--output-format", "--format",
        default=DEFAULT_OUTPUT_FORMAT,
        choices=["text", "markdown", "srt", "html"],
        help=f"Output format (default: {DEFAULT_OUTPUT_FORMAT})"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for transcripts (default: transcripts/)"
    )

    # Other options
    parser.add_argument(
        "--callback-url",
        help="Webhook URL for async processing notifications"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed API responses"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without actually transcribing"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.min_speakers < 1 or args.max_speakers < 1:
        print("❌ Speaker counts must be positive integers")
        sys.exit(1)

    if args.min_speakers > args.max_speakers:
        print("❌ Minimum speakers cannot exceed maximum speakers")
        sys.exit(1)

    # Get files to process
    if not args.files:
        # Interactive mode
        file_input = input("📁 Enter audio file path or pattern: ").strip()
        if not file_input:
            print("❌ No file specified")
            sys.exit(1)
        args.files = [file_input]

    # Find all matching files
    audio_files = find_audio_files(args.files)

    if not audio_files:
        print("❌ No valid audio files found")
        sys.exit(1)

    print(f"🎵 Found {len(audio_files)} audio file(s) to process")

    # Create output directory if specified
    output_dir = args.output_dir or Path("transcripts")
    if not args.dry_run:
        output_dir.mkdir(exist_ok=True)
        print(f"📁 Output directory: {output_dir.absolute()}")

    # Dry run mode
    if args.dry_run:
        print("\n🔍 Dry run - files that would be processed:")
        for file_path in audio_files:
            size = format_file_size(file_path.stat().st_size)
            print(f"   📄 {file_path} ({size})")
        print(
            f"\nSettings: language={args.language}, format={args.output_format}, speakers={args.min_speakers}-{args.max_speakers}")
        return

    # Process files
    successful = 0
    failed = 0

    for i, file_path in enumerate(audio_files, 1):
        print(f"\n{'=' * 50}")
        print(f"Processing file {i}/{len(audio_files)}")

        success = transcribe_single_file(file_path, args, output_dir)
        if success:
            successful += 1
        else:
            failed += 1

    # Final summary
    print(f"\n{'=' * 50}")
    print(f"🎯 Processing complete!")
    print(f"✅ Successful: {successful}")
    if failed > 0:
        print(f"❌ Failed: {failed}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()