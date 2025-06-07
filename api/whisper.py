import requests
import logging
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

def transcribe_audio(
    file_path,
    language=DEFAULT_LANGUAGE,
    prompt=None,
    speaker_labels=DEFAULT_SPEAKER_LABELS,
    translate=DEFAULT_TRANSLATE,
    response_format="verbose_json",
    timestamp_granularities=DEFAULT_TIMESTAMP_GRANULARITIES,
    callback_url=None,
    min_speakers=DEFAULT_MIN_SPEAKERS,
    max_speakers=DEFAULT_MAX_SPEAKERS
):
    headers = {
        "Authorization": f"Bearer {WHISPER_API_KEY}"
    }

    data = [
        ("language", language),
        ("response_format", response_format),
        ("speaker_labels", str(speaker_labels).lower()),
        ("translate", str(translate).lower())
    ]

    if prompt:
        data.append(("prompt", prompt))
    if callback_url:
        data.append(("callback_url", callback_url))
    if min_speakers is not None:
        data.append(("min_speakers", str(min_speakers)))
    if max_speakers is not None:
        data.append(("max_speakers", str(max_speakers)))
    if timestamp_granularities:
        for granularity in timestamp_granularities:
            data.append(("timestamp_granularities[]", granularity))

    try:
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(WHISPER_API_URL, headers=headers, files=files, data=data)
            response.raise_for_status()

        if ENV == "dev":
            logger.info(f"Whisper API response status: {response.status_code}")
            logger.debug(f"Whisper API response body: {response.text}")

        return response.json()

    except requests.RequestException as e:
        logger.error(f"Network or HTTP error while calling Whisper API: {e}")
        raise Exception(f"Network or HTTP error: {e}")

    except Exception as e:
        logger.error(f"Unexpected error in transcribe_audio: {e}")
        raise
