import os
import json


def format_verbose_json_to_markdown(data):
    output = []
    segments = data.get("segments", [])

    for segment in segments:
        start = segment.get("start", 0)
        end = segment.get("end", 0)
        speaker = segment.get("speaker", "Speaker ?")
        text = segment.get("text", "").strip()

        line = f"**{speaker}** [{start:.2f}s - {end:.2f}s]: {text}"
        output.append(line)

    return "\n\n".join(output)


def format_verbose_json_to_html(data):
    segments = data.get("segments", [])
    html_lines = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "  <meta charset='UTF-8'>",
        "  <title>Transcript</title>",
        "  <style>",
        "    body { font-family: sans-serif; line-height: 1.6; padding: 2em; max-width: 800px; margin: auto; background: #fdfdfd; color: #333; }",
        "    h3 { margin-top: 2em; font-size: 1.1em; color: #222; }",
        "    small { color: #888; font-weight: normal; font-size: 0.9em; }",
        "    p { margin: 0.2em 0 1em; }",
        "  </style>",
        "</head>",
        "<body>",
        "<h2>Transcript</h2>"
    ]

    for seg in segments:
        speaker = seg.get("speaker", "Speaker")
        start = seg.get("start", 0)
        text = seg.get("text", "")
        timestamp = f"{int(start // 60):02}:{int(start % 60):02}"
        html_lines.append(f"<h3>{speaker} <small>({timestamp})</small></h3>")
        html_lines.append(f"<p>{text}</p>")

    html_lines.append("</body></html>")
    return "\n".join(html_lines)


def save_transcript_to_file(data_or_text, source_file, response_format):
    base = os.path.basename(source_file)
    name, _ = os.path.splitext(base)
    output_dir = "transcripts"
    os.makedirs(output_dir, exist_ok=True)

    # Markdown
    if response_format == "verbose_json":
        ext = ".md"
        data = json.loads(data_or_text) if isinstance(data_or_text, str) else data_or_text
        markdown = format_verbose_json_to_markdown(data)
        markdown_path = os.path.join(output_dir, f"{name}_transcript{ext}")
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        print(f"💾 Saved Markdown transcript to: {markdown_path}")

        # HTML
        html = format_verbose_json_to_html(data)
        html_path = os.path.join(output_dir, f"{name}_transcript.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"🌐 Saved HTML transcript to: {html_path}")

    else:
        ext = ".srt" if response_format == "srt" else ".txt"
        text = data_or_text
        text_path = os.path.join(output_dir, f"{name}_transcript{ext}")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"💾 Saved transcript to: {text_path}")
