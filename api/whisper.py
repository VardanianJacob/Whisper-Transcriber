import requests
import logging
import os
import mimetypes
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
REQUEST_TIMEOUT = (30, 300)  # (connect_timeout, read_timeout)
MAX_RETRIES = 3


class WhisperAPIError(Exception):
    """Custom exception for Whisper API errors."""
    pass


class FileValidationError(Exception):
    """Custom exception for file validation errors."""
    pass


def validate_audio_file(file_path: Union[str, Path]) -> Path:
    """
    Validate audio file for transcription.

    Args:
        file_path: Path to audio file

    Returns:
        Path: Validated file path

    Raises:
        FileValidationError: If file is invalid
    """
    file_path = Path(file_path)

    # Check if file exists
    if not file_path.exists():
        raise FileValidationError(f"File does not exist: {file_path}")

    # Check if it's a file (not directory)
    if not file_path.is_file():
        raise FileValidationError(f"Path is not a file: {file_path}")

    # Check file size
    file_size = file_path.stat().st_size
    if file_size == 0:
        raise FileValidationError("File is empty")

    if file_size > MAX_FILE_SIZE:
        size_mb = file_size / (1024 * 1024)
        raise FileValidationError(f"File too large: {size_mb:.1f}MB (max: {MAX_FILE_SIZE // (1024 * 1024)}MB)")

    # Check file extension
    file_extension = file_path.suffix.lower()
    if file_extension not in SUPPORTED_AUDIO_TYPES:
        raise FileValidationError(
            f"Unsupported file type: {file_extension}. Supported: {', '.join(SUPPORTED_AUDIO_TYPES)}")

    # Check MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type and not (mime_type.startswith('audio/') or mime_type.startswith('video/')):
        raise FileValidationError(f"Invalid MIME type: {mime_type}")

    logger.info(f"File validation passed: {file_path.name} ({file_size / 1024:.1f}KB)")
    return file_path


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


def transcribe_audio(
        file_path: Union[str, Path],
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
    Transcribe audio file using Whisper API.

    Args:
        file_path: Path to audio file
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
    validated_file_path = validate_audio_file(file_path)
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

    # Prepare form data
    data = [
        ("language", language.strip()),
        ("response_format", response_format),
        ("speaker_labels", str(speaker_labels).lower()),
        ("translate", str(translate).lower())
    ]

    # Add optional parameters
    if prompt and prompt.strip():
        data.append(("prompt", prompt.strip()))

    if callback_url and callback_url.strip():
        data.append(("callback_url", callback_url.strip()))

    if min_speakers is not None:
        data.append(("min_speakers", str(min_speakers)))

    if max_speakers is not None:
        data.append(("max_speakers", str(max_speakers)))

    # Add timestamp granularities
    for granularity in timestamp_granularities:
        data.append(("timestamp_granularities[]", granularity))

    logger.info(f"Starting transcription for: {validated_file_path.name}")
    logger.debug(f"API parameters: language={language}, speaker_labels={speaker_labels}, translate={translate}")

    # Make API request with retry logic
    last_exception = None

    for attempt in range(MAX_RETRIES):
        try:
            with open(validated_file_path, "rb") as file_handle:
                files = {"file": (validated_file_path.name, file_handle, "audio/mpeg")}

                logger.debug(f"API request attempt {attempt + 1}/{MAX_RETRIES}")

                response = requests.post(
                    WHISPER_API_URL,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=REQUEST_TIMEOUT
                )

                # Check for HTTP errors
                response.raise_for_status()

                # Log response details in dev mode
                if ENV == "dev":
                    logger.info(f"Whisper API response status: {response.status_code}")
                    logger.debug(f"Response headers: {dict(response.headers)}")

                # Parse JSON response
                result = response.json()

                logger.info(f"Transcription completed successfully for: {validated_file_path.name}")
                return result

        except requests.exceptions.Timeout as e:
            last_exception = e
            logger.warning(f"Request timeout on attempt {attempt + 1}: {e}")

        except requests.exceptions.ConnectionError as e:
            last_exception = e
            logger.warning(f"Connection error on attempt {attempt + 1}: {e}")

        except requests.exceptions.HTTPError as e:
            # Don't retry for client errors (4xx)
            if 400 <= e.response.status_code < 500:
                logger.error(f"Client error: {e.response.status_code} - {e.response.text}")
                raise WhisperAPIError(f"API client error: {e.response.status_code}")

            # Retry for server errors (5xx)
            last_exception = e
            logger.warning(f"Server error on attempt {attempt + 1}: {e}")

        except requests.exceptions.RequestException as e:
            last_exception = e
            logger.warning(f"Request error on attempt {attempt + 1}: {e}")

        except ValueError as e:
            # JSON parsing error
            logger.error(f"Invalid JSON response: {e}")
            raise WhisperAPIError(f"Invalid API response format: {e}")

        except Exception as e:
            logger.error(f"Unexpected error during transcription: {e}")
            raise WhisperAPIError(f"Transcription failed: {str(e)}")

    # All retries failed
    logger.error(f"All {MAX_RETRIES} retry attempts failed")
    raise WhisperAPIError(f"API request failed after {MAX_RETRIES} attempts: {str(last_exception)}")


def get_supported_languages() -> List[str]:
    """
    Get list of supported languages for transcription.
    This is a placeholder - in a real implementation, you might
    query the API or maintain a static list.

    Returns:
        list: List of supported language codes
    """
    return [
        'english', 'spanish', 'french', 'german', 'italian', 'portuguese',
        'russian', 'chinese', 'japanese', 'korean', 'arabic', 'hindi'
    ]