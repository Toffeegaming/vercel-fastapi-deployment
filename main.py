import re, os
from time import time
from fastapi import FastAPI, __version__, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from trueskill import Rating, rate, MU, SIGMA
from tinydb import TinyDB, Query
from typing import Union
from typing import List, Tuple


# General variables
db = TinyDB('db.json')
matches = db.table('Matches')
API_KEY = os.getenv('API_KEY')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # use token authentication
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

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


# Functions
def get_new_ratings(p1: Player, p2: Player, p3: Player, p4: Player, ranks) -> Tuple[Player, Player, Player, Player]:
    """Returns the new ratings for the players in a 2v2 game.
    :param ranks: [0,1] Team 1 won, [1,0] Team 2 won, [0,0] Draw
    :return: The new ratings for the players in the game."""
    r1 = Rating(p1.mu, p1.sigma)  # 1P's skill
    r2 = Rating(p2.mu, p2.sigma)  # 2P's skill
    r3 = Rating(p3.mu, p3.sigma)  # 3P's skill
    r4 = Rating(p4.mu, p4.sigma)  # 4P's skill

    t1 = [r1, r2] # Team 1
    t2 = [r3, r4] # Team 2

    (new_r1, new_r2), (new_r3, new_r4) = rate([t1, t2], ranks=ranks)

    new_p1 = Player(p1.name, new_r1.mu, new_r1.sigma)
    new_p2 = Player(p2.name, new_r2.mu, new_r2.sigma)
    new_p3 = Player(p3.name, new_r3.mu, new_r3.sigma)
    new_p4 = Player(p4.name, new_r4.mu, new_r4.sigma)
    return new_p1, new_p2, new_p3, new_p4

def get_player(searchName) -> Player:
    result = db.search(Query().name.matches(searchName, flags=re.IGNORECASE))
    return Player(result[0]['name'], result[0]['mu'], result[0]['sigma'])

def update_player_rating(target: Player):
    db.update({'mu': target.mu, 'sigma': target.sigma}, Query().name == target.name)

def add_player_to_db(name):
    #check if player already exists
    if db.contains(Query().name == name):
        raise HTTPException(status_code=404, detail="Player already exists")
    player = {'name': name, 'mu': MU, 'sigma': SIGMA}
    db.insert(player)
    print('Added player ' + name + ' to the database')
    return player

def reset_all_ratings():
    db.update({'mu': MU, 'sigma': SIGMA}, Query().rating.exists())

def api_key_auth(api_key: str = Depends(oauth2_scheme)):
    if api_key !=  API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Forbidden"
        )


# API Endpoints
@app.get("/")
async def root():
    return HTMLResponse(html)

@app.get('/ping')
async def hello():
    return {'res': 'pong', 'version': __version__, "time": time()}

@app.get("/api/players", dependencies=[Depends(api_key_auth)])
def read_players():
    return db.all()

@app.get("/api/players/{player_name}", dependencies=[Depends(api_key_auth)])
def read_item(player_name: str):
    return get_player(player_name)

@app.post("/api/players/{player_name}", dependencies=[Depends(api_key_auth)])
def add_player(player_name: str):
    return add_player_to_db(player_name)

@app.get("/api/matches/", dependencies=[Depends(api_key_auth)])
def read_matches():
    return matches.all()

@app.get("/api/matches/{match_id}}", dependencies=[Depends(api_key_auth)])
def read_matches(match_id: int):
    return matches.get(doc_id=match_id)

@app.post("/api/matches", dependencies=[Depends(api_key_auth)])
def play_match(p1: Union[str, None] = None, p2: Union[str, None] = None, p3: Union[str, None] = None, p4: Union[str, None] = None, result: Union[int, None] = None):
    if p1 is None or p2 is None or p3 is None or p4 is None or result is None:
        raise HTTPException(status_code=404, detail="Not all inputs were specified")
    
    if result not in [0, 1, 2]:
        raise HTTPException(status_code=404, detail="Result must be 0, 1 or 2")

    if result == 1:
        rankings = [0, 1]
    elif result == 2:
        rankings = [1, 0]
    else:
        rankings = [0, 0]

    player1 = get_player(p1)
    player2 = get_player(p2)
    player3 = get_player(p3)
    player4 = get_player(p4)

    playedMatch = Match(players=[player1, player2, player3, player4], result= result) # save ranking before match
    
    player1, player2, player3, player4 = get_new_ratings(player1, player2, player3, player4, rankings) # get new player ratings

    playedMatch.new_rankings = [player1, player2, player3, player4] # save ranking after match

    # update player ratings in database
    update_player_rating(player1)
    update_player_rating(player2)
    update_player_rating(player3)
    update_player_rating(player4)

    # save match to database

    result = {
            "players": [
            {"name": playedMatch.players[0].name, "mu": playedMatch.players[0].mu, "sigma": playedMatch.players[0].sigma},
            {"name": playedMatch.players[1].name, "mu": playedMatch.players[1].mu, "sigma": playedMatch.players[1].sigma},
            {"name": playedMatch.players[2].name, "mu": playedMatch.players[2].mu, "sigma": playedMatch.players[2].sigma},
            {"name": playedMatch.players[3].name, "mu": playedMatch.players[3].mu, "sigma": playedMatch.players[3].sigma}
            ],
            "result": playedMatch.result,
            "new_rankings": [
                {"name": playedMatch.new_rankings[0].name, "mu": playedMatch.new_rankings[0].mu, "sigma": playedMatch.new_rankings[0].sigma},
                {"name": playedMatch.new_rankings[1].name, "mu": playedMatch.new_rankings[1].mu, "sigma": playedMatch.new_rankings[1].sigma},
                {"name": playedMatch.new_rankings[2].name, "mu": playedMatch.new_rankings[2].mu, "sigma": playedMatch.new_rankings[2].sigma},
                {"name": playedMatch.new_rankings[3].name, "mu": playedMatch.new_rankings[3].mu, "sigma": playedMatch.new_rankings[3].sigma}
            ]
        }

    matches.insert(result)
    return result
