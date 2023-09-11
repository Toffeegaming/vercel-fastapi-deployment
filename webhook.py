from discord_webhook import AsyncDiscordWebhook
from os import getenv

async def PostWebhook(input):
    webhookUrl = getenv('DISCORD_WEBHOOK_URL')
    try:
        player1 = input['players']['1']['name']
        player2 = input['players']['2']['name']
        player3 = input['players']['3']['name']
        player4 = input['players']['4']['name']
        result = input['result']
        if result == 1:
            webhookContent = f"{player1} en {player2} hebben gewonnen tegen {player3} en {player4}"
        elif result == 2:
            webhookContent = f"{player3} en {player4} hebben gewonnen tegen {player1} en {player2}"
        else:
            webhookContent = f"{player1} en {player2} hebben gelijk gespeeld tegen {player3} en {player4}"
    except:
        webhookContent = "Fout in data!"

    webhook = AsyncDiscordWebhook(url=webhookUrl, content=webhookContent)
    await webhook.execute()
