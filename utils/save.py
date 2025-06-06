import os
import json

def format_verbose_json_to_markdown(data):
    """
    Преобразует verbose_json результат в Markdown.
    """
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
    """
    Преобразует verbose_json результат в HTML.
    """
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
        text = seg.get("text", "").strip()
        timestamp = f"{int(start // 60):02}:{int(start % 60):02}"
        html_lines.append(f"<h3>{speaker} <small>({timestamp})</small></h3>")
        html_lines.append(f"<p>{text}</p>")

    html_lines.append("</body></html>")
    return "\n".join(html_lines)


def save_transcript_to_file(data, source_file, output_format):
    """
    Сохраняет результат транскрипции в папку `transcripts` в указанном формате.
    """
    base_name = os.path.basename(source_file)
    name, _ = os.path.splitext(base_name)
    output_dir = "transcripts"
    os.makedirs(output_dir, exist_ok=True)

    if output_format == "markdown":
        if not isinstance(data, dict):
            raise ValueError("Expected dict for markdown output")

        md_content = format_verbose_json_to_markdown(data)
        html_content = format_verbose_json_to_html(data)

        md_path = os.path.join(output_dir, f"{name}_transcript.md")
        html_path = os.path.join(output_dir, f"{name}_transcript.html")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"💾 Markdown: {md_path}")
        print(f"🌐 HTML: {html_path}")
        return md_path, html_path

    # SRT или TXT (по умолчанию)
    ext = ".srt" if output_format == "srt" else ".txt"
    out_path = os.path.join(output_dir, f"{name}_transcript{ext}")

    if isinstance(data, (dict, list)):
        text = json.dumps(data, indent=2, ensure_ascii=False)
    else:
        text = str(data)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"💾 Saved {output_format.upper()} to: {out_path}")
    return out_path
