# Mock Buddy

Mock Buddy is a Streamlit mock-interview app that builds questions from a resume and generates AI feedback and per-answer scores.

## Run locally

Install the system packages listed in `Mock_INTERVIEW/packages.txt`, then install Python dependencies and run the app:

```powershell
python -m pip install -r requirements.txt
streamlit run Mock_INTERVIEW/app.py
```

Set API credentials in `Mock_INTERVIEW/.env` for local development:

```env
QUESTION_OPENAI_API_KEY=your_question_provider_key
FEEDBACK_OPENAI_API_KEY=your_feedback_provider_key
```

For Groq feedback credentials, the app selects Groq's OpenAI-compatible endpoint and its configured default model automatically. Never commit `.env` or credentials.

## Free deployment on Streamlit Community Cloud

1. Use this project folder as the GitHub repository root. Keep the repository private if it contains personal information or unpublished code.
2. In Streamlit Community Cloud, create an app from that repository.
3. Set **Main file path** to `Mock_INTERVIEW/app.py`.
4. Add these secrets in the app settings. Use the provider-specific model and endpoint if you need to override the defaults:

   ```toml
   QUESTION_OPENAI_API_KEY = "your_question_provider_key"
   FEEDBACK_OPENAI_API_KEY = "your_feedback_provider_key"
   ```

5. The repository-root `requirements.txt` and `packages.txt` provide the Python and Linux system dependencies used by the app.
6. Deploy and test with a non-sensitive sample resume.

The app's uploaded resumes and SQLite interview history are stored on the app filesystem. Streamlit Community Cloud's filesystem is not durable across app restarts or redeploys, so don't rely on it for permanent or shared interview history. Use non-sensitive test data until persistent storage is configured.
