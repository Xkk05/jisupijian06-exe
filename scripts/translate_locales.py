#!/usr/bin/env python3
"""
Reusable JSON localization translator via OpenAI-compatible chat/completions.

Features:
- Nested JSON support (string leaf nodes only)
- Chunked translation for token control
- Per-language concurrency
- Placeholder protection (e.g. {{count}})
- Retry with ordered-array fallback strategy
- Configurable base_url / model / api_key / concurrency / chunk size
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple
from urllib import error, request

DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "openai/gpt-oss-120b"
# 如果你希望固定写死 Key，可直接把空字符串替换为真实值。
DEFAULT_API_KEY = "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"


LANGUAGE_NAMES: Dict[str, str] = {
    "ar": "Arabic",
    "bn": "Bengali",
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "fa": "Farsi (Persian)",
    "fr": "French",
    "he": "Hebrew",
    "hi": "Hindi",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "ms": "Malay",
    "nl": "Dutch",
    "pl": "Polish",
    "pt": "Portuguese",
    "pt_BR": "Brazilian Portuguese",
    "ru": "Russian",
    "sw": "Swahili",
    "ta": "Tamil",
    "th": "Thai",
    "tl": "Tagalog",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "vi": "Vietnamese",
    "zh_CN": "Simplified Chinese",
    "zh_TW": "Traditional Chinese",
}

PLACEHOLDER_RE = re.compile(r"\{\{\s*[^{}]+\s*\}\}|\{[^{}]+\}")
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")


def flatten_object(obj: dict, prefix: str = "", acc: Dict[str, str] | None = None) -> Dict[str, str]:
    if acc is None:
        acc = {}
    for key, value in obj.items():
        path_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flatten_object(value, path_key, acc)
            continue
        if not isinstance(value, str):
            raise ValueError(f"Only string leaf values are supported. Problem key: {path_key}")
        acc[path_key] = value
    return acc


def unflatten_object(flat: Dict[str, str]) -> dict:
    result: dict = {}
    for path_key, value in flat.items():
        keys = path_key.split(".")
        cursor = result
        for part in keys[:-1]:
            if part not in cursor or not isinstance(cursor[part], dict):
                cursor[part] = {}
            cursor = cursor[part]
        cursor[keys[-1]] = value
    return result


def sorted_placeholders(text: str) -> List[str]:
    return sorted(PLACEHOLDER_RE.findall(text))


def same_placeholders(source: str, translated: str) -> bool:
    return sorted_placeholders(source) == sorted_placeholders(translated)


def sanitize_json_text(raw: str) -> str:
    trimmed = raw.strip()
    fenced = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", trimmed, re.IGNORECASE)
    content = fenced.group(1) if fenced else trimmed

    first_brace = content.find("{")
    last_brace = content.rfind("}")
    if first_brace < 0 or last_brace < 0 or last_brace <= first_brace:
        raise ValueError("Model response does not contain a valid JSON object.")
    return content[first_brace : last_brace + 1]


def parse_langs(langs_raw: str) -> List[str]:
    langs = [x.strip() for x in langs_raw.split(",") if x.strip()]
    if not langs:
        raise ValueError("--langs cannot be empty")
    # Keep user order while removing duplicates.
    return list(dict.fromkeys(langs))


def ensure_string_dict(obj: object, *, field_name: str) -> Dict[str, str]:
    if not isinstance(obj, dict):
        raise ValueError(f'"{field_name}" must be a JSON object.')
    result: Dict[str, str] = {}
    for key, value in obj.items():
        if not isinstance(key, str):
            raise ValueError(f'"{field_name}" contains a non-string key: {key!r}')
        if not isinstance(value, str):
            raise ValueError(f'"{field_name}" value for key "{key}" is not a string.')
        result[key] = value
    return result


def chunk_entries(entries: List[Tuple[str, str]], size: int) -> List[List[Tuple[str, str]]]:
    chunks: List[List[Tuple[str, str]]] = []
    for idx in range(0, len(entries), size):
        chunks.append(entries[idx : idx + size])
    return chunks


def request_chat_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: List[dict],
    temperature: float,
    timeout_sec: int,
) -> str:
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    payload = json.dumps(
        {
            "model": model,
            "temperature": temperature,
            "messages": messages,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = request.Request(
        endpoint,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with request.urlopen(req, timeout=timeout_sec) as resp:
        body = resp.read().decode("utf-8")
    data = json.loads(body)
    content = data.get("choices", [{}])[0].get("message", {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Translation API response is missing message content.")
    return content


def call_with_retry(fn, retries: int, retry_backoff_sec: float):
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception as err:  # noqa: BLE001
            last_err = err
            if attempt >= retries:
                break
            time.sleep((attempt + 1) * retry_backoff_sec)
    assert last_err is not None
    raise last_err


def _http_get_json(*, endpoint: str, api_key: str, timeout_sec: int) -> dict:
    req = request.Request(
        endpoint,
        method="GET",
        headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
    )
    with request.urlopen(req, timeout=timeout_sec) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def verify_model_endpoint(*, base_url: str, api_key: str, model: str, timeout_sec: int) -> None:
    models_endpoint = f"{base_url.rstrip('/')}/models"
    try:
        models_payload = _http_get_json(endpoint=models_endpoint, api_key=api_key, timeout_sec=timeout_sec)
        models = models_payload.get("data", [])
        model_ids = {str(item.get("id", "")) for item in models if isinstance(item, dict)}
        if model_ids and model not in model_ids:
            sample = ", ".join(sorted([m for m in model_ids if m])[:8])
            raise ValueError(
                f'Model "{model}" not found on {models_endpoint}. '
                f"Available examples: {sample or 'none'}"
            )
        print(f"[check] model endpoint OK: {models_endpoint}", flush=True)
    except error.HTTPError as err:
        if err.code != 404:
            body = err.read().decode("utf-8", errors="ignore")
            raise ValueError(f"Model endpoint check failed: HTTP {err.code}: {body}") from err
    except error.URLError as err:
        raise ValueError(f"Model endpoint check failed: {err}") from err
    except json.JSONDecodeError:
        # Some providers may not expose a standard /models payload.
        pass

    # Fallback: validate by doing a tiny chat completion request.
    _ = request_chat_completion(
        base_url=base_url,
        api_key=api_key,
        model=model,
        messages=[
            {"role": "system", "content": "Return exactly: OK"},
            {"role": "user", "content": "OK"},
        ],
        temperature=0.0,
        timeout_sec=min(timeout_sec, 45),
    )
    print(f"[check] chat completion probe OK: {base_url.rstrip('/')}/chat/completions", flush=True)


def is_locale_fully_adapted(*, output_path: Path, lang: str, source_strings: Dict[str, str]) -> bool:
    if not output_path.exists():
        return False
    try:
        data = json.loads(output_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return False
    if not isinstance(data, dict):
        return False
    strings = data.get("strings", data)
    if not isinstance(strings, dict):
        return False
    if set(strings.keys()) != set(source_strings.keys()):
        return False

    allow_cjk = lang in {"zh_CN", "zh_TW"}
    for key, source_value in source_strings.items():
        value = strings.get(key)
        if not isinstance(value, str) or not value.strip():
            return False
        if not same_placeholders(source_value, value):
            return False
        if not allow_cjk and CJK_RE.search(value):
            return False
    return True


def load_existing_locale_strings(output_path: Path) -> Dict[str, str]:
    if not output_path.exists():
        return {}
    try:
        data = json.loads(output_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    if not isinstance(data, dict):
        return {}
    strings = data.get("strings", data)
    if not isinstance(strings, dict):
        return {}
    result: Dict[str, str] = {}
    for key, value in strings.items():
        if isinstance(key, str) and isinstance(value, str):
            result[key] = value
    return result


def translate_chunk_by_order(
    *,
    lang: str,
    chunk_object: Dict[str, str],
    base_url: str,
    api_key: str,
    model: str,
    temperature: float,
    timeout_sec: int,
    retries: int,
    retry_backoff_sec: float,
) -> Dict[str, str]:
    language_name = LANGUAGE_NAMES.get(lang, lang)
    source_keys = list(chunk_object.keys())
    source_values = [chunk_object[k] for k in source_keys]

    system_prompt = " ".join(
        [
            "You are a professional software localization translator.",
            f"Translate UI messages into {language_name}.",
            'Return ONLY one valid JSON object in format {"values":[...]} with exactly the same item count and order as input.',
            "Preserve placeholders exactly, including forms like {{count}} and {{ message }}.",
            r"Preserve escaped newline markers (\n) and markdown/code syntax.",
            "Do not add commentary or code fences.",
        ]
    )
    user_prompt = "\n".join(
        [
            f"Target language code: {lang}",
            "Translate each array item value and keep strict order.",
            "Input values array:",
            json.dumps(source_values, ensure_ascii=False, indent=2),
        ]
    )

    def _do_request():
        content = request_chat_completion(
            base_url=base_url,
            api_key=api_key,
            model=model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=temperature,
            timeout_sec=timeout_sec,
        )
        parsed = json.loads(sanitize_json_text(content))
        values = parsed.get("values")
        if not isinstance(values, list) or len(values) != len(source_values):
            raise ValueError(f"Translated array mismatch for {lang}.")
        return values

    values = call_with_retry(_do_request, retries=retries, retry_backoff_sec=retry_backoff_sec)

    mapped: Dict[str, str] = {}
    for i, key in enumerate(source_keys):
        src = source_values[i]
        dst = values[i]
        if isinstance(dst, str) and same_placeholders(src, dst):
            mapped[key] = dst
        else:
            mapped[key] = src
    return mapped


def translate_chunk(
    *,
    lang: str,
    chunk_object: Dict[str, str],
    base_url: str,
    api_key: str,
    model: str,
    temperature: float,
    timeout_sec: int,
    retries: int,
    retry_backoff_sec: float,
) -> Dict[str, str]:
    language_name = LANGUAGE_NAMES.get(lang, lang)

    system_prompt = " ".join(
        [
            "You are a professional software localization translator.",
            f"Translate UI messages into {language_name}.",
            "Return ONLY one valid JSON object with exactly the same keys.",
            "Do not translate any key names.",
            "Preserve placeholders exactly, including forms like {{count}} and {{ message }}.",
            r"Preserve escaped newline markers (\n) and markdown/code syntax.",
            "Do not add commentary or code fences.",
        ]
    )
    user_prompt = "\n".join(
        [
            f"Target language code: {lang}",
            "Translate each JSON value while preserving product terminology consistency.",
            "Input JSON object:",
            json.dumps(chunk_object, ensure_ascii=False, indent=2),
        ]
    )

    source_keys = list(chunk_object.keys())

    def _do_request() -> Dict[str, str]:
        content = request_chat_completion(
            base_url=base_url,
            api_key=api_key,
            model=model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=temperature,
            timeout_sec=timeout_sec,
        )
        parsed = json.loads(sanitize_json_text(content))
        translated = flatten_object(parsed)

        if len(translated) != len(source_keys):
            raise ValueError(f"Translated key count mismatch for {lang}.")
        for key in source_keys:
            if key not in translated:
                raise ValueError(f"Translated key missing: {key}")

        mapped: Dict[str, str] = {}
        for key in source_keys:
            source_value = chunk_object[key]
            translated_value = translated.get(key)
            if not isinstance(translated_value, str):
                raise ValueError(f"Translated value is not string at key: {key}")
            if not same_placeholders(source_value, translated_value):
                raise ValueError(f"Placeholder mismatch at key: {key}")
            mapped[key] = translated_value
        return mapped

    try:
        return call_with_retry(_do_request, retries=retries, retry_backoff_sec=retry_backoff_sec)
    except Exception:  # noqa: BLE001
        return translate_chunk_by_order(
            lang=lang,
            chunk_object=chunk_object,
            base_url=base_url,
            api_key=api_key,
            model=model,
            temperature=temperature,
            timeout_sec=timeout_sec,
            retries=retries,
            retry_backoff_sec=retry_backoff_sec,
        )


def translate_one_language(
    *,
    lang: str,
    source_lang_code: str,
    source_data: dict,
    source_strings: Dict[str, str],
    base_template: dict,
    source_entries: List[Tuple[str, str]],
    output_dir: Path,
    force: bool,
    skip_adapted: bool,
    chunk_size: int,
    base_url: str,
    model: str,
    api_key: str,
    temperature: float,
    timeout_sec: int,
    retries: int,
    retry_backoff_sec: float,
) -> None:
    output_path = output_dir / f"{lang}.json"
    print(f"[start] {lang}", flush=True)
    if skip_adapted and is_locale_fully_adapted(output_path=output_path, lang=lang, source_strings=source_strings):
        print(f"[skip] {lang} already fully adapted ({output_path})", flush=True)
        return

    if lang == source_lang_code:
        output_path.write_text(json.dumps(source_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[done] {lang} copied from source language", flush=True)
        return

    translated_flat: Dict[str, str] = {}
    pending_entries: List[Tuple[str, str]] = list(source_entries)

    # 增量模式：已有语言文件时，仅翻译新增/无效条目，避免整包重跑
    if output_path.exists() and not force:
        existing_strings = load_existing_locale_strings(output_path)
        for key, source_value in source_entries:
            existing_value = existing_strings.get(key)
            if (
                isinstance(existing_value, str)
                and existing_value.strip()
                and same_placeholders(source_value, existing_value)
            ):
                translated_flat[key] = existing_value
        pending_entries = [(key, value) for key, value in source_entries if key not in translated_flat]
        if pending_entries:
            print(
                f"[{lang}] incremental mode: reuse={len(translated_flat)} pending={len(pending_entries)}",
                flush=True,
            )
        else:
            print(f"[skip] {lang} no pending keys ({output_path})", flush=True)
            return

    chunks = chunk_entries(pending_entries, chunk_size)
    for idx, chunk in enumerate(chunks, start=1):
        chunk_object = dict(chunk)
        print(f"[{lang}] chunk {idx}/{len(chunks)} request ({len(chunk)} keys)", flush=True)
        translated_chunk = translate_chunk(
            lang=lang,
            chunk_object=chunk_object,
            base_url=base_url,
            api_key=api_key,
            model=model,
            temperature=temperature,
            timeout_sec=timeout_sec,
            retries=retries,
            retry_backoff_sec=retry_backoff_sec,
        )
        for key, source_value in chunk:
            translated_flat[key] = translated_chunk.get(key, source_value)
        print(f"[{lang}] chunk {idx}/{len(chunks)} completed", flush=True)

    translated_obj = dict(base_template)
    translated_obj["strings"] = {key: translated_flat.get(key, source_value) for key, source_value in source_strings.items()}
    output_path.write_text(json.dumps(translated_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[done] {lang} -> {output_path}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch translate i18n JSON content with an LLM.")
    parser.add_argument("--source", required=True, help="Source locale JSON file path (e.g. en.json)")
    parser.add_argument("--output-dir", required=True, help="Output directory. Files are written as <lang>.json")
    parser.add_argument("--langs", required=True, help='Target language codes, comma separated (e.g. ja,ko,fr), or "all"')
    parser.add_argument("--source-lang-code", default="en", help="Source language code (default: en)")
    parser.add_argument("--base-url", default=os.getenv("LLM_BASE_URL", os.getenv("NVIDIA_BASE_URL", DEFAULT_BASE_URL)), help="OpenAI-compatible base URL")
    parser.add_argument("--model", default=os.getenv("LLM_MODEL", os.getenv("NVIDIA_MODEL", DEFAULT_MODEL)), help="Model name")
    parser.add_argument(
        "--api-key",
        default=os.getenv("LLM_API_KEY", os.getenv("NVIDIA_API_KEY", os.getenv("OPENAI_API_KEY", DEFAULT_API_KEY))),
        help="API key",
    )
    parser.add_argument("--chunk-size", type=int, default=220, help="Keys per translation chunk (default: 220)")
    parser.add_argument("--concurrency", type=int, default=3, help="Number of language workers (default: 3)")
    parser.add_argument("--temperature", type=float, default=0.2, help="Model temperature (default: 0.2)")
    parser.add_argument("--timeout-sec", type=int, default=180, help="Request timeout in seconds (default: 180)")
    parser.add_argument("--retries", type=int, default=4, help="Retry count on failure (default: 4)")
    parser.add_argument("--retry-backoff-sec", type=float, default=2.0, help="Backoff base in seconds (default: 2.0)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing locale files")
    parser.add_argument("--skip-adapted", action="store_true", default=True, help="Skip locale files that are already fully adapted (default: true)")
    parser.add_argument("--no-skip-adapted", action="store_false", dest="skip_adapted", help="Do not skip adapted locale files")
    parser.add_argument("--skip-model-check", action="store_true", help="Skip base_url/model availability check before translating")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    source_path = Path(args.source).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    langs_raw = args.langs.strip()
    langs = list(LANGUAGE_NAMES.keys()) if langs_raw.lower() == "all" else parse_langs(langs_raw)
    if args.chunk_size < 1:
        raise ValueError("--chunk-size must be >= 1")
    if args.concurrency < 1:
        raise ValueError("--concurrency must be >= 1")

    source_data = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(source_data, dict):
        raise ValueError("Source JSON must be a top-level object.")

    if "strings" in source_data:
        source_strings = ensure_string_dict(source_data.get("strings"), field_name="strings")
        base_template = dict(source_data)
        # Keep source_map untouched if it exists; ensure predictable output even if absent.
        base_template.setdefault("source_map", {})
    else:
        source_strings = ensure_string_dict(source_data, field_name="root")
        base_template = {"strings": source_strings, "source_map": {}}

    source_entries = list(source_strings.items())

    needs_remote = any(lang != args.source_lang_code for lang in langs)
    if needs_remote and not args.api_key:
        raise ValueError("Missing API key. Set --api-key or environment variable.")
    if needs_remote and not args.skip_model_check:
        verify_model_endpoint(
            base_url=args.base_url.rstrip("/"),
            api_key=args.api_key,
            model=args.model,
            timeout_sec=args.timeout_sec,
        )

    print(f"Source keys: {len(source_entries)}", flush=True)
    print(f"Target languages: {', '.join(langs)}", flush=True)
    print(f"Model: {args.model}", flush=True)
    print(f"Base URL: {args.base_url.rstrip('/')}", flush=True)

    if args.skip_adapted and not args.force:
        langs_to_process: List[str] = []
        for lang in langs:
            output_path = output_dir / f"{lang}.json"
            if is_locale_fully_adapted(output_path=output_path, lang=lang, source_strings=source_strings):
                print(f"[skip] {lang} already fully adapted ({output_path})", flush=True)
                continue
            langs_to_process.append(lang)
        langs = langs_to_process
        if not langs:
            print("All requested locales are already fully adapted.", flush=True)
            print("Locale generation completed.", flush=True)
            return 0

    failed: List[Tuple[str, str]] = []
    with ThreadPoolExecutor(max_workers=min(args.concurrency, len(langs))) as pool:
        future_map = {
            pool.submit(
                translate_one_language,
                lang=lang,
                source_lang_code=args.source_lang_code,
                source_data=source_data,
                source_strings=source_strings,
                base_template=base_template,
                source_entries=source_entries,
                output_dir=output_dir,
                force=args.force,
                skip_adapted=args.skip_adapted,
                chunk_size=args.chunk_size,
                base_url=args.base_url.rstrip("/"),
                model=args.model,
                api_key=args.api_key,
                temperature=args.temperature,
                timeout_sec=args.timeout_sec,
                retries=args.retries,
                retry_backoff_sec=args.retry_backoff_sec,
            ): lang
            for lang in langs
        }
        for future in as_completed(future_map):
            lang = future_map[future]
            try:
                future.result()
            except error.HTTPError as err:
                body = err.read().decode("utf-8", errors="ignore")
                msg = f"HTTP {err.code}: {body}"
                failed.append((lang, msg))
                print(f"[fail] {lang}: {msg}", file=sys.stderr, flush=True)
            except Exception as err:  # noqa: BLE001
                msg = str(err)
                failed.append((lang, msg))
                print(f"[fail] {lang}: {msg}", file=sys.stderr, flush=True)

    if failed:
        summary = ", ".join([f"{lang}({msg})" for lang, msg in failed])
        raise RuntimeError(f"Some languages failed: {summary}")

    print("Locale generation completed.", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as err:  # noqa: BLE001
        print(str(err), file=sys.stderr)
        raise SystemExit(1)
