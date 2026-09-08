# Aurum — Smart Investment Guide

AI-powered Flask web app for Indian investment education, SIP planning, goal planning, portfolio rebalancing, crash simulation, and personalised AI explanations using **Google Gemini**.

> Educational use only. This app does not provide professional financial advice. Users should verify information and consult a qualified financial advisor before investing.

## What changed

- Removed all Gemini or Gemini code and UI text.
- Added Google Gemini support using `google-genai`.
- Uses `.env` for `GEMINI_API_KEY`.
- Replaced plain SHA-256 password hashing with Werkzeug salted password hashing.
- Keeps backward compatibility for old demo users and upgrades their password hash after successful login.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create your `.env` file

Create a file named `.env` in the same folder as `app.py`:

```env
GEMINI_API_KEY=your_real_gemini_api_key_here
SECRET_KEY=change-this-random-secret-key
```

Do not put quotes around the key.

### 3. Run the app

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Gemini usage

The backend uses:

```python
model="gemini-2.5-flash"
```

Gemini powers:

| Feature | Gemini does |
|---|---|
| AI Chat | Answers Indian investment questions |
| Goal Planner | Generates personalised goal advice |
| Health Score | Explains financial health score |
| Rebalancer | Explains allocation changes |
| Crash Simulator | Gives calm market-crash guidance |
| Suggestions | Generates investment instrument suggestions |

## Security notes

This project now uses Werkzeug password hashing instead of plain SHA-256. For a production app, also add:

- Real database instead of JSON file storage
- HTTPS
- CSRF protection
- Rate limiting
- Strong secret key
- Proper input validation and logging

## Troubleshooting

If you see:

```text
AI advisor is offline. Please configure your GEMINI_API_KEY
```

Check:

1. `.env` is in the same folder as `app.py`.
2. `.env` contains the real full key, not a placeholder.
3. You installed dependencies with `pip install -r requirements.txt`.
4. Restart the Flask server after changing `.env`.

Test key loading:

```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('GEMINI_API_KEY'))"
```
