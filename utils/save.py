import os
import json
import html
import logging
from typing import Dict, List, Any, Union, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_transcript_data(data: Any) -> Dict[str, Any]:
    """
    Validate and normalize transcript data structure.

    Args:
        data: Raw transcript data

    Returns:
        dict: Validated data structure

    Raises:
        ValueError: If data structure is invalid
    """
    if not isinstance(data, dict):
        raise ValueError("Transcript data must be a dictionary")

    segments = data.get("segments", [])
    if not isinstance(segments, list):
        raise ValueError("Segments must be a list")

    return data


def format_verbose_json_to_markdown(data: Dict[str, Any]) -> str:
    """
    Convert verbose_json result to Markdown format.

    Args:
        data: Transcript data with segments

    Returns:
        str: Formatted Markdown content

    Raises:
        ValueError: If data structure is invalid
    """
    try:
        validated_data = validate_transcript_data(data)
        segments = validated_data.get("segments", [])

        if not segments:
            return "⚠️ No segments found in transcription."

        output = []
        for i, segment in enumerate(segments):
            try:
                start = float(segment.get("start", 0))
                end = float(segment.get("end", 0))
                speaker = str(segment.get("speaker", f"Speaker {i + 1}")).strip()
                text = str(segment.get("text", "")).strip()

                if not text:
                    continue

                # Format timestamp
                start_time = f"{start:.2f}s"
                end_time = f"{end:.2f}s"

                # Escape Markdown special characters in text
                text_escaped = text.replace("*", "\\*").replace("_", "\\_")

                line = f"**{speaker}** [{start_time} - {end_time}]: {text_escaped}"
                output.append(line)

            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid segment {i}: {e}")
                continue

        if not output:
            return "⚠️ No valid segments found in transcription."

        return "\n\n".join(output)

    except Exception as e:
        logger.error(f"Failed to format markdown: {e}")
        raise ValueError(f"Markdown formatting failed: {str(e)}")


def format_verbose_json_to_html(data: Dict[str, Any]) -> str:
    """
    Convert verbose_json result to HTML format.

    Args:
        data: Transcript data with segments

    Returns:
        str: Formatted HTML content

    Raises:
        ValueError: If data structure is invalid
    """
    try:
        validated_data = validate_transcript_data(data)
        segments = validated_data.get("segments", [])

        if not segments:
            return "<p>⚠️ No segments found in transcription.</p>"

        html_lines = [
            "<!DOCTYPE html>",
            "<html lang='en'>",
            "<head>",
            "  <meta charset='UTF-8'>",
            "  <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
            "  <title>Transcript</title>",
            "  <style>",
            "    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; padding: 2em; max-width: 800px; margin: auto; background: #fdfdfd; color: #333; }",
            "    h2 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 0.5em; }",
            "    .segment { margin-bottom: 1.5em; padding: 1em; background: #f8f9fa; border-left: 4px solid #3498db; border-radius: 4px; }",
            "    .speaker { font-weight: bold; color: #2c3e50; margin-bottom: 0.5em; }",
            "    .timestamp { color: #7f8c8d; font-size: 0.9em; font-weight: normal; }",
            "    .text { color: #34495e; line-height: 1.5; }",
            "  </style>",
            "</head>",
            "<body>",
            "<h2>Transcript</h2>"
        ]

        for i, segment in enumerate(segments):
            try:
                speaker = str(segment.get("speaker", f"Speaker {i + 1}")).strip()
                start = float(segment.get("start", 0))
                text = str(segment.get("text", "")).strip()

                if not text:
                    continue

                # Format timestamp as MM:SS
                minutes = int(start // 60)
                seconds = int(start % 60)
                timestamp = f"{minutes:02d}:{seconds:02d}"

                # Escape HTML in all user content
                speaker_escaped = html.escape(speaker)
                text_escaped = html.escape(text)

                html_lines.append('<div class="segment">')
                html_lines.append(
                    f'  <div class="speaker">{speaker_escaped} <span class="timestamp">({timestamp})</span></div>')
                html_lines.append(f'  <div class="text">{text_escaped}</div>')
                html_lines.append('</div>')

            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid segment {i}: {e}")
                continue

        html_lines.append("</body></html>")
        return "\n".join(html_lines)

    except Exception as e:
        logger.error(f"Failed to format HTML: {e}")
        raise ValueError(f"HTML formatting failed: {str(e)}")


def format_to_srt(data: Dict[str, Any]) -> str:
    """
    Convert transcript data to SRT subtitle format.

    Args:
        data: Transcript data with segments

    Returns:
        str: SRT formatted content
    """
    try:
        validated_data = validate_transcript_data(data)
        segments = validated_data.get("segments", [])

        if not segments:
            return ""

        srt_lines = []
        for i, segment in enumerate(segments, 1):
            try:
                start = float(segment.get("start", 0))
                end = float(segment.get("end", 0))
                text = str(segment.get("text", "")).strip()

                if not text:
                    continue

                # Convert seconds to SRT time format (HH:MM:SS,mmm)
                def seconds_to_srt_time(seconds):
                    hours = int(seconds // 3600)
                    minutes = int((seconds % 3600) // 60)
                    secs = int(seconds % 60)
                    millis = int((seconds % 1) * 1000)
                    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

                start_time = seconds_to_srt_time(start)
                end_time = seconds_to_srt_time(end)

                srt_lines.append(str(i))
                srt_lines.append(f"{start_time} --> {end_time}")
                srt_lines.append(text)
                srt_lines.append("")  # Empty line between subtitles

            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid segment {i}: {e}")
                continue

        return "\n".join(srt_lines)

    except Exception as e:
        logger.error(f"Failed to format SRT: {e}")
        raise ValueError(f"SRT formatting failed: {str(e)}")


def save_transcript_to_file(
        data: Union[Dict[str, Any], str],
        source_file: str,
        output_format: str
) -> Union[str, Tuple[str, str]]:
    """
    Save transcript result to the `transcripts` folder in specified format.

    Args:
        data: Transcript data or string content
        source_file: Original audio file path
        output_format: Output format ('markdown', 'html', 'srt', 'txt')

    Returns:
        str or tuple: File path(s) of saved transcript(s)

    Raises:
        ValueError: If parameters are invalid
        OSError: If file operations fail
    """
    if not source_file:
        raise ValueError("Source file path cannot be empty")

    if output_format not in ['markdown', 'html', 'srt', 'txt']:
        raise ValueError(f"Unsupported output format: {output_format}")

    try:
        # Create safe filename
        base_name = Path(source_file).stem
        output_dir = Path("transcripts")
        output_dir.mkdir(exist_ok=True)

        if output_format == "markdown":
            if not isinstance(data, dict):
                raise ValueError("Dictionary required for markdown format")

            md_content = format_verbose_json_to_markdown(data)
            html_content = format_verbose_json_to_html(data)

            md_path = output_dir / f"{base_name}_transcript.md"
            html_path = output_dir / f"{base_name}_transcript.html"

            # Write files with proper error handling
            md_path.write_text(md_content, encoding="utf-8")
            html_path.write_text(html_content, encoding="utf-8")

            logger.info(f"Saved markdown to: {md_path}")
            logger.info(f"Saved HTML to: {html_path}")
            return str(md_path), str(html_path)

        elif output_format == "srt":
            if isinstance(data, dict):
                content = format_to_srt(data)
            else:
                content = str(data)
            ext = ".srt"

        elif output_format == "html":
            if isinstance(data, dict):
                content = format_verbose_json_to_html(data)
            else:
                content = str(data)
            ext = ".html"

        else:  # txt format
            if isinstance(data, dict):
                content = json.dumps(data, indent=2, ensure_ascii=False)
            else:
                content = str(data)
            ext = ".txt"

        output_path = output_dir / f"{base_name}_transcript{ext}"
        output_path.write_text(content, encoding="utf-8")

        logger.info(f"Saved {output_format.upper()} to: {output_path}")
        return str(output_path)

    except Exception as e:
        logger.error(f"Failed to save transcript: {e}")
        raise OSError(f"File save failed: {str(e)}")