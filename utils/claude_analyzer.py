import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional
from config import CLAUDE_API_KEY, CLAUDE_API_URL

logger = logging.getLogger(__name__)


class ClaudeAnalyzerError(Exception):
    """Custom exception for Claude analyzer errors."""
    pass


async def generate_speaking_analysis(transcript: str, filename: str = "audio") -> str:
    """
    Generate HTML analysis report using Claude API

    Args:
        transcript: The transcription text with speaker labels
        filename: Original audio filename

    Returns:
        HTML string with complete analysis report

    Raises:
        ClaudeAnalyzerError: If analysis fails
    """

    # Validate inputs
    if not CLAUDE_API_KEY:
        raise ClaudeAnalyzerError("Claude API key not configured. Please set CLAUDE_API_KEY environment variable.")

    if not transcript or not transcript.strip():
        raise ClaudeAnalyzerError("Empty transcript provided")

    # Optimized prompt for better performance and reliability
    prompt = f"""Analyze this speaking session transcript and create a comprehensive HTML report.

TRANSCRIPT:
{transcript}

Create a complete HTML page with:
1. **Executive Summary** - Key insights overview
2. **Speaker Analysis** - Individual speaking patterns and statistics  
3. **Communication Metrics** - Speaking time, word count, pace analysis
4. **Key Topics** - Main discussion points and themes
5. **Engagement Quality** - Interaction patterns and effectiveness
6. **Recommendations** - Specific improvement suggestions

Technical requirements:
- Complete HTML document with embedded CSS
- Use Chart.js CDN for interactive charts: https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js
- Modern, responsive design with professional styling
- Mobile-friendly layout
- Include speaker time distribution charts
- Base all analysis on actual transcript content
- Filename: {filename}

Return ONLY the complete HTML starting with <!DOCTYPE html>"""

    headers = {
        "Content-Type": "application/json",
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01"
    }

    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4000,
        "temperature": 0.3,  # Lower temperature for more consistent output
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    # Increased timeout for large files (3 minutes)
    timeout = aiohttp.ClientTimeout(total=180)

    try:
        logger.info(f"🧠 Starting Claude analysis for: {filename}")
        logger.info(f"📝 Transcript length: {len(transcript)} characters")

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
        test_transcript = """Speaker 1: Hello everyone, welcome to today's meeting. I'm excited to discuss our quarterly results.
Speaker 2: Thank you for having me. The numbers look really promising this quarter.
Speaker 1: Absolutely. Let's dive into the details and see what drove our success."""

        result = await generate_speaking_analysis(test_transcript, "connection_test.mp3")

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


async def estimate_analysis_time(transcript_length: int) -> int:
    """
    Estimate analysis time based on transcript length.

    Args:
        transcript_length: Number of characters in transcript

    Returns:
        Estimated time in seconds
    """
    # Base time: 30 seconds
    base_time = 30

    # Additional time based on length (roughly 1 second per 100 characters)
    additional_time = transcript_length // 100

    # Cap at 3 minutes (180 seconds)
    total_time = min(base_time + additional_time, 180)

    return total_time


if __name__ == "__main__":
    # Run test when module is executed directly
    import datetime

    logging.basicConfig(level=logging.INFO)


    async def main():
        print("Testing Claude API connection...")
        success = await test_claude_connection()
        if success:
            print("✅ Connection test passed!")
        else:
            print("❌ Connection test failed!")

        # Test timing estimation
        test_lengths = [1000, 5000, 10000, 50000]
        print("\nEstimated analysis times:")
        for length in test_lengths:
            time_est = await estimate_analysis_time(length)
            print(f"  {length:,} chars -> {time_est} seconds")


    asyncio.run(main())