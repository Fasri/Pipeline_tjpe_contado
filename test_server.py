import sys
from pathlib import Path
sys.path.insert(0, '.')

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

BASE_DIR = Path('chatbot')
templates = Jinja2Templates(directory=BASE_DIR / 'templates')
print('Templates OK')

from fastapi.staticfiles import StaticFiles
static = StaticFiles(directory=BASE_DIR / 'static')
print('Static OK')
