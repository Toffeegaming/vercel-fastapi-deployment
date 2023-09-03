import uvicorn
from time import time
from os.path import join
from fastapi import FastAPI, __version__
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from tinydb import TinyDB, Query
from typing import Union, List, Tuple

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


# Classes
class Player:
    def __init__(self, name: str, mu: float, sigma: float):
        self.name = name
        self.mu = mu
        self.sigma = sigma

class Match:
    def __init__(self, players: List[Player], result: List[int], new_rankings: List[Player] = []):
        self.players = players
        self.result = result
        self.new_rankings = new_rankings


# API endpoints
@app.get("/")
async def root():
    return HTMLResponse(html)

html = f"""
<!DOCTYPE html>
<html>
    <head>
        <title>FastAPI on Vercel</title>
        <link rel="icon" href="/static/favicon.ico" type="image/x-icon" />
    </head>
    <body>
        <div class="bg-gray-200 p-4 rounded-lg shadow-lg">
            <h1>Hello from FastAPI@{__version__}</h1>
            <ul>
                <li><a href="/docs">/docs</a></li>
                <li><a href="/redoc">/redoc</a></li>
            </ul>
            <p>Powered by <a href="https://vercel.com" target="_blank">Vercel</a></p>
        </div>
    </body>
</html>
"""

@app.get('/ping')
async def hello():
    return {'res': 'pong', 'version': __version__, "time": time()}

@app.get("/players")
def read_players():
    db = TinyDB("db.json")
    return db.all()

if __name__ == "__main__":
      uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)