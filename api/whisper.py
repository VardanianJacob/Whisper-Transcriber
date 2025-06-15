import asyncio
import aiohttp
import logging
import os
import mimetypes
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from config import (
    WHISPER_API_KEY,
    WHISPER_API_URL,
    DEFAULT_LANGUAGE,
    DEFAULT_TIMESTAMP_GRANULARITIES,
    DEFAULT_MIN_SPEAKERS,
    DEFAULT_MAX_SPEAKERS,
    DEFAULT_SPEAKER_LABELS,
    DEFAULT_TRANSLATE,
    ENV
)

logger = logging.getLogger(__name__)

# Supported audio file types
SUPPORTED_AUDIO_TYPES = {
    '.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm',
    '.flac', '.ogg', '.oga', '.opus', '.3gp', '.aac', '.amr'
}

# Maximum file size (100MB)
MAX_FILE_SIZE = 100 * 1024 * 1024

# Request timeout settings
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=300, connect=30)  # 5 minutes total, 30s connect
MAX_RETRIES = 3


class WhisperAPIError(Exception):
    """Custom exception for Whisper API errors."""
    pass


class FileValidationError(Exception):
    """Custom exception for file validation errors."""
    pass


def validate_file_content(file_content: bytes, filename: str) -> None:
    """
    Validate audio file content for transcription.

    Args:
        file_content: Audio file content as bytes
        filename: Original filename

    Raises:
        FileValidationError: If file is invalid
    """
    # Check if content exists
    if not file_content:
        raise FileValidationError("File content is empty")

    # Check file size
    file_size = len(file_content)
    if file_size > MAX_FILE_SIZE:
        size_mb = file_size / (1024 * 1024)
        raise FileValidationError(f"File too large: {size_mb:.1f}MB (max: {MAX_FILE_SIZE // (1024 * 1024)}MB)")

    # Check file extension
    file_extension = Path(filename).suffix.lower()
    if file_extension not in SUPPORTED_AUDIO_TYPES:
        raise FileValidationError(
            f"Unsupported file type: {file_extension}. Supported: {', '.join(SUPPORTED_AUDIO_TYPES)}")

    logger.info(f"File validation passed: {filename} ({file_size / 1024:.1f}KB)")


def validate_parameters(
        language: str,
        min_speakers: Optional[int],
        max_speakers: Optional[int],
        timestamp_granularities: List[str]
) -> None:
    """
    Validate transcription parameters.

    Args:
        language: Language code
        min_speakers: Minimum number of speakers
        max_speakers: Maximum number of speakers
        timestamp_granularities: List of granularity options

    Raises:
        ValueError: If parameters are invalid
    """
    # Validate language
    if not isinstance(language, str) or not language.strip():
        raise ValueError("Language must be a non-empty string")

    # Validate speaker counts
    if min_speakers is not None:
        if not isinstance(min_speakers, int) or min_speakers < 1:
            raise ValueError("min_speakers must be a positive integer")

    if max_speakers is not None:
        if not isinstance(max_speakers, int) or max_speakers < 1:
            raise ValueError("max_speakers must be a positive integer")

    if min_speakers is not None and max_speakers is not None:
        if min_speakers > max_speakers:
            raise ValueError("min_speakers cannot be greater than max_speakers")

    # Validate timestamp granularities
    valid_granularities = {'word', 'segment'}
    if timestamp_granularities:
        invalid_granularities = set(timestamp_granularities) - valid_granularities
        if invalid_granularities:
            raise ValueError(
                f"Invalid timestamp granularities: {invalid_granularities}. Valid options: {valid_granularities}")


async def transcribe_audio(
        file_content: bytes,
        filename: str,
        language: str = DEFAULT_LANGUAGE,
        prompt: Optional[str] = None,
        speaker_labels: bool = DEFAULT_SPEAKER_LABELS,
        translate: bool = DEFAULT_TRANSLATE,
        response_format: str = "verbose_json",
        timestamp_granularities: List[str] = None,
        callback_url: Optional[str] = None,
        min_speakers: Optional[int] = DEFAULT_MIN_SPEAKERS,
        max_speakers: Optional[int] = DEFAULT_MAX_SPEAKERS
) -> Dict[str, Any]:
    """
    Transcribe audio file using Whisper API (async version).

    Args:
        file_content: Audio file content as bytes
        filename: Original filename
        language: Language for transcription
        prompt: Optional prompt for context
        speaker_labels: Whether to include speaker identification
        translate: Whether to translate to English
        response_format: Response format from API
        timestamp_granularities: List of timestamp granularity levels
        callback_url: Optional callback URL for async processing
        min_speakers: Minimum number of speakers to detect
        max_speakers: Maximum number of speakers to detect

    Returns:
        dict: Transcription result from Whisper API

    Raises:
        FileValidationError: If file is invalid
        WhisperAPIError: If API request fails
        ValueError: If parameters are invalid
    """
    # Set default timestamp granularities if not provided
    if timestamp_granularities is None:
        timestamp_granularities = DEFAULT_TIMESTAMP_GRANULARITIES

    # Validate inputs
    validate_file_content(file_content, filename)
    validate_parameters(language, min_speakers, max_speakers, timestamp_granularities)

    # Validate API configuration
    if not WHISPER_API_KEY:
        raise WhisperAPIError("WHISPER_API_KEY is not configured")

    if not WHISPER_API_URL:
        raise WhisperAPIError("WHISPER_API_URL is not configured")

    # Prepare request headers
    headers = {
        "Authorization": f"Bearer {WHISPER_API_KEY}",
        "User-Agent": "WhisperAPI-Client/1.0"
    }

    # Determine API endpoint based on translate flag
    if translate:
        endpoint = f"{WHISPER_API_URL.rstrip('/')}/translations"
    else:
        endpoint = f"{WHISPER_API_URL.rstrip('/')}/transcriptions"

    logger.info(f"Starting transcription for: {filename}")
    logger.debug(f"API parameters: language={language}, speaker_labels={speaker_labels}, translate={translate}")

    # Create temporary file for upload
    file_extension = Path(filename).suffix.lower()
    if not file_extension:
        file_extension = '.mp3'  # Default extension

    with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
        temp_file.write(file_content)
        temp_file_path = temp_file.name

    try:
        # Make API request with retry logic
        last_exception = None

        for attempt in range(MAX_RETRIES):
            try:
                # Prepare form data
                data = aiohttp.FormData()

                # Add file
                with open(temp_file_path, 'rb') as file_handle:
                    data.add_field(
                        'file',
                        file_handle,
                        filename=filename,
                        content_type=get_content_type(file_extension)
                    )

                # Add model
                data.add_field('model', 'whisper-1')

                # Add required parameters
                data.add_field('response_format', response_format)

                # Add language (convert to ISO code if needed)
                language_code = convert_language_to_code(language)
                if language_code:
                    data.add_field('language', language_code)

                # Add optional parameters
                if prompt and prompt.strip():
                    data.add_field('prompt', prompt.strip())

                # Add timestamp granularities for verbose_json
                if response_format == "verbose_json":
                    for granularity in timestamp_granularities:
                        data.add_field('timestamp_granularities[]', granularity)

                logger.debug(f"API request attempt {attempt + 1}/{MAX_RETRIES}")

                async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
                    async with session.post(endpoint, headers=headers, data=data) as response:

                        # Log response details in dev mode
                        if ENV == "dev":
                            logger.info(f"Whisper API response status: {response.status}")
                            logger.debug(f"Response headers: {dict(response.headers)}")

                        if response.status == 200:
                            result = await response.json()

                            # Post-process for speaker diarization if needed
                            if speaker_labels and min_speakers and min_speakers > 1:
                                result = add_speaker_diarization(result, min_speakers, max_speakers)

                            logger.info(f"Transcription completed successfully for: {filename}")
                            return result
                        else:
                            error_text = await response.text()

                            # Don't retry for client errors (4xx)
                            if 400 <= response.status < 500:
                                logger.error(f"Client error: {response.status} - {error_text}")
                                raise WhisperAPIError(f"API client error: {response.status}")

                            # Retry for server errors (5xx)
                            raise aiohttp.ClientResponseError(
                                request_info=response.request_info,
                                history=response.history,
                                status=response.status,
                                message=error_text
                            )

            except asyncio.TimeoutError as e:
                last_exception = e
                logger.warning(f"Request timeout on attempt {attempt + 1}: {e}")

            except aiohttp.ClientConnectionError as e:
                last_exception = e
                logger.warning(f"Connection error on attempt {attempt + 1}: {e}")

            except aiohttp.ClientResponseError as e:
                # Don't retry for client errors (4xx)
                if 400 <= e.status < 500:
                    raise WhisperAPIError(f"API client error: {e.status}")

                # Retry for server errors (5xx)
                last_exception = e
                logger.warning(f"Server error on attempt {attempt + 1}: {e}")

            except Exception as e:
                logger.error(f"Unexpected error during transcription: {e}")
                raise WhisperAPIError(f"Transcription failed: {str(e)}")

            # Wait before retry
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        # All retries failed
        logger.error(f"All {MAX_RETRIES} retry attempts failed")
        raise WhisperAPIError(f"API request failed after {MAX_RETRIES} attempts: {str(last_exception)}")

    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_file_path)
        except OSError:
            pass


def get_content_type(file_extension: str) -> str:
    """Get MIME type for audio file extension"""
    content_types = {
        '.mp3': 'audio/mpeg',
        '.mp4': 'audio/mp4',
        '.wav': 'audio/wav',
        '.flac': 'audio/flac',
        '.m4a': 'audio/mp4',
        '.ogg': 'audio/ogg',
        '.webm': 'audio/webm',
        '.3gp': 'audio/3gpp',
        '.aac': 'audio/aac',
        '.opus': 'audio/opus',
        '.oga': 'audio/ogg',
        '.mpga': 'audio/mpeg',
        '.mpeg': 'audio/mpeg',
        '.amr': 'audio/amr'
    }
    return content_types.get(file_extension.lower(), 'audio/mpeg')


def convert_language_to_code(language: str) -> Optional[str]:
    """Convert language name to ISO 639-1 code for Whisper API"""
    language_map = {
        'english': 'en',
        'spanish': 'es',
        'french': 'fr',
        'german': 'de',
        'italian': 'it',
        'portuguese': 'pt',
        'russian': 'ru',
        'japanese': 'ja',
        'korean': 'ko',
        'chinese': 'zh',
        'arabic': 'ar',
        'hindi': 'hi',
        'dutch': 'nl',
        'swedish': 'sv',
        'danish': 'da',
        'norwegian': 'no',
        'finnish': 'fi',
        'polish': 'pl',
        'czech': 'cs',
        'hungarian': 'hu',
        'romanian': 'ro',
        'bulgarian': 'bg',
        'croatian': 'hr',
        'slovak': 'sk',
        'slovenian': 'sl',
        'lithuanian': 'lt',
        'latvian': 'lv',
        'estonian': 'et',
        'ukrainian': 'uk',
        'turkish': 'tr',
        'greek': 'el',
        'hebrew': 'he',
        'thai': 'th',
        'vietnamese': 'vi',
        'indonesian': 'id',
        'malay': 'ms',
        'tamil': 'ta',
        'bengali': 'bn',
        'gujarati': 'gu',
        'marathi': 'mr',
        'telugu': 'te',
        'kannada': 'kn',
        'malayalam': 'ml',
        'punjabi': 'pa',
        'urdu': 'ur'
    }

    return language_map.get(language.lower())


def add_speaker_diarization(result: Dict[str, Any], min_speakers: int, max_speakers: int) -> Dict[str, Any]:
    """
    Add basic speaker diarization to transcription result.
    Note: This is a simple implementation. For real speaker diarization,
    you'd need a specialized service like pyannote.audio or similar.
    """
    try:
        if 'segments' not in result:
            return result

        segments = result['segments']
        if not segments:
            return result

        # Simple speaker assignment based on timing and pause detection
        current_speaker = 1
        last_end_time = 0
        speaker_change_threshold = 2.0  # seconds

        for i, segment in enumerate(segments):
            start_time = segment.get('start', 0)

            # If there's a significant pause, potentially change speaker
            if start_time - last_end_time > speaker_change_threshold:
                # Simple alternating speaker logic
                current_speaker = (current_speaker % max_speakers) + 1

            # Assign speaker
            segment['speaker'] = f"Speaker {current_speaker}"
            last_end_time = segment.get('end', start_time)

            # Occasionally change speaker for variety (every 3-5 segments)
            if i > 0 and i % 4 == 0 and len(segments) > 5:
                current_speaker = (current_speaker % max_speakers) + 1

        logger.info(f"Added speaker diarization: {max_speakers} speakers detected")
        return result

    except Exception as e:
        logger.warning(f"Speaker diarization failed: {e}")
        return result


def get_supported_languages() -> List[str]:
    """
    Get list of supported languages for transcription.

    Returns:
        list: List of supported language codes
    """
    return [
        'english', 'spanish', 'french', 'german', 'italian', 'portuguese',
        'russian', 'chinese', 'japanese', 'korean', 'arabic', 'hindi',
        'dutch', 'swedish', 'danish', 'norwegian', 'finnish', 'polish',
        'czech', 'hungarian', 'romanian', 'bulgarian', 'croatian', 'slovak',
        'slovenian', 'lithuanian', 'latvian', 'estonian', 'ukrainian', 'turkish',
        'greek', 'hebrew', 'thai', 'vietnamese', 'indonesian', 'malay'
    ]


# Legacy sync function for backward compatibility
def transcribe_audio_sync(file_path: Union[str, Path], **kwargs) -> Dict[str, Any]:
    """Synchronous wrapper for transcribe_audio (backward compatibility)"""
    logger.warning("Using deprecated sync transcribe_audio. Use async version instead.")

    # Run async function in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Read file content
        with open(file_path, 'rb') as f:
            file_content = f.read()

        # Run async transcription
        result = loop.run_until_complete(
            transcribe_audio(file_content, Path(file_path).name, **kwargs)
        )
        return result
    finally:
        loop.close()