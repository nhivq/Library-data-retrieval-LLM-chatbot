import json
from pathlib import Path


ISO_639_2_JSON = Path("/usr/share/iso-codes/json/iso_639-2.json")

FALLBACK_LANGUAGE_NAMES = {
    "eng": "English",
    "ger": "German",
    "deu": "German",
    "spa": "Spanish",
    "fre": "French",
    "fra": "French",
    "chi": "Chinese",
    "zho": "Chinese",
    "ita": "Italian",
    "rus": "Russian",
    "jpn": "Japanese",
    "ara": "Arabic",
    "por": "Portuguese",
    "kor": "Korean",
    "heb": "Hebrew",
    "pol": "Polish",
    "dut": "Dutch",
    "nld": "Dutch",
    "lat": "Latin",
    "ind": "Indonesian",
    "tur": "Turkish",
    "cmn": "Mandarin Chinese",
    "und": "Undetermined",
    "mul": "Multiple languages",
}


def load_language_names():

    language_names = FALLBACK_LANGUAGE_NAMES.copy()

    if not ISO_639_2_JSON.exists():
        return language_names

    with open(
        ISO_639_2_JSON,
        encoding="utf-8"
    ) as f:
        data = json.load(f)

    for entry in data.get("639-2", []):
        name = entry.get("name")

        if not name:
            continue

        for key in ("alpha_2", "alpha_3", "bibliographic"):
            code = entry.get(key)

            if code:
                language_names[code.lower()] = name

    return language_names


LANGUAGE_NAMES = load_language_names()


def clean_language_name(name):

    return name.split(";")[0].strip()


def extract_language_code(language):

    if isinstance(language, dict):
        language = language.get("key")

    if not language:
        return None

    if not isinstance(language, str):
        return None

    return language.replace("/languages/", "").strip()


def normalize_language(language):

    code = extract_language_code(language)

    if not code:
        return None

    name = LANGUAGE_NAMES.get(
        code.lower(),
        code
    )

    return clean_language_name(name)


def normalize_languages(languages):

    normalized = []

    for language in languages or []:
        name = normalize_language(language)

        if name and name not in normalized:
            normalized.append(name)

    return normalized
