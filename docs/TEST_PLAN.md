# Test Plan

## Functional Checks

- PDF upload and RAG responses
- Booking flow and confirmation
- Database save and booking ID generation
- Email failure handling
- Admin dashboard listing, search, export, cancel, and restore
- Booking retrieval by email
- Friendly validation messages for invalid email, phone, date, and time

## Automated Checks

Run:

```bash
python -m unittest discover -s tests
```

Current automated coverage includes:

- validation helpers
- booking model helpers

## External Verification

- Public Streamlit deployment still needs to be verified after deployment
- Email delivery requires valid Gmail credentials
- Groq chat requires a valid `GROQ_API_KEY`
