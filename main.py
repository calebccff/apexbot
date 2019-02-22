
import discord
from discord.ext import commands
import requests
import asyncio
import json
import checks
from utils import *

config = json.load(open("config.json"))
users = json.load(open("users.json"))
objects = json.load(open("objects.json"))
suggestions = json.load(open("suggestions.json"))
HELP_MSG = open("help.txt").read()
bot = commands.Bot(command_prefix=config["prefix"], description=config["description"],
    max_messages=10000)
bot.remove_command('help')
server = None
logchannel = None

@bot.event
async def on_ready():
    global server, logchannel
    print("Logged in as", bot.user.name)
    server = list(bot.servers)[0]
    logchannel = bot.get_channel(objects["channels"]["bot-log"])
    await get_messages()
    await users_update()
    bot.loop.create_task(users_loop())
    await bot.change_presence(game=discord.Game(name="with the mortals"))
    

async def spam_filter(message):
    words = open("banned", "r").readlines()
    for word in [w.strip() for w in words]:
        if word in message.content.lower():
            users[get_fromid(users, "id", message.author.id)]["strikes"] += 1
            await bot.send_message(message.channel, "Watch your profanity")
            await bot.http.delete_message(message.channel.id, message.id)
def start():
    bot.run(open("token").readlines()[0])

async def users_loop():
    while True:
        for mem in server.members:
            if (not mem.bot) and get_fromid(users, "id", mem.id) is not None and users[get_fromid(users, "id", mem.id)]["strikes"] > 3:
                users[get_fromid(users, "id", mem.id)]["strikes"] = 0
                print("Kicking user: "+mem.display_name)
                await bot.send_message(mem, "cowabunga it is")
                await bot.kick(mem)
                await log(users[get_fromid(users, "id", mem.id)]["nick"]+" has been kicked for toxic behaviour")
                return
        await save_json(users, "users") #ONLY time to save users, no need to do it multiple times
        await asyncio.sleep(1)

async def users_update():
    global users
    await bot.wait_until_ready()
    for mem in server.members:
        if mem.bot:
            continue
        if get_fromid(users, "id", mem.id) is not None:
            #print("Updating-"+str(n)+": "+mem.display_name)
            users[get_fromid(users, "id", mem.id)]["nick"] = mem.display_name
        else:
            users.append({"id": mem.id, "nick": mem.display_name, "origin": "", "strikes": 0, "stats": {}})
        #await asyncio.sleep(10)

async def handle_suggestion(message):
    await bot.add_reaction(message, "\u2B06")
    await bot.add_reaction(message, "\u2B07")
    suggestions.append({"id": message.id, "uid": message.author.id, "text": message.content, "up": 0, "down": 0})
    print(suggestions)
    await save_json(suggestions, "suggestions")

async def get_messages():
    mid = objects["messages"]["rolepick"]
    deleted = False
    for sid in [x["id"] for x in suggestions]:
        try:
            message = await bot.get_message(server.get_channel(objects["channels"]["suggestions"]), sid)
            bot.messages.append(message)
            print("Found suggestion: "+suggestions[get_fromid(suggestions, "id", sid)]["text"])
        except discord.errors.NotFound:
            print("Suggestion gone")
            del suggestions[get_fromid(suggestions, "id", sid)] #That suggestion is gone or too old
    await save_json(suggestions, "suggestions")
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
            await log("Asiigning role "+emote.name+" to "+user.display_name)
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
    if get_fromid(suggestions, "id", message.id) is not None: #Reaction to suggestion
        if emote == "\u2B06":
            suggestions[get_fromid(suggestions, "id", message.id)]["up"] -= 1
        elif emote == "\u2B07":
            suggestions[get_fromid(suggestions, "id", message.id)]["down"] -= 1
        else:
            await bot.remove_reaction(message, emote, user)
        await save_json(suggestions, "suggestions")
        return
    if type(emote) is discord.Emoji and message.id == objects["messages"]["rolepick"]:
        await log("Removing role "+emote.name+" from "+user.display_name)
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
    # if message.channel.is_private: #Do private channel things
    #     print("Message in private channel")
    #     return
    if message.channel.id == objects["channels"]["suggestions"]:
        print("Suggestion message")
        await handle_suggestion(message)
    msg = message.content
    print(message.author.name+": "+msg)
    if msg.startswith("$"):
        await bot.process_commands(message)
        return # Don't run spam filter on commands
    await spam_filter(message)

@bot.command(pass_context=True)
#add a user through their origin account
async def link(ctx, originuser):
    userid = ctx.message.author.id
    users[get_fromid(users, "id", userid)]["origin"] = originuser
    await bot.say("Updated your origin username "+ctx.message.author.name)
    stats = await get_stats(originuser)
    await update_stats(userid, stats)

async def get_stats(user):
    r=requests.get("https://public-api.tracker.gg/apex/v1/standard/profile/5/"+user, headers={"TRN-Api-Key": "62979e1c-f8bd-4fe9-a07e-ea9213155850"})
    try:
        data = r.json()["data"]
        print("Got data")
    except KeyError:
        await bot.say("Error, try again, perhaps you failed to enter your OWN USERNAME properly, hmmm?")
        return
    stats = data["stats"]
    stat = dict()
    stat["level"] = str(stats[0]["displayValue"])
    stat["kills"] = stats[1]["displayValue"]
    stat["legends"] = []
    for legend in data["children"]:
        stat["legends"].append({
            "name": legend["metadata"]["legend_name"],
            "thumbnail": legend["metadata"]["icon"],
            "stats": []})
        for st in legend["stats"]:
            stat["legends"][-1]["stats"].append({
                "name": st["metadata"]["name"],
                "value": st["displayValue"],
                "rank": st["displayRank"]
            })
    return stat

async def update_stats(userid, stats):
    users[get_fromid(users, "id", userid)]["stats"] = stats

@bot.command()
@commands.check(checks.is_admin) #If user had mod roles
# Get top suggestions
async def getsuggestions():
    channel = bot.get_channel(objects["channels"]["suggestions"])
    ordered = sorted(suggestions, key=lambda x: x["up"]-x["down"])
    embed=discord.Embed(title="Top Suggestions", description="", color=0xFAFA05)
    embed.set_author(name="Odin")
    for sug in ordered:
        embed.add_field(name=users[get_fromid(users, "id", sug["uid"])],
        value=sug["text"]+" | "+str(sug["up"])+" | "+str(sug["down"]), inline=False)
    await bot.say(embed=embed)
    #do embed things
    #Go through suggestions and sort

@bot.command(pass_context=True)
async def add(ctx, arg):
    print(arg)
    await bot.send_typing(ctx.message.channel)
    user = users[get_fromid(users, "id", arg[2:-1])]
    if user is None or user["origin"] == "":
        await bot.say("Unfortunately, "+uname["nick"]+" hasn't added their origin account yet, go tell them off")
        return
    await bot.say("Make sure you're signed in to the Origin website...\nhttps://www.origin.com/gbr/en-us/search?searchString="+user["origin"])
        

@bot.command()
#$ping - sends pong
async def ping():
    await bot.say("Whoever threw that, your mum's a hoe")

@bot.command()
@commands.check(checks.is_admin) #If user had mod roles
async def setprop(user, prop, value):
    users[get_fromid(users, "id", user[2:-1])][prop] = int(value)

@bot.command()
@commands.check(checks.is_admin) #If user had mod roles
async def getprop(user, prop):
    await bot.say(users[get_fromid(users, "id", user[2:-1])][prop])

@bot.command(pass_context=True)
@commands.check(checks.is_admin)
async def banword(ctx, word):
    f = open("banned", "a")
    f.write("\n"+word)
    f.close()
    await bot.http.delete_message(ctx.message.channel.id, ctx.message.id)
    await bot.say("Banned the word")

@bot.command(pass_context=True)
@commands.check(checks.is_admin)
async def unbanword(ctx, word):
    banned = open("banned").readlines()
    del banned[banned.index(word)] #Might error, this is safe as it won't overwrite the file
    f = open("banned", "w")
    f.write("".join(banned))
    f.close()
    await bot.http.delete_message(ctx.message.channel.id, ctx.message.id)
    await bot.say("Unbanned the word")

@bot.command(pass_context=True)
@commands.check(checks.is_admin)
async def purge(ctx, num):
    await bot.purge_from(ctx.message.channel, limit=int(num)+1) #Count for the purge message

@bot.command(pass_context=True)
#Stats request
async def stats(ctx):
    user = users[get_fromid(users, "id", ctx.message.author.id)]
    await bot.send_typing(ctx.message.channel)
    if user is None or user["origin"] == "":
        await bot.say("You have to add your origin tag first - that's not very cash money of you")
        return
        
    await log("Getting stats for "+user["nick"])
    stats = user["stats"]

    stat = await get_stats(user["origin"])
    await update_stats(ctx.message.author.id, stat)

    embed=discord.Embed(title=user["nick"]+"'s Power Level", url="https://apex.tracker.gg/profile/pc/"+user["origin"], description="<Server Rank>", color=0xFA0A05)
    embed.set_author(name=user["nick"])
    embed.add_field(name="Level", value=stats["level"], inline=True)
    embed.add_field(name="Kills", value=stats["kills"], inline=True)
    await bot.say(embed=embed)

    embed = discord.Embed(color=0xFA0A05)
    for legend in stats["legends"]:
        await bot.send_typing(ctx.message.channel)
        await asyncio.sleep(0.5) #Prevent rate limit
        embed.set_thumbnail(url=legend["thumbnail"])
        embed.add_field(name="Name", value=legend["name"], inline=True)
        for st in legend["stats"]:
            embed.add_field(name=st["name"], value=st["value"], inline=True)
        await bot.say(embed=embed)
        embed = discord.Embed(color=0xFA0A05)
    await bot.say("```cpp\nThat's a lot of damage```")
    

@bot.command(pass_context=True)
async def help(ctx):
    await bot.send_message(ctx.message.author, HELP_MSG)

async def log(msg):
    print(msg)
    await bot.send_message(logchannel, msg)

if __name__ == "__main__":
    start()
    