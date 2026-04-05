# VoiceLens 🎙

**Speak. Distil. Understand.**

VoiceLens is a lightweight web app that turns spoken audio, video, and text files into structured knowledge — transcription, detailed summaries, and auto-generated Q&A pairs — powered by Google Gemini and OpenAI Whisper.

---

## Features

- **Live Voice Recording** — Record directly in the browser using the Web Speech API. Transcription appears in real time as you speak.
- **File Upload** — Upload audio, video, or text files and get a full transcription, summary, and Q&A automatically.
- **AI Summarization** — Gemini generates detailed multi-paragraph summaries covering all key points, decisions, and important details.
- **Q&A Generation** — Automatically produces 8–10 insightful question and answer pairs including factual, analytical, and open-ended discussion questions.
- **Local Transcription** — Audio and video files are transcribed locally using OpenAI Whisper — your audio never leaves your machine.
- **Clean Dark UI** — Minimal, distraction-free interface with tab-based navigation between voice and file upload modes.

---

## Supported File Formats

| Type  | Extensions |
|-------|-----------|
| Audio | `.mp3` `.wav` `.m4a` `.ogg` `.flac` `.aac` `.webm` |
| Video | `.mp4` `.mkv` `.mov` `.avi` |
| Text  | `.txt` `.pdf` |

Maximum file size: **100 MB**

---

## Tech Stack

| Layer     | Technology |
|-----------|-----------|
| Frontend  | Vanilla HTML / CSS / JavaScript |
| Backend   | Python, FastAPI |
| AI Model  | Google Gemini 2.0 Flash (summarization, Q&A) |
| Transcription | OpenAI Whisper (local, offline) |
| Audio conversion | ffmpeg |

---

## Prerequisites

- Python 3.9 or higher
- ffmpeg installed and available in PATH
- A free Google Gemini API key

### Install ffmpeg

**Windows:** Download from https://ffmpeg.org/download.html and add to PATH

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

---

## Installation

**1. Clone the repository**
```bash
git clone https://github.com/yourusername/voicelens.git
cd voicelens
```

**2. Install Python dependencies**
```bash
pip install fastapi uvicorn requests openai-whisper torch torchaudio python-multipart
```

**3. Add your Gemini API key**

Open `main.py` and replace the placeholder on this line:
```python
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
```

Get a free key at: https://aistudio.google.com/app/apikey

---

## Running the App

**Start the backend:**
```bash
uvicorn main:app --reload
```

The API will be running at `http://localhost:8000`

**Open the frontend:**

Open `index.html` directly in your browser. No build step needed.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/` | Health check, returns supported formats |
| `POST` | `/summarize` | Summarize plain text input |
| `POST` | `/upload-and-summarize` | Upload file → transcribe → summarize → Q&A |
| `POST` | `/generate-qa` | Generate Q&A from a summary string |

### Example: Summarize text

```bash
curl -X POST http://localhost:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{"text": "Your spoken text here..."}'
```

### Example: Upload a file

```bash
curl -X POST http://localhost:8000/upload-and-summarize \
  -F "file=@your_audio.mp3"
```

**Response:**
```json
{
  "filename": "your_audio.mp3",
  "transcription": "...",
  "summary": "...",
  "qa_pairs": [
    { "question": "...", "answer": "..." }
  ]
}
```

---

## Project Structure

```
voicelens/
├── main.py       # FastAPI backend
├── index.html    # Frontend (single file, no build needed)
└── README.md
```

---

## Notes

- The **Start Recording** button requires a Chromium-based browser (Chrome, Edge) as Firefox has limited Web Speech API support.
- Whisper transcription runs **entirely on your local machine** — audio files are never sent to any external server.
- Gemini is only used for summarization and Q&A generation, not for audio processing.
- First run will download the Whisper `base` model (~140 MB) automatically.

---

## License

MIT License. Feel free to use, modify, and distribute.
<img width="1881" height="878" alt="image" src="https://github.com/user-attachments/assets/dbf4a677-013d-457c-889f-6032123fe9b8" />
<img width="1880" height="864" alt="image" src="https://github.com/user-attachments/assets/e9601710-69c7-48c9-b6b5-baae4c341bb5" />
