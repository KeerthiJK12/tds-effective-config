# IIT Madras TDS — Effective Config Service

## Run locally (Windows)

1. Install Python 3.10+.
2. Open Command Prompt in this folder.
3. Run:

   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

4. Open `http://127.0.0.1:8000/effective-config`.

Test overrides with:
`http://127.0.0.1:8000/effective-config?set=port=9000&set=debug=true`

## Configuration precedence

Defaults -> `config.development.yaml` -> `.env` -> OS environment variables with `APP_` prefix -> `set` query overrides.

`NUM_WORKERS` in `.env` maps to `workers`. `api_key` is always masked as `*****`.
