import requests
from config import (
    WHISPER_API_KEY,
    WHISPER_API_URL,
    DEFAULT_LANGUAGE,
    DEFAULT_RESPONSE_FORMAT,
    DEFAULT_TIMESTAMP_GRANULARITIES,
    DEFAULT_MIN_SPEAKERS,
    DEFAULT_MAX_SPEAKERS,
    DEFAULT_SPEAKER_LABELS,
    DEFAULT_TRANSLATE
)

def transcribe_audio(
    file_path,
    language=DEFAULT_LANGUAGE,
    prompt=None,
    speaker_labels=DEFAULT_SPEAKER_LABELS,
    translate=DEFAULT_TRANSLATE,
    response_format=DEFAULT_RESPONSE_FORMAT,
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

    with open(file_path, "rb") as f:
        files = {"file": f}
        response = requests.post(WHISPER_API_URL, headers=headers, files=files, data=data)

    if response.status_code == 200:
        return response.json() if response_format.endswith("json") else response.text
    else:
        raise Exception(f"❌ Error {response.status_code}: {response.text}")
