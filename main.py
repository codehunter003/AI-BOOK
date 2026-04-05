from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import json
import re
import logging
import base64
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paste your free Gemini API key from: https://aistudio.google.com/app/apikey
# NOTE: File uploads require python-multipart. Install with:
#   pip install python-multipart
GEMINI_API_KEY = "give your gemini key"

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# Supported file extensions and their MIME types
SUPPORTED_AUDIO = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
    ".webm": "audio/webm",
}

SUPPORTED_VIDEO = {
    ".mp4": "video/mp4",
    ".mkv": "video/x-matroska",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
}

SUPPORTED_TEXT = {
    ".txt": "text/plain",
    ".pdf": "application/pdf",
}

ALL_SUPPORTED = {**SUPPORTED_AUDIO, **SUPPORTED_VIDEO, **SUPPORTED_TEXT}


# ─────────────────────────────────────────────
# Core Gemini call (text-only prompt)
# ─────────────────────────────────────────────
def call_gemini(prompt: str) -> str:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1024},
    }

    try:
        resp = requests.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            json=payload,
            timeout=30,
        )
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Gemini API request timed out.")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Network error: {str(e)}")

    _check_gemini_status(resp)
    return _extract_gemini_text(resp)


# ─────────────────────────────────────────────
# Gemini call with inline file data (audio/video/pdf)
# ─────────────────────────────────────────────
def call_gemini_with_file(prompt: str, file_data: bytes, mime_type: str) -> str:
    b64_data = base64.b64encode(file_data).decode("utf-8")

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_data,
                        }
                    },
                    {"text": prompt},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048},
    }

    try:
        resp = requests.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            json=payload,
            timeout=60,
        )
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Gemini API request timed out.")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Network error: {str(e)}")

    _check_gemini_status(resp)
    return _extract_gemini_text(resp)


def _check_gemini_status(resp):
    logger.info(f"Gemini response status: {resp.status_code}")
    if resp.status_code == 400:
        raise HTTPException(status_code=400, detail=f"Bad request to Gemini: {resp.text}")
    if resp.status_code == 403:
        raise HTTPException(status_code=403, detail="Gemini API key is invalid or has no permissions.")
    if resp.status_code == 429:
        raise HTTPException(status_code=429, detail="Gemini API rate limit exceeded. Try again later.")
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Gemini API error {resp.status_code}: {resp.text}")


def _extract_gemini_text(resp) -> str:
    try:
        result = resp.json()
        candidates = result.get("candidates", [])
        if not candidates:
            raise HTTPException(status_code=500, detail="Gemini returned no candidates.")
        return candidates[0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected Gemini response structure: {resp.text}")
        raise HTTPException(status_code=500, detail=f"Failed to parse Gemini response: {str(e)}")


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────
class TextRequest(BaseModel):
    text: str

class SummaryRequest(BaseModel):
    summary: str


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status": "VoiceLens backend running",
        "supported_formats": list(ALL_SUPPORTED.keys()),
    }


@app.post("/summarize")
def summarize(req: TextRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is empty")

    logger.info(f"Summarize request. Text length: {len(req.text)}")

    prompt = (
        "Summarize the following spoken text concisely in 2 to 4 sentences. "
        "Preserve all key points and important details. "
        "Return ONLY the summary text with no introduction or preamble.\n\n"
        f"Text to summarize:\n{req.text}"
    )

    try:
        summary = call_gemini(prompt)
        logger.info("Summary generated successfully.")
        return {"summary": summary}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /summarize: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-and-summarize")
async def upload_and_summarize(file: UploadFile = File(...)):
    """
    Upload an audio, video, or text file.
    Gemini will transcribe + summarize + generate Q&A automatically.

    Supported:
    - Audio : .mp3, .wav, .m4a, .ogg, .flac, .aac, .webm
    - Video : .mp4, .mkv, .mov, .avi
    - Text  : .txt, .pdf
    """
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALL_SUPPORTED:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Supported: {', '.join(ALL_SUPPORTED.keys())}",
        )

    mime_type = ALL_SUPPORTED[ext]
    logger.info(f"File upload received: {filename} ({mime_type})")

    file_data = await file.read()
    if not file_data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # 20 MB limit (Gemini inline_data limit)
    max_size = 20 * 1024 * 1024
    if len(file_data) > max_size:
        raise HTTPException(status_code=400, detail="File too large. Maximum allowed size is 20 MB.")

    # ── Step 1: Transcribe ──────────────────────
    if ext in SUPPORTED_TEXT:
        transcribe_prompt = (
            "Extract and return all the readable text from this document. "
            "Return only the raw text content, no commentary."
        )
    else:
        transcribe_prompt = (
            "Transcribe all the spoken words from this audio/video file accurately. "
            "Return only the plain transcription text."
        )

    try:
        transcription = call_gemini_with_file(transcribe_prompt, file_data, mime_type)
        logger.info(f"Transcription done. Length: {len(transcription)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    if not transcription.strip():
        raise HTTPException(status_code=500, detail="No speech or text detected in the uploaded file.")

    # ── Step 2: Summarize ───────────────────────
    summary_prompt = (
        "Summarize the following spoken text concisely in 2 to 4 sentences. "
        "Preserve all key points and important details. "
        "Return ONLY the summary text with no introduction or preamble.\n\n"
        f"Text to summarize:\n{transcription}"
    )

    try:
        summary = call_gemini(summary_prompt)
        logger.info("Summary generated from uploaded file.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")

    # ── Step 3: Generate Q&A ────────────────────
    qa_prompt = (
        "Given the following summary, generate 3 to 5 insightful question-and-answer pairs "
        "that test comprehension of the key ideas.\n\n"
        "Return ONLY a valid JSON array in this exact format:\n"
        '[{"question": "...", "answer": "..."}, ...]\n\n'
        "Rules:\n"
        "- No markdown code fences\n"
        "- No extra text before or after the JSON\n"
        "- Valid JSON only\n\n"
        f"Summary:\n{summary}"
    )

    try:
        raw = call_gemini(qa_prompt)
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
        raw = raw.strip()
        qa_pairs = json.loads(raw)
        if not isinstance(qa_pairs, list):
            qa_pairs = []
    except Exception as e:
        logger.warning(f"Q&A generation failed (non-critical): {e}")
        qa_pairs = []

    return {
        "filename": filename,
        "transcription": transcription,
        "summary": summary,
        "qa_pairs": qa_pairs,
    }


@app.post("/generate-qa")
def generate_qa(req: SummaryRequest):
    if not req.summary.strip():
        raise HTTPException(status_code=400, detail="Summary is empty")

    logger.info("Generate Q&A request received.")

    prompt = (
        "Given the following summary, generate 3 to 5 insightful question-and-answer pairs "
        "that test comprehension of the key ideas.\n\n"
        "Return ONLY a valid JSON array in this exact format:\n"
        '[{"question": "...", "answer": "..."}, ...]\n\n'
        "Rules:\n"
        "- No markdown code fences\n"
        "- No extra text before or after the JSON\n"
        "- Valid JSON only\n\n"
        f"Summary:\n{req.summary}"
    )

    try:
        raw = call_gemini(prompt)
        logger.info(f"Raw Q&A response: {raw[:200]}")

        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
        raw = raw.strip()

        qa_pairs = json.loads(raw)

        if not isinstance(qa_pairs, list):
            raise HTTPException(status_code=500, detail="Q&A response is not a list.")

        return {"qa_pairs": qa_pairs}

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse Q&A JSON: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /generate-qa: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
