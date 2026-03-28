# Hotel Booking Assistant - AI Concierge

An AI-powered hotel booking assistant built with Streamlit, LangChain, Groq, FAISS, and SQLite.

## Features

- RAG chatbot over bundled hotel docs and user-uploaded PDFs
- Conversational booking with structured slot filling
- Booking retrieval by guest email
- Confirmation summary before database write
- Email confirmation after successful booking
- Admin dashboard with search, export, cancel, restore, and status override
- Short-term memory across the last 25 messages

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure secrets

Edit `.streamlit/secrets.toml` with your real values:

```toml
GROQ_API_KEY = "gsk_your_key_here"
EMAIL_SENDER = "your@email.com"
EMAIL_PASSWORD = "xxxx xxxx xxxx xxxx"
```

### 3. Run locally

```bash
streamlit run app/main.py
```

## Deployment

This project is ready for Streamlit Cloud deployment. After pushing to GitHub:

1. Create a new Streamlit Cloud app
2. Point the entry file to `app/main.py`
3. Add the same secrets in the Streamlit Cloud dashboard
4. Verify end-to-end booking, email, and admin flows

## Live Demo

Streamlit App: https://hotel-booking-chatbot-varun.streamlit.app
GitHub Repo: https://github.com/Varun-2311/hotel-booking-chatbot

## Project Structure

```text
hotel_booking_assistant/
|-- app/
|   |-- main.py
|   |-- chat_logic.py
|   |-- booking_flow.py
|   |-- rag_pipeline.py
|   |-- tools.py
|   |-- admin_dashboard.py
|   |-- config.py
|   `-- validation.py
|-- db/
|   |-- database.py
|   `-- models.py
|-- docs/
|-- tests/
|-- .streamlit/
|   `-- secrets.toml
`-- requirements.txt
```

## Submission Support

Supporting assignment material is included in `docs/`:

- `ARCHITECTURE.md`
- `TEST_PLAN.md`
- `FUTURE_IMPROVEMENTS.md`

Run the lightweight automated checks with:

```bash
python -m unittest discover -s tests
```

## Notes

- SQLite is acceptable for the assignment and resets on some cloud restarts
- FAISS is rebuilt per session from bundled docs and uploaded files
- Live chat and email require valid Groq and Gmail credentials
