import os
from dotenv import load_dotenv
from langsmith import Client
from langsmith.run_helpers import traceable

load_dotenv()

LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv(
    "LANGSMITH_PROJECT",
    "smart-travel-planner"
)

client = Client(
    api_key=LANGSMITH_API_KEY
)

def get_langsmith_client():
    return client