
import discord
from discord.ext import commands
import requests
import asyncio
import json

config = json.load(open("config.json"))
users = json.load(open("users.json"))
bot = commands.Bot(command_prefix=config["prefix"], description=config["description"])
server = None
playing = "with {} users"

async def spam_filter(message):
    words = open("banned", "r")
    for word in words:
        if word in message.content:
            await bot.send_message(message.channel, "That is a banned word, please be kind, like Shaggy. Shaggy only uses 0.003\% of his power to be kind")
            await bot.http.delete_message(message.channel.id, message.id)

def start():
    bot.run(open("token").read())

async def background_loop():
    global playing
    await bot.wait_until_ready()
    while not bot.is_closed:
        await bot.change_presence(game=discord.Game(name=playing
        .format(sum([mem.status==discord.Status.online for mem in server.members]))))
        await asyncio.sleep(1)

@bot.event
async def on_ready():
    global server
    print("Logged in as", bot.user.name)
    server = list(bot.servers)[0]
    bot.loop.create_task(background_loop())
    #await bot.change_presence(game=discord.Game(name="with the mortals"))

@bot.event
async def on_reaction_add(reaction, user):
    emote = reaction.emoji
    message = reaction.message
    if emote is discord.Emoji:
        emote = emote.name
    print(emote)
    if "<:" in emote: #message.id == "<mid>" and
        print("Relevant emote used")
        emote = emote[emote.index(":"):]
        await bot.add_roles(user, discord.utils.get(server.roles, name=emote[:emote.index(":")]))

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.is_private: #Do private channel things
        return
    msg = message.content
    print(message.author.name+": "+msg)
    if msg.startswith("$"):
        await bot.process_commands(message)
        return
    await spam_filter(message)

@bot.command(pass_context=True)
#add a user through their origin account
async def add(ctx, originuser):
    print(users)
    userid = ctx.message.author.id
    found = False
    for i, uid in enumerate([x["user"] for x in users]):
        if uid == userid:
            found = True
            users[i]["origin"] = originuser
    if not found:
        users.append({"user": userid, "origin": originuser})
    f = open("users.json", "w")
    json.dump(users, f, indent=4)
    f.close()
    await bot.say("Updated "+originuser+" in the user list")
    

@bot.command()
#$help - sends help
async def test():
    await bot.say("Whoever threw that, your mums a hoe ")

@bot.command(pass_context=True)
#Stats request
async def stats(ctx):
    if str(ctx.message.author.id) not in [x["user"] for x in users]:
        await bot.say("You have to add your origin tag first - that's not very cash money of you")

    user = users[[x["user"] for x in users].index(ctx.message.author.id)]["origin"]
    print("Getting stats for "+user)
    
    r=requests.get("https://public-api.tracker.gg/apex/v1/standard/profile/5/"+user, headers={"TRN-Api-Key": "62979e1c-f8bd-4fe9-a07e-ea9213155850"})
    try:
        data = r.json()["data"]
    except KeyError:
        await bot.say("Error, try again, perhaps you failed to enter your OWN USERNAME properly, hmmm?")
        return
    stats = data["stats"]
    level = str(stats[0]["displayValue"])
    kills = str(stats[1]["displayValue"])
    damage = str(stats[2]["displayValue"])
    thumbnail = data["children"][0]["metadata"]["icon"]
    main = data["children"][0]["metadata"]["legend_name"]

    embed=discord.Embed(title=user+"'s Level of Dankness", url="https://apex.tracker.gg/profile/pc/"+user, description="<Server Rank>", color=0xFA0A05)
    embed.set_author(name=user)
    embed.set_thumbnail(url=thumbnail)
    embed.add_field(name="Level", value=level, inline=False)
    embed.add_field(name="Damage", value=damage, inline=False)
    embed.add_field(name="Kills", value=kills, inline=False)
    embed.add_field(name="Last Played", value=main, inline=False)
    embed.set_footer(text="That's a lot of damage")
    await bot.say(embed=embed)
    

if __name__ == "__main__":
    start()
    