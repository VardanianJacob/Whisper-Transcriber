import aiohttp
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from config import CLAUDE_API_KEY, CLAUDE_API_URL
from api.whisper import transcribe_audio

logger = logging.getLogger(__name__)


class ClaudeAnalyzerError(Exception):
    """Custom exception for Claude analyzer errors."""
    pass


async def generate_speaking_analysis(
        file_content: bytes,
        filename: str,
        language: str = "english",
        prompt: str = "",
        translate: bool = False,
        min_speakers: int = 1,
        max_speakers: int = 8,
        **kwargs
) -> str:
    """
    Generate HTML analysis report using Whisper + Claude API

    Args:
        file_content: Audio file content as bytes
        filename: Original audio filename
        language: Language for transcription
        prompt: Additional context prompt
        translate: Whether to translate to English
        min_speakers: Minimum number of speakers
        max_speakers: Maximum number of speakers

    Returns:
        HTML string with complete analysis report

    Raises:
        ClaudeAnalyzerError: If analysis fails
    """

    # Validate inputs
    if not CLAUDE_API_KEY:
        raise ClaudeAnalyzerError("Claude API key not configured. Please set CLAUDE_API_KEY environment variable.")

    if not file_content:
        raise ClaudeAnalyzerError("No audio file content provided")

    try:
        # Step 1: Transcribe audio with Whisper
        logger.info(f"🎤 Starting transcription for: {filename}")

        transcript_result = await transcribe_audio(
            file_content=file_content,
            filename=filename,
            language=language,
            translate=translate,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
            speaker_labels=True,
            response_format="verbose_json"
        )

        # Extract transcript text and segments
        if isinstance(transcript_result, dict):
            transcript_text = transcript_result.get("text", "")
            segments = transcript_result.get("segments", [])
        else:
            transcript_text = str(transcript_result)
            segments = []

        if not transcript_text.strip():
            raise ClaudeAnalyzerError("No transcript text was generated from the audio file")

        logger.info(f"✅ Transcription completed: {len(transcript_text)} characters")

        # Step 2: Format transcript with speaker labels
        formatted_transcript = format_transcript_with_speakers(transcript_text, segments)

        # Step 3: Generate analysis with Claude
        logger.info(f"🧠 Starting Claude analysis for: {filename}")
        html_report = await analyze_transcript_with_claude(
            transcript=formatted_transcript,
            filename=filename,
            custom_prompt=prompt,
            language=language
        )

        logger.info(f"✅ Complete analysis finished for {filename}")
        return html_report

    except Exception as e:
        if isinstance(e, ClaudeAnalyzerError):
            raise
        else:
            logger.error(f"❌ Analysis failed for {filename}: {str(e)}")
            raise ClaudeAnalyzerError(f"Analysis failed: {str(e)}")


def format_transcript_with_speakers(transcript_text: str, segments: list) -> str:
    """
    Format transcript with speaker labels from segments.

    Args:
        transcript_text: Raw transcript text
        segments: List of transcript segments with timing and speaker info

    Returns:
        Formatted transcript with speaker labels
    """
    if not segments:
        return transcript_text

    formatted_lines = []

    for segment in segments:
        speaker = segment.get('speaker', 'Speaker 1')
        text = segment.get('text', '').strip()
        start_time = segment.get('start', 0)

        if text:
            # Format timestamp as MM:SS
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            timestamp = f"[{minutes:02d}:{seconds:02d}]"

            formatted_lines.append(f"{speaker} {timestamp}: {text}")

    return "\n".join(formatted_lines) if formatted_lines else transcript_text


async def analyze_transcript_with_claude(
        transcript: str,
        filename: str,
        custom_prompt: str = "",
        language: str = "english"
) -> str:
    """
    Send transcript to Claude for analysis.

    Args:
        transcript: Formatted transcript with speaker labels
        filename: Original filename
        custom_prompt: Additional analysis context
        language: Original language of the audio

    Returns:
        HTML analysis report
    """

    # Build analysis prompt
    base_prompt = f"""Analyze this speaking session transcript and create a comprehensive HTML report.

TRANSCRIPT:
{transcript}

CONTEXT:
- Filename: {filename}
- Original Language: {language}
{f"- Additional Context: {custom_prompt}" if custom_prompt else ""}

Create a complete HTML page with:
1. **Executive Summary** - Key insights overview (2-3 sentences)
2. **Speaker Analysis** - Individual speaking patterns, style, and statistics  
3. **Communication Metrics** - Speaking time distribution, word count, pace analysis
4. **Key Topics & Themes** - Main discussion points and content analysis
5. **Engagement Quality** - Interaction patterns, turn-taking, and effectiveness
6. **Recommendations** - Specific, actionable improvement suggestions
7. **Detailed Transcript** - Clean, formatted version with timestamps

Technical requirements:
- Complete HTML document with embedded CSS styling
- Use Chart.js CDN for interactive charts: https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js
- Modern, responsive design with professional styling
- Mobile-friendly layout with proper viewport settings
- Include speaker time distribution pie chart and speaking pace line chart
- Use actual data from the transcript for all metrics and charts
- Professional color scheme with gradients and shadows
- Print-friendly styles with @media print rules

Return ONLY the complete HTML starting with <!DOCTYPE html>"""

    headers = {
        "Content-Type": "application/json",
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01"
    }

    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4000,
        "temperature": 0.3,
        "messages": [
            {
                "role": "user",
                "content": base_prompt
            }
        ]
    }

    # Timeout for large analyses
    timeout = aiohttp.ClientTimeout(total=180)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(CLAUDE_API_URL, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()

                    # Extract content from Claude response
                    if "content" in result and len(result["content"]) > 0:
                        html_content = result["content"][0]["text"]

                        # Validate that we got HTML
                        if not html_content.strip().startswith("<!DOCTYPE html"):
                            logger.warning("Claude response doesn't appear to be valid HTML, wrapping...")
                            html_content = wrap_in_html(html_content, filename)

                        logger.info(f"✅ Claude analysis generated successfully for {filename}")
                        logger.info(f"📄 Generated HTML length: {len(html_content)} characters")
                        return html_content
                    else:
                        raise ClaudeAnalyzerError("Invalid response format from Claude API")

                else:
                    error_text = await response.text()
                    logger.error(f"❌ Claude API error {response.status}: {error_text}")

                    # Handle specific error cases
                    if response.status == 401:
                        raise ClaudeAnalyzerError("Invalid Claude API key")
                    elif response.status == 429:
                        raise ClaudeAnalyzerError("Claude API rate limit exceeded - please try again in a few minutes")
                    elif response.status >= 500:
                        raise ClaudeAnalyzerError("Claude API server error - please try again later")
                    else:
                        raise ClaudeAnalyzerError(f"Claude API error {response.status}: {error_text}")

    except asyncio.TimeoutError:
        logger.error("❌ Claude API request timeout (3 minutes)")
        raise ClaudeAnalyzerError("Analysis timeout - please try with a shorter audio file or try again later")
    except aiohttp.ClientError as e:
        logger.error(f"❌ Network error during Claude API call: {str(e)}")
        raise ClaudeAnalyzerError(f"Network error: {str(e)}")
    except ClaudeAnalyzerError:
        # Re-raise our custom errors as-is
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error during Claude analysis: {str(e)}")
        raise ClaudeAnalyzerError(f"Analysis failed: {str(e)}")


def wrap_in_html(content: str, filename: str) -> str:
    """
    Wrap content in basic HTML structure if Claude doesn't return valid HTML.

    Args:
        content: The content to wrap
        filename: Original filename for title

    Returns:
        Complete HTML document
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analysis Report - {filename}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}

        .container {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin: 20px 0;
        }}

        .header {{
            text-align: center;
            border-bottom: 3px solid #667eea;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}

        .header h1 {{
            color: #667eea;
            margin: 0;
            font-size: 2.5em;
        }}

        .content {{
            white-space: pre-wrap;
            background: #f8f9fa;
            padding: 25px;
            border-radius: 8px;
            border-left: 5px solid #667eea;
            font-size: 16px;
        }}

        .error-note {{
            background: #fff3cd;
            color: #856404;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
            border-left: 4px solid #ffc107;
        }}

        @media (max-width: 768px) {{
            body {{ padding: 10px; }}
            .container {{ padding: 20px; }}
            .header h1 {{ font-size: 2em; }}
        }}

        @media print {{
            body {{
                background: white !important;
                color: black !important;
            }}
            .container {{
                box-shadow: none !important;
                margin: 0 !important;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 Analysis Report</h1>
            <p>Generated by Claude AI for: <strong>{filename}</strong></p>
            <p style="font-size: 14px; opacity: 0.7;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="error-note">
            <strong>Note:</strong> The AI response was not in the expected HTML format. 
            This is a fallback display of the analysis content.
        </div>

        <div class="content">
{content}
        </div>
    </div>
</body>
</html>"""


async def test_claude_connection() -> bool:
    """
    Test Claude API connection with a simple request.

    Returns:
        bool: True if connection successful, False otherwise
    """
    if not CLAUDE_API_KEY:
        logger.error("No Claude API key configured")
        return False

    try:
        test_transcript = """Speaker 1 [00:00]: Hello everyone, welcome to today's meeting. I'm excited to discuss our quarterly results.
Speaker 2 [00:05]: Thank you for having me. The numbers look really promising this quarter.
Speaker 1 [00:10]: Absolutely. Let's dive into the details and see what drove our success."""

        result = await analyze_transcript_with_claude(test_transcript, "connection_test.mp3")

        # Basic validation - check if we got HTML back
        is_valid = (
                len(result) > 100 and
                "<!DOCTYPE html" in result and
                "</html>" in result
        )

        if is_valid:
            logger.info("✅ Claude API connection test successful")
            return True
        else:
            logger.error("❌ Claude API test failed - invalid response format")
            return False

    except Exception as e:
        logger.error(f"❌ Claude API connection test failed: {e}")
        return False


async def estimate_analysis_time(file_size_bytes: int) -> int:
    """
    Estimate total analysis time based on file size.

    Args:
        file_size_bytes: Size of audio file in bytes

    Returns:
        Estimated time in seconds
    """
    # Base times in seconds
    transcription_time = max(30, file_size_bytes // (1024 * 1024) * 15)  # ~15s per MB
    analysis_time = 45  # Claude analysis time

    total_time = transcription_time + analysis_time

    # Cap at 5 minutes (300 seconds)
    return min(total_time, 300)


# Legacy function for backward compatibility
async def generate_speaking_analysis_legacy(transcript: str, filename: str = "audio") -> str:
    """
    Legacy function that only takes transcript (for backward compatibility).

    Args:
        transcript: Already transcribed text
        filename: Filename for the report

    Returns:
        HTML analysis report
    """
    logger.warning("Using legacy generate_speaking_analysis - transcript already provided")
    return await analyze_transcript_with_claude(transcript, filename)


if __name__ == "__main__":
    # Run test when module is executed directly
    logging.basicConfig(level=logging.INFO)


    async def main():
        print("Testing Claude API connection...")
        success = await test_claude_connection()
        if success:
            print("✅ Connection test passed!")
        else:
            print("❌ Connection test failed!")

        # Test timing estimation
        test_sizes = [1024 * 1024, 5 * 1024 * 1024, 10 * 1024 * 1024, 25 * 1024 * 1024]  # 1MB, 5MB, 10MB, 25MB
        print("\nEstimated analysis times:")
        for size in test_sizes:
            time_est = await estimate_analysis_time(size)
            print(f"  {size / (1024 * 1024):.1f}MB -> {time_est} seconds ({time_est // 60}min {time_est % 60}s)")


    asyncio.run(main())