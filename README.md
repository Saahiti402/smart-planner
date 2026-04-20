# Smart Planner

Smart Planner is an AI-powered travel planning application that helps users plan trips, compare destinations, optimize budgets, manage preferences, and ask travel questions through a conversational assistant.

The project runs as a Docker Compose stack with a Streamlit frontend, FastAPI backend, PostgreSQL database, and a local Chroma vector store for retrieval-augmented travel responses.

## Features

- User registration and login
- AI-assisted trip planning with generated itineraries
- Natural language travel assistant
- Budget optimization by destination, travelers, trip length, transport, and hotel category
- Destination comparison using local travel knowledge
- Weather, flights, hotels, and places lookup through external APIs
- User preference management
- Conversation history
- RAG support for policies, hotels, pricing, and destination documents
- FastAPI Swagger documentation
- Dockerized local development setup

## Tech Stack

- Frontend: Streamlit
- Backend: FastAPI
- Database: PostgreSQL
- ORM: SQLAlchemy
- Vector store: ChromaDB
- Embeddings: sentence-transformers
- LLM provider: Groq
- Observability: LangSmith support
- Runtime: Docker Compose

## Project Structure

```text
smart-planner/
|-- app/
|   |-- main.py                  # FastAPI routes and application startup
|   |-- auth.py                  # Password hashing and verification
|   |-- database.py              # SQLAlchemy database setup
|   |-- models.py                # Database models
|   |-- schemas.py               # Request/response schemas
|   `-- services/                # Travel, RAG, budget, LLM, and external API services
|-- rag_docs/                    # Source documents used for RAG
|-- tests/                       # Unit tests
|-- streamlit_app.py             # Streamlit frontend
|-- docker-compose.yml           # Frontend, backend, and PostgreSQL stack
|-- Dockerfile                   # Multi-stage Docker build
|-- requirements.backend.txt     # Backend dependencies
|-- requirements.frontend.txt    # Frontend dependencies
`-- README.md
```

## Prerequisites

Install these before running the project:

- Docker Desktop
- Git
- Optional for local non-Docker development: Python 3.10+

## Environment Variables

Create a `.env` file in the project root before starting the backend.

```env
GROQ_API_KEY=your_groq_api_key
SERPAPI_KEY=your_serpapi_key
OPENWEATHER_API_KEY=your_openweather_api_key
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=smart-travel-planner
```

Notes:

- `GROQ_API_KEY` is needed for AI itinerary and assistant responses.
- `SERPAPI_KEY` is used for flights, hotels, and places.
- `OPENWEATHER_API_KEY` is used for weather data.
- `LANGSMITH_API_KEY` and `LANGSMITH_PROJECT` are optional unless you want tracing.
- When using Docker Compose, `DATABASE_URL` is automatically set to the bundled PostgreSQL container.

## Run With Docker Desktop

From the project root, start the full stack:

```bash
docker compose up --build
```

After startup, open:

- Streamlit app: <http://localhost:8501>
- FastAPI backend: <http://localhost:8000>
- API documentation: <http://localhost:8000/docs>

The stack includes:

- `frontend`: Streamlit UI on port `8501`
- `backend`: FastAPI API on port `8000`
- `db`: PostgreSQL database on port `5432`

## First-Time RAG Setup

The backend can rebuild the Chroma vector store from files in `rag_docs/`.

After the backend is running, call:

```bash
curl -X POST http://localhost:8000/store-rag
```

You can test retrieval with:

```bash
curl "http://localhost:8000/search-rag?query=hotel%20policy&role=user"
```

The first backend startup may take longer because the `all-MiniLM-L6-v2` embedding model can be downloaded. Docker stores the Hugging Face cache in a volume, so future runs should be faster.

## Common API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` | Backend health check |
| `POST` | `/register` | Register a user |
| `POST` | `/login` | Log in a user |
| `POST` | `/plan-trip` | Create a trip and generate an itinerary |
| `GET` | `/ask-travel` | Ask the travel assistant |
| `POST` | `/optimize-budget` | Optimize budget with structured input |
| `POST` | `/optimize-budget-nl` | Optimize budget from natural language |
| `GET` | `/destinations` | List known destinations |
| `POST` | `/compare-destinations` | Compare destination options |
| `POST` | `/store-rag` | Rebuild the vector store |
| `GET` | `/search-rag` | Search the RAG knowledge base |
| `GET` | `/conversations` | Fetch user conversation history |

For full request and response schemas, use the Swagger UI at <http://localhost:8000/docs>.

## Stop The Stack

Stop containers while keeping saved database data:

```bash
docker compose down
```

Stop containers and remove the PostgreSQL data volume:

```bash
docker compose down -v
```

## Run Tests

If you are running outside Docker, install dependencies first:

```bash
python -m pip install -r requirements.txt
```

Then run:

```bash
python -m unittest discover tests
```

## Local Development Without Docker

Docker Compose is the recommended path because it configures PostgreSQL and service URLs automatically.

If you want to run locally without Docker:

1. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

2. Create a `.env` file with your API keys and a local `DATABASE_URL`:

   ```env
   DATABASE_URL=postgresql://planner:planner123@localhost:5432/smart_travel
   GROQ_API_KEY=your_groq_api_key
   SERPAPI_KEY=your_serpapi_key
   OPENWEATHER_API_KEY=your_openweather_api_key
   ```

3. Start the backend:

   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

4. Start the frontend in another terminal:

   ```bash
   streamlit run streamlit_app.py
   ```

## Troubleshooting

### Backend cannot connect to the database

Make sure Docker Compose is running and the `db` service is healthy:

```bash
docker compose ps
```

If you are running locally without Docker, confirm your `DATABASE_URL` points to a running PostgreSQL instance.

### AI responses fail

Check that `GROQ_API_KEY` exists in `.env` and that the backend was restarted after editing the file.

### Weather, hotel, flight, or places data is missing

Check the relevant external API keys:

- `OPENWEATHER_API_KEY` for weather
- `SERPAPI_KEY` for flights, hotels, and places

### RAG results are empty

Rebuild the vector store:

```bash
curl -X POST http://localhost:8000/store-rag
```

Also confirm that the `rag_docs/` folder contains the policy, pricing, hotel, and destination documents.

## License

No license file is currently included. Add one before publishing or distributing the project.
