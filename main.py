import uvicorn, psycopg2, os
from time import time
from fastapi import FastAPI, __version__, HTTPException, Depends, Body, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from trueskill import Rating, rate, MU, SIGMA
from typing import Union, List, Tuple


CONN_STRING = os.getenv('DATABASE_URL')

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # use token authentication
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
API_KEY = os.getenv('API_KEY')


# Classes
class Player:
    def __init__(self, name: str, mu: float, sigma: float):
        self.name = name
        self.mu = mu
        self.sigma = sigma

class Match:
    def __init__(self, result: List[int], players: List[Player], new_rankings: List[Player] = []):
        self.result = result
        self.players = players
        self.new_rankings = new_rankings


# Functions
def api_key_auth(api_key: str = Depends(oauth2_scheme)):
    if api_key !=  API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Forbidden"
        )
    
def db_execute(query: str):
    try:
        with psycopg2.connect(CONN_STRING) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                return cur.fetchall()
    except:
        print('Error during execution of query: ' + query)

def db_info():
    try:
        with psycopg2.connect(CONN_STRING) as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT NOW();')
                time = cur.fetchone()[0]

                cur.execute('SELECT version();')
                version = cur.fetchone()[0]
                print('Current time:', time)
                print('PostgreSQL version:', version)
    except:
        print('Error during getting database info')

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

def get_player(searchName: str) -> Player:
    result = db_execute('SELECT * FROM players WHERE UPPER(name) = UPPER(\'' + searchName + '\');')
    return Player(result[0][1], result[0][2], result[0][3])

def get_player_by_id(player_id: int) -> Player:
    result = db_execute('SELECT * FROM players WHERE id = ' + str(player_id) + ';')
    return Player(result[0][1], float(result[0][2]), float(result[0][3]))

def get_match(match_id: int) -> Match:
    result = db_execute('SELECT * FROM matches WHERE id = ' + str(match_id) + ';')[0]
    return Match(
        result=result[1],
        players= [
            Player(result[2][0] ,mu=result[5][0],sigma=result[6][0]),
            Player(result[2][1] ,mu=result[5][1],sigma=result[6][1]),
            Player(result[2][2] ,mu=result[5][2],sigma=result[6][2]),
            Player(result[2][3] ,mu=result[5][3],sigma=result[6][3])],
        new_rankings= [
            Player(result[2][0] ,mu=result[3][0],sigma=result[4][0]),
            Player(result[2][1] ,mu=result[3][1],sigma=result[4][1]),
            Player(result[2][2] ,mu=result[3][2],sigma=result[4][2]),
            Player(result[2][3] ,mu=result[3][3],sigma=result[4][3])]
        )


def update_player_rating(target: Player):
    result = db_execute('UPDATE players SET mu = ' + str(target.mu) + ', sigma = ' + str(target.sigma) + ' WHERE UPPER(name) = UPPER(\'' + target.name + '\') RETURNING *;')
    return Player(result[0][1], result[0][2], result[0][3])

def add_player_to_db(name):
    return db_execute(f"INSERT INTO players (name, mu, sigma) VALUES ('{name}', {MU}, {SIGMA}) RETURNING *;")

def add_match_to_db(match: Match): # INSERT INTO matches (results, player_names, player_new_mu, player_new_sigma) VALUES (ARRAY[1,0], ARRAY[1,2,3,4], ARRAY[26.0,26.0,24.0,24.0], ARRAY[7.2,7.2,7.2,7.2]) RETURNING *;
    query =f"INSERT INTO matches (results, player_names, player_new_mu, player_new_sigma, player_old_mu, player_old_sigma) VALUES (ARRAY{match.result}, ARRAY['{match.players[0].name}', '{match.players[1].name}', '{match.players[2].name}', '{match.players[3].name}'], ARRAY[{match.new_rankings[0].mu}, {match.new_rankings[1].mu}, {match.new_rankings[2].mu}, {match.new_rankings[3].mu}],ARRAY[{match.new_rankings[0].sigma}, {match.new_rankings[1].sigma}, {match.new_rankings[2].sigma}, {match.new_rankings[3].sigma}],ARRAY[{match.players[0].mu}, {match.players[1].mu}, {match.players[2].mu}, {match.players[3].mu}],ARRAY[{match.players[0].sigma}, {match.players[1].sigma}, {match.players[2].sigma}, {match.players[3].sigma}]) RETURNING *;"
    return db_execute(query)

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

@app.get("/players", dependencies=[Depends(api_key_auth)])
def read_players():
    players = db_execute('SELECT * FROM players;')
    result = {}
    for player in players:
        playerDict = {player[0]: {'name': player[1], 'mu': float(player[2]), 'sigma': float(player[3])} }
        result = result | playerDict
    return result

@app.get("/players/{player_name}", dependencies=[Depends(api_key_auth)])
def read_player(player_name: str):
    return get_player(player_name)

@app.post("/players/{player_name}", dependencies=[Depends(api_key_auth)])
def add_player(player_name: str):
    return add_player_to_db(player_name)

@app.get("/players/id/{player_id}", dependencies=[Depends(api_key_auth)])
def read_player_by_id(player_id: int):
    return get_player_by_id(player_id)

@app.get("/matches/", dependencies=[Depends(api_key_auth)])
def read_matches():
    matches = db_execute('SELECT * FROM matches;')
    result = {}
    for match in matches:
        matchDict = {
            match[0]: Match(
                result=match[1],
                players= [
                    Player(match[2][0] ,mu=match[5][0],sigma=match[6][0]),
                    Player(match[2][1] ,mu=match[5][1],sigma=match[6][1]),
                    Player(match[2][2] ,mu=match[5][2],sigma=match[6][2]),
                    Player(match[2][3] ,mu=match[5][3],sigma=match[6][3])],
                new_rankings= [
                    Player(match[2][0] ,mu=match[3][0],sigma=match[4][0]),
                    Player(match[2][1] ,mu=match[3][1],sigma=match[4][1]),
                    Player(match[2][2] ,mu=match[3][2],sigma=match[4][2]),
                    Player(match[2][3] ,mu=match[3][3],sigma=match[4][3])]
                )
            }
        result = result | matchDict
    return result

@app.get("/matches/{match_id}}", dependencies=[Depends(api_key_auth)])
def read_matches(match_id: int):
    return get_match(match_id)

@app.post("/matches", dependencies=[Depends(api_key_auth)])
def play_match(playerId1: Union[str, None] = None, playerId2: Union[str, None] = None, playerId3: Union[str, None] = None, playerId4: Union[str, None] = None, result: Union[int, None] = None):
    if playerId1 is None or playerId2 is None or playerId3 is None or playerId4 is None or result is None:
        raise HTTPException(status_code=404, detail="Not all inputs were specified")

    if result not in [0, 1, 2]:
        raise HTTPException(status_code=404, detail="Result must be 0, 1 or 2")

    if result == 1:
        rankings = [0, 1]
    elif result == 2:
        rankings = [1, 0]
    else:
        rankings = [0, 0]

    player1 = get_player_by_id(playerId1)
    player2 = get_player_by_id(playerId2)
    player3 = get_player_by_id(playerId3)
    player4 = get_player_by_id(playerId4)

    playedMatch = Match(players=[player1, player2, player3, player4], result=rankings) # save ranking before match
    
    player1, player2, player3, player4 = get_new_ratings(player1, player2, player3, player4, rankings) # get new player ratings
    playedMatch.new_rankings = [player1, player2, player3, player4] # save ranking after match

    # update player ratings in database
    update_player_rating(player1)
    update_player_rating(player2)
    update_player_rating(player3)
    update_player_rating(player4)

    return add_match_to_db(playedMatch)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)