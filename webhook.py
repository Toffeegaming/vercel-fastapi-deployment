from discord_webhook import AsyncDiscordWebhook
from os import getenv
async def PostWebhook(input):
    print("Posting webhook...")
    webhookUrl = getenv('DISCORD_WEBHOOK_URL')
    try:
        player1 = input[0][2][0]
        player2 = input[0][2][1]
        player3 = input[0][2][2]
        player4 = input[0][2][3]
        result = input[0][1]
        if result == [0,1]:
            webhookContent = f"{player1} en {player2} hebben gewonnen tegen {player3} en {player4}"
        elif result == [1,0]:
            webhookContent = f"{player3} en {player4} hebben gewonnen tegen {player1} en {player2}"
        else:
            webhookContent = f"{player1} en {player2} hebben gelijk gespeeld tegen {player3} en {player4}"
    except Exception as e:
        webhookContent = "Fout in data!"
        print(e)
    finally:
        webhook = AsyncDiscordWebhook(url=webhookUrl, content=webhookContent)
        await webhook.execute()
        print("Webhook posted!")
