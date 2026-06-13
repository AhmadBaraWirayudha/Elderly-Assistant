# Family AI Assistant

Final project prototype for **Maju Bareng AI by Hacktiv8 partnered with Google**.

Goal:
- one-screen assistant
- simple enough for elderly users
- playful enough for kindergarten children
- fast response path first
- image and sound support
- RAG over a small curated knowledge base

## What is included

- Streamlit UI
- Elderly mode
- Kindergarten mode
- PIN gate
- LangChain + FAISS RAG
- Gemini router with fast / standard / reasoning models
- Voice input
- Voice output
- Image input
- Friendly error handling
- Ready-to-edit knowledge base in `rag/kb/`

## Project layout

```text
elderly_assistant/
├── app.py
├── config.py
├── router.py
├── requirements.txt
├── README.md
├── .env.example
├── rag/
│   ├── chain.py
│   └── kb/
│       ├── medications.txt
│       ├── appointments.txt
│       ├── contacts.txt
│       ├── howto.txt
│       ├── faqs.txt
│       └── ai_basics.txt
├── audio/
│   ├── stt.py
│   └── tts.py
├── providers/
│   └── gemini_client.py
└── utils/
    ├── state.py
    ├── auth.py
    ├── errors.py
    └── history.py
```

## Setup

### 1) Create a virtual environment

```bash
python -m venv .venv
```

### 2) Activate it

Windows:

```bash
.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Add your API key

Copy `.env.example` to `.env` and fill in:

```bash
GEMINI_API_KEY=your_key_here
```

Optional overrides:
- `APP_MODE=elderly` or `APP_MODE=kid`
- `PIN_ENABLED=1`
- `ACCESS_PIN_HASH=<sha256 hash>`
- `GEMINI_MODEL_FLASH_LITE=gemini-2.5-flash-lite`
- `GEMINI_MODEL_FLASH=gemini-2.5-flash`
- `GEMINI_MODEL_REASONING=gemini-2.5-pro`
- `GEMINI_MODEL_TTS=gemini-3.1-flash-tts-preview`

## Run

```bash
streamlit run app.py
```

## PIN

Default PIN:
- `1234`

Change it before real use.

Generate a new hash:

```python
import hashlib
print(hashlib.sha256(b"your_new_pin").hexdigest())
```

Put the result into:

```bash
ACCESS_PIN_HASH=...
```

## How the routing works

The app routes requests using:
- image presence
- retrieval score from the KB
- query length
- mode (elderly vs kindergarten)

Routing idea:
- `flash_lite` for easy, high-confidence, short requests
- `flash` for normal requests
- `reasoning` for low-confidence or more complex requests
- `vision` for image-based requests

## How to extend the KB

Edit or add `.txt` files in:

```text
rag/kb/
```

Then delete the FAISS cache folder:

```text
rag/faiss_index
```

The app will rebuild the index on the next run.

## Voice and image

- Voice input uses `st.audio_input`
- Image input uses `st.camera_input` and `st.file_uploader`
- Voice output is generated as a WAV file and played in Streamlit

## Next steps

- Add better STT fallback for offline use
- Add true streaming UI tokens
- Add per-mode prompt templates in separate files
- Add teacher/guardian admin screen
- Add progress badges for kindergarten mode
- Add OCR for uploaded documents and medicine labels
- Add persistent chat history in SQLite
- Add user profiles for elderly users and children
- Add analytics for response latency and task success
- Add safer content filters for child mode
- Add multi-user session isolation

## Notes

- Live API was intentionally dropped to keep the first version simple.
- This prototype is designed for clarity and low confusion, not feature density.
- The code is intentionally modular so the router and providers can be swapped later.
