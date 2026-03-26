from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from dotenv import load_dotenv
import os

ROOT_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = ROOT_DIR / 'uploads' / 'products'
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
DIST_DIR = Path(__file__).resolve().parents[1] / "frontend" / "dist"

load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]
