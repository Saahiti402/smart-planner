# Smart Planner

## Docker Desktop

This project is ready to run as a three-container stack in Docker Desktop:

- `frontend`: Streamlit UI on `http://localhost:8501`
- `backend`: FastAPI API on `http://localhost:8000`
- `db`: PostgreSQL database on `localhost:5432`

### Before you start

Make sure the project has a local `.env` file with the API keys the backend needs. Docker Compose will automatically use those values and will override `DATABASE_URL` so the app talks to the bundled PostgreSQL container instead of an external database.

### Start the stack

```bash
docker compose up --build
```

In Docker Desktop, you can also open this folder and start the `docker-compose.yml` stack from the UI.

### Open the app

- Streamlit UI: `http://localhost:8501`
- FastAPI docs: `http://localhost:8000/docs`

### First start notes

The backend may take a little longer on its first run because `sentence-transformers` may need to download the `all-MiniLM-L6-v2` model.

If your local `chroma_db` folder is empty, you can rebuild the vector store after startup:

```bash
curl -X POST http://localhost:8000/store-rag
```

### Stop the stack

```bash
docker compose down
```

To also remove the PostgreSQL data volume:

```bash
docker compose down -v
```
