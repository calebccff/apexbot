
import discord
from discord.ext import commands
import requests
import asyncio
import json
import checks

config = json.load(open("config.json"))
users = json.load(open("users.json"))
objects = json.load(open("objects.json"))
suggestions = json.load(open("suggestions.json"))
bot = commands.Bot(command_prefix=config["prefix"], description=config["description"],
    max_messages=10000)
server = None

@bot.event
async def on_ready():
    global server
    print("Logged in as", bot.user.name)
    server = list(bot.servers)[0]
    await get_rolepick_message()
    #bot.loop.create_task(status_loop())
    await bot.change_presence(game=discord.Game(name="with the mortals"))
    bot.loop.create_task(users_update())

async def spam_filter(message):
    print("Running spam filter")
    words = open("banned", "r").readlines()
    print(message.content.lower())
    for word in [w.strip() for w in words]:
        if word in message.content.lower():
            users[get_fromid(users, "id", message.author.id)]["strikes"] += 1
            await bot.send_message(message.channel, "That is a banned word, please be kind, like Shaggy. Shaggy only uses 0.003\% of his power to be kind")
            await bot.http.delete_message(message.channel.id, message.id)

async def save_json(obj, file):
    f = open(file+".json", "w")
    json.dump(obj, f, indent=4)
    f.close()

def start():
    bot.run(open("token").readlines()[0])

def get_fromid(obj, key, id):
    try:
        return [x[key] for x in obj].index(id)
    except ValueError:
        return None

async def status_loop():
    await bot.wait_until_ready()
    playing = 0
    text = open("illhaveyouknow", "r").read()
    while not bot.is_closed:
        await bot.change_presence(game=discord.Game(
            name=text[playing:playing+25]))
        playing += 15
        if playing > len(text):
            playing = 0
        await asyncio.sleep(3)

async def users_update():
    global users
    await bot.wait_until_ready()
    while not bot.is_closed:
        for mem in server.members:
            if mem.bot:
                continue
            if get_fromid(users, "id", mem.id) is not None:
                #print("Updating-"+str(n)+": "+mem.display_name)
                users[get_fromid(users, "id", mem.id)]["nick"] = mem.display_name
            else:
                users.append({"id": mem.id, "nick": mem.display_name, "origin": "", "strikes": 0, "kills": 0, "damage": 0, "level": 0, "main": "", "thumbnail": ""})
            originuser = users[get_fromid(users, "id", mem.id)]["origin"]
            if originuser:
                stats = await get_stats(originuser)
                await update_stats(mem.id, stats)
            await asyncio.sleep(3/len(server.members)) #Prevent rate limit maybe?
        await save_json(users, "users")
        #await asyncio.sleep(10)

async def handle_suggestion(message):
    await bot.add_reaction(message, "\u2B06")
    await bot.add_reaction(message, "\u2B07")
    suggestions.append({"id": message.id, "text": message.content, "up": 0, "down": 0})
    print(suggestions)
    await save_json(suggestions, "suggestions")

async def get_rolepick_message():
    mid = objects["messages"]["rolepick"]
    deleted = False
    try:
        message = await bot.get_message(server.get_channel(objects["channels"]["welcome"]), mid)
        bot.messages.append(message)
    except discord.errors.NotFound:
        deleted = True
    if mid == "" or deleted:
        await bot.send_message(server.get_channel(objects["channels"]["welcome"]),
            "React to this message to assign yourself roles")

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    emote = reaction.emoji
    message = reaction.message
    if get_fromid(suggestions, "id", message.id) is not None: #Reaction to suggestion
        if emote == "\u2B06":
            suggestions[get_fromid(suggestions, "id", message.id)]["up"] += 1
        elif emote == "\u2B07":
            suggestions[get_fromid(suggestions, "id", message.id)]["down"] += 1
        else:
            #remove reaction
            await bot.remove_reaction(message, emote, user)
        await save_json(suggestions, "suggestions")
        return
    
    
    if message.id == objects["messages"]["rolepick"]:
        if type(emote) is discord.Emoji:
            if emote.id not in [x["id"] for x in list(objects["emotes"].values())]:
                await bot.remove_reaction(message, reaction.emoji, user)
            print("User reacted to role pick message")
            for eid, rid in [[x["id"], x["role"]] for x in list(objects["emotes"].values())]:
                if emote.id == eid:
                    await bot.add_roles(user, discord.utils.get(server.roles, id=rid))
        else:
            await bot.remove_reaction(message, emote, user)

@bot.event
async def on_reaction_remove(reaction, user):
    emote = reaction.emoji
    message = reaction.message
    if user.bot:
        return
    if type(emote) is discord.Emoji and message.id == objects["messages"]["rolepick"]:
        print("User reacted to role pick message")
        for eid, rid in [[x["id"], x["role"]] for x in list(objects["emotes"].values())]:
            if emote.id == eid:
                await bot.remove_roles(user, discord.utils.get(server.roles, id=rid))

@bot.event
async def on_message(message):
    if message.author.bot:
        if message.channel.id == objects["channels"]["welcome"]:
            objects["messages"]["rolepick"] = message.id
            await save_json(objects, "objects")
            print(message.content)
            for emote in server.emojis:
                if emote.id in [x["id"] for x in list(objects["emotes"].values())]:
                    print(emote.name)
                    await bot.add_reaction(message, emote)
        return
    if message.channel.is_private: #Do private channel things
        print("Message in private channel")
        return
    if message.channel.id == objects["channels"]["suggestions"]:
        print("Suggestion message")
        await handle_suggestion(message)
    msg = message.content
    print(message.author.name+": "+msg)
    if msg.startswith("$"):
        await bot.process_commands(message)
        return
    await spam_filter(message)

@bot.command(pass_context=True)
#add a user through their origin account
async def add(ctx, originuser):
    userid = ctx.message.author.id
    users[get_fromid(users, "id", userid)]["origin"] = originuser
    await save_json(users, "users")
    await bot.say("Updated your origin username @"+ctx.message.author.name)
    stats = await get_stats(originuser)
    await update_stats(userid, stats)

async def update_stats(userid, stats):
    for k in list(stats.keys()):
        users[get_fromid(users, "id", userid)][k] = stats[k]

@bot.command()
@commands.check(checks.is_admin) #Only admins can use this command
# Get top suggestions
async def getsuggestions():
    channel = bot.get_channel(objects["channels"]["suggestions"])
    #Go through suggestions and sort

@bot.command()
#$ping - sends pong
async def ping():
    await bot.say("Whoever threw that, your mums a hoe ")

async def get_stats(user):
    r=requests.get("https://public-api.tracker.gg/apex/v1/standard/profile/5/"+user, headers={"TRN-Api-Key": "62979e1c-f8bd-4fe9-a07e-ea9213155850"})
    try:
        data = r.json()["data"]
    except KeyError:
        await bot.say("Error, try again, perhaps you failed to enter your OWN USERNAME properly, hmmm?")
        return
    stats = data["stats"]
    stat = dict()
    stat["level"] = str(stats[0]["displayValue"])
    stat["kills"] = str(stats[1]["displayValue"])
    stat["damage"] = str(stats[2]["displayValue"])
    stat["thumbnail"] = data["children"][0]["metadata"]["icon"]
    stat["main"] = data["children"][0]["metadata"]["legend_name"]
    return stat

@bot.command(pass_context=True)
#Stats request
async def stats(ctx):
    user = users[get_fromid(users, "id", ctx.message.author.id)]
    if user["origin"] == "":
        await bot.say("You have to add your origin tag first - that's not very cash money of you")
        
    print("Getting stats for "+user["origin"])

    # stat = await get_stats(user)
    # await update_stats(ctx.message.author.id, stat)

    embed=discord.Embed(title=user["nick"]+"'s Level of Dankness", url="https://apex.tracker.gg/profile/pc/"+user["origin"], description="<Server Rank>", color=0xFA0A05)
    embed.set_author(name=user["nick"])
    embed.set_thumbnail(url=user["thumbnail"])
    embed.add_field(name="Level", value=user["level"], inline=False)
    embed.add_field(name="Damage", value=user["damage"], inline=False)
    embed.add_field(name="Kills", value=user["kills"], inline=False)
    embed.add_field(name="Last Played", value=user["main"], inline=False)
    embed.set_footer(text="That's a lot of damage")
    await bot.say(embed=embed)
    

if __name__ == "__main__":
    start()
    