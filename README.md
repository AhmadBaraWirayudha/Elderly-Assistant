# Elderly Assistant, Simple AI Dashboard for Elderly

> **Maju Bareng AI 2025 · Hacktiv8 × Google**
>
> *Voice-first · Photo-aware · Single screen · Powered by Gemini 2.5*

---

## What Is this?

Most AI tools overwhelm elderly users with dense menus, tiny buttons, and walls of text.
**Elderly Assistant does the opposite.**

One screen. Three big input modes: **Speak, Type, Photo**.
Every answer is spoken aloud. No confusion. No clutter.

Built on Gemini 2.5 and LangChain RAG, it routes each query to the right model
automatically: fast and cheap for simple questions, more capable for complex ones all
invisible to the user.

---

## Features at a Glance

| Feature | Detail |
|---|---|
| 🎤 **Voice input** | Record a question; Gemini transcribes it instantly |
| ⌨️ **Text input** | Large text box with a single big button |
| 📷 **Photo input** | Point at a medicine label, document, or appliance and get a plain explanation |
| 🔊 **Auto read-aloud** | Every answer is spoken back with TTS |
| 🧠 **Smart model router** | Flash-Lite for simple hits · Flash for medium · Pro for complex reasoning |
| 📚 **Personal knowledge base** | RAG over your own docs: meds, contacts, appointments, device guides, FAQs |
| 🔐 **PIN protection** | Simple 4-digit PIN keeps family data private |
| 💬 **Chat history** | Every conversation saved to SQLite for review |
| ⚡ **Immediate acknowledgement** | "I heard you" shows before the answer, no silent wait |
| 🎨 **Elderly-first design** | 22 px base font · large buttons · high contrast · Google colour palette |

---

## Architecture

```
User
  ├── 🎤 Speak  → Gemini STT (Files API)
  ├── ⌨️ Type   → plain text
  └── 📷 Photo  → Gemini Vision (PIL image)
          │
          ▼
   LangChain RAG
   (FAISS + Gemini Embeddings → personal knowledge base)
          │
          ▼
   Model Router
   ├── Flash-Lite  — high KB score + short query
   ├── Flash       — medium confidence / moderate length
   └── Pro         — low KB score / complex reasoning
          │
          ▼
   Streaming answer  →  TTS (gTTS)
          │
          ▼
   SQLite chat history
```

---

## Quick Start

### Prerequisites

- Python 3.10 or higher
- A Gemini API key, get one free at [Google AI Studio](https://aistudio.google.com/)

---

### Step 1 - Clone the project

```bash
git clone https://github.com/your-username/elderai.git
cd elderai
```

### Step 2 - Create a virtual environment (recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### Step 3 - Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 - Add your Gemini API key

Open `config.py` and replace the placeholder:

```python
GEMINI_API_KEY = "INSERT_YOUR_KEY_HERE"
```

with your actual key from [aistudio.google.com](https://aistudio.google.com/).

### Step 5 - Personalise the knowledge base *(optional but recommended)*

Open the `.txt` files inside `rag/kb/` and fill in your real information:

| File | What to add |
|---|---|
| `medications.txt` | Medicines with dosage and timing |
| `appointments.txt` | Doctor names, clinic phones, next visit dates |
| `contacts.txt` | Family members, neighbours, emergency numbers |
| `howto.txt` | Device guides for TV, phone, Wi-Fi, etc. |
| `faqs.txt` | Common questions and answers in plain language |

You can add new `.txt` files too — they are picked up automatically.

### Step 6 - Run the app

```bash
streamlit run app.py
```

Open your browser to **http://localhost:8501**

> **Default PIN is `1234`.**
> Change it by running:
> ```bash
> python -c "import hashlib; print(hashlib.sha256(b'your_new_pin').hexdigest())"
> ```
> and pasting the output into `PIN_HASH` in `config.py`.

---

## Project Structure

```
elderai/
├── app.py                   ← Main Streamlit entry point
├── config.py                ← API key, model names, all tunables
├── router.py                ← Model selection logic
├── requirements.txt
├── README.md
│
├── .streamlit/
│   └── config.toml          ← Theme (Google colours, font, port)
│
├── rag/
│   ├── chain.py             ← LangChain LCEL chain + FAISS + Gemini embeddings
│   └── kb/                  ← Personal knowledge base (plain .txt files)
│       ├── medications.txt
│       ├── appointments.txt
│       ├── contacts.txt
│       ├── howto.txt
│       └── faqs.txt
│
├── audio/
│   ├── stt.py               ← Speech-to-text via Gemini Files API
│   └── tts.py               ← Text-to-speech via gTTS
│
└── utils/
    ├── state.py             ← Single session_state initialiser
    ├── auth.py              ← PIN gate
    ├── errors.py            ← Elderly-friendly error messages
    └── history.py           ← SQLite persistence
```

---

## Configuration Reference

All settings live in `config.py`:

| Key | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | `INSERT_YOUR_KEY_HERE` | Your key from Google AI Studio |
| `GEMINI_MODELS` | flash-lite / flash / pro | Model names per tier |
| `ROUTER` thresholds | 0.80 / 0.55 / 40 / 80 | Score and word-count cutoffs |
| `TTS_LANG` | `"en"` | Change to `"id"` for Bahasa Indonesia |
| `PIN_HASH` | `1234` (hashed) | SHA-256 hash of your PIN |
| `MAX_HISTORY` | `6` | Conversation turns kept in context |

---

## Troubleshooting

**"Please add the API key"** → Open `config.py` and insert your Gemini key.

**FAISS index errors on first run** → Delete the `kb_index/` folder and restart. It rebuilds automatically.

**Voice tab not working** → Gemini STT uploads audio to the Files API. Make sure your API key has Files API access enabled and your network allows outbound HTTPS.

**TTS has no sound** → Your browser may block autoplay. The audio widget is still shown press the play button manually.

**Very slow first startup** → The FAISS index is being built from your KB documents. This only happens once; it loads from disk on all future runs.

---

## Hopes for the Next: Roadmap

This prototype solves the core UX problem. Here is where we want to take it:

### Near Term
- 🌏 **Full Bahasa Indonesia support** with a language toggle on the main screen
- 🗣️ **Gemini Live API integration** true real-time conversational voice, replacing the record-transcribe-respond loop for dramatically lower latency
- ☁️ **Google Cloud TTS upgrade** natural, expressive voices replacing gTTS
- 💊 **Medication reminder scheduler** set reminders once; receive push notifications daily

### Medium Term
- 👨‍👩‍👧 **Family caregiver portal** a separate web view for family members to update the knowledge base, review conversation history, and add new contacts remotely
- 🧠 **Cross-session memory** remember the user's name, preferences, and recent health notes across all conversations
- 📊 **Health tracking** log blood pressure, blood sugar, or weight through voice and visualise trends over time
- 🔐 **End-to-end encryption** protect all health data in transit and at rest (AES-256 + TLS)
- 🌐 **Deploy to Streamlit Cloud / Cloud Run** shareable URL for family members to set up for their parents in minutes

### Long Term
- 📱 **Dedicated mobile app** (Flutter) larger touch targets, haptic feedback, offline mode
- 👁️ **Fall detection** continuous background monitoring via device camera with automatic family alert
- 🏥 **Healthcare integration** connect to Indonesian public health records (BPJS) for appointment booking and lab results
- 🔈 **Wake word activation** "Hei ElderAI, tolong…" no screen tapping needed
- 📵 **Offline mode** on-device small language model for areas with poor connectivity
- 🌍 **Multi-language KB** auto-detect and respond in the user's regional language (Javanese, Sundanese, Batak, etc.)

---

## Team

Built for **Maju Bareng AI 2025** Final Project, a programme by [Hacktiv8](https://hacktiv8.com) in partnership with Google, bringing AI education and real-world applications to Indonesia. Developed by Ahmad Bara Wirayudha.
