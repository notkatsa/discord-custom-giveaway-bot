#!/usr/bin/python3
import discum, requests, configparser, asyncio, aiohttp, tqdm, itertools, time

limit = 15  # Number of messages to scan in the channel. MAX: 100
baseurl = "https://discord.com/api/v9"
entered_giveaways = set()

async def get_messages(session, auth_token, channel_id):
    while True:
        async with session.get(
            f"{baseurl}/channels/{channel_id}/messages?limit={limit}",
            headers={"Authorization": auth_token},
        ) as response:
            response = response
            headers = response.headers
            messages = await response.json()
        if "Retry-After" in headers:
            await asyncio.sleep(5)
            continue
        else:
            break

    return {"messages": messages, "channel_id": channel_id}

def evaluate_message(message):
    if message == []:
        print("No message")
        return
    if "Bot" in str(message) and "components" in str(message):
        if (message["components"] == []):
            return False
        
        bar = message["components"][0]
        foo = bar["components"][0]
    
        if 'emoji' in foo:
            if foo['emoji']['name'] == "🎉": # and reaction["me"] == False:
                return True
    return False

def getGuildID(channel_id, giveaway_channels):
    for guild_id, channel_ids in giveaway_channels.items():
        if channel_id in channel_ids:
            return guild_id
    return None

async def react_messages(session, auth_token, channel_id, message, guild_id):
    if (message['id'] in entered_giveaways):
        return

    bot = discum.Client(token=auth_token)
    bot.click(applicationID="294882584201003009", channelID=channel_id, messageID=message['id'], messageFlags="0", 
            guildID=guild_id, 
            data={"component_type": 2,"custom_id": "enter-giveaway"})
    entered_giveaways.add(message['id'])


    return

async def main(auth_token):
    async with aiohttp.ClientSession() as session:  # create aiohttp session

        ### FILL IN here
        giveaway_channels = {
        #   "guild_id" : ["channel_id1", "channel_id2"...],
        }
        ### GET messages
        print("Fetching messages...")
        tasks=[]
        for guild_id in giveaway_channels:
            channel_ids = giveaway_channels[guild_id]
            tasks.extend(get_messages(session, auth_token, channel_id) for channel_id in channel_ids)
        channels = []
        for t in tqdm.tqdm(asyncio.as_completed(tasks), total=len(tasks)):
            channels.append(await t)

        giveaways = []
        for channel in channels:
            for message in channel["messages"]:
                if type(message) == dict and evaluate_message(message) == True and (message["id"] not in entered_giveaways):
                    giveaways.append(
                        {"messages": message, "channel_id": channel["channel_id"], "guild_id": getGuildID(channel["channel_id"], giveaway_channels)}
                    )
        print("--------------------------")
        print(f"{len(giveaways)} giveaways found!")
        print("--------------------------")

        ### React to giveaways
        print("Joining...")
        for giveaway in giveaways:
            await react_messages(session, auth_token, giveaway["channel_id"], giveaway["messages"], giveaway["guild_id"])

def init():
    config = configparser.ConfigParser()
    config.read("config.ini")
    try:
        token = config["DEFAULT"]["token"]
    except KeyError:
        config["DEFAULT"]["token"] = input(
            "Input authentification token here: "
        ).strip()
        with open("config.ini", "w") as configfile:
            config.write(configfile)
    auth_token = config["DEFAULT"]["token"]

    print()
    print("Read token from file: " + auth_token)
    print()

    with requests.get(
        baseurl + "/users/@me", headers={"Authorization": auth_token}
    ) as response:
        response = response

    if response.status_code == 200:
        user = response.json()["username"]
        print("----------------------")
        print("Logged in with user " + user)
        print("----------------------")
        asyncio.get_event_loop().run_until_complete(main(auth_token))
        print("All servers completed!")

    elif response.status_code == 401:
        open("config.ini", "w").close()  # clear config file
        print("Wrong token!")
        print()
        init()
    elif response.status_code == 429:
        retry_after = response.headers["Retry-After"]
        exit(
            f"Too many requests! \nPlease retry again in {retry_after} seconds ({round(int(retry_after) / 60)} minute(s)).\nAlternatively, change your IP."
        )
    else:
        exit(f"Unknown error! The server returned {response}.")

import warnings

if __name__ == "__main__":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        while (1):
            init()
            print("Scanning again in 1 minute")
            time.sleep(45)

