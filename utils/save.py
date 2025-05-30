import os
import json

def format_verbose_json_to_markdown(data):
    output = []
    segments = data.get("segments", [])
    if not segments:
        return "⚠️ No segments found in transcription."

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
    if not segments:
        return "<p>⚠️ No segments found in transcription.</p>"

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

def save_transcript_to_file(data_or_text, source_file, output_format):
    base = os.path.basename(source_file)
    name, _ = os.path.splitext(base)
    output_dir = "transcripts"
    os.makedirs(output_dir, exist_ok=True)

    # Try parse if stringified JSON
    if isinstance(data_or_text, str):
        try:
            data = json.loads(data_or_text)
        except Exception:
            data = data_or_text  # plain text
    else:
        data = data_or_text

    # MARKDOWN/HTML mode
    if output_format == "markdown":
        if not isinstance(data, dict):
            raise ValueError("Expected dict for markdown output")

        markdown = format_verbose_json_to_markdown(data)
        html = format_verbose_json_to_html(data)

        md_path = os.path.join(output_dir, f"{name}_transcript.md")
        html_path = os.path.join(output_dir, f"{name}_transcript.html")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"💾 Saved Markdown transcript to: {md_path}")
        print(f"🌐 Saved HTML transcript to: {html_path}")
        return md_path, html_path

    # SRT or TXT output
    ext = ".srt" if output_format == "srt" else ".txt"
    out_path = os.path.join(output_dir, f"{name}_transcript{ext}")

    # Convert to string if needed
    if isinstance(data, (dict, list)):
        text = json.dumps(data, indent=2)
    else:
        text = str(data)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"💾 Saved {output_format.upper()} transcript to: {out_path}")
    return out_path
