from discord.ext import commands
import json

with open('objects.json') as json_data_file:
    objects = json.load(json_data_file)

def is_admin(ctx):
    return objects["roles"]["admin"] in [x.id for x in ctx.message.author.roles]
