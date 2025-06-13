import aiohttp
import asyncio
import logging
from typing import Dict, Any
from config import CLAUDE_API_KEY, CLAUDE_API_URL

logger = logging.getLogger(__name__)


async def generate_speaking_analysis(transcript: str, filename: str = "audio") -> str:
    """
    Generate HTML analysis report using Claude API

    Args:
        transcript: The transcription text with speaker labels
        filename: Original audio filename

    Returns:
        HTML string with complete analysis report
    """

    prompt = f"""Please analyze this speaking session transcript and generate a comprehensive HTML report similar to a speaking club analysis.

TRANSCRIPT:
{transcript}

REQUIREMENTS:
1. Create a complete HTML page with embedded CSS and JavaScript
2. Include interactive charts using Chart.js
3. Analyze speaker participation, timing, and engagement
4. Generate insights and recommendations
5. Use modern, professional styling
6. Include sections for:
   - Speaker statistics
   - Speaking time distribution
   - Participation analysis
   - Key insights
   - Recommendations for improvement
   - Essential phrases for business English (if applicable)

7. Make it visually appealing with:
   - Gradients and modern colors
   - Interactive charts (pie, bar, line charts)
   - Responsive design
   - Professional typography

8. Base the analysis on the actual transcript content
9. Filename: {filename}

Please return ONLY the complete HTML code, no explanations."""

    headers = {
        "Content-Type": "application/json",
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01"
    }

    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4000,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(CLAUDE_API_URL, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    html_content = result["content"][0]["text"]
                    logger.info(f"✅ Claude analysis generated successfully for {filename}")
                    return html_content
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Claude API error {response.status}: {error_text}")
                    raise Exception(f"Claude API error: {response.status}")

    except Exception as e:
        logger.error(f"❌ Failed to generate Claude analysis: {str(e)}")
        raise Exception(f"Analysis generation failed: {str(e)}")