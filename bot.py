import discord

from discord.ext import commands
from discord import Color

from dotenv import dotenv_values

import argparse

import json
import time
import random

import re

import sqlite3

import logging
#import logging.handlers
#https://docs.python.org/3/library/logging.handlers.html#logging.handlers.RotatingFileHandler


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(name)-16s] [%(levelname)-8s] %(module)s.%(funcName)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', handlers=[logging.StreamHandler(), logging.FileHandler("./bot-log.log")])
logger = logging.getLogger()
dmlogger = logging.getLogger('DirectMessage')

version = 'v0.0.1-beta'

cliParser = argparse.ArgumentParser(prog='compleat_bot', description='JumpStart Compleat Bot', epilog='', add_help=False)
cliParser.add_argument('-e', '--env', choices=['DEV', 'PROD'], default='DEV', action='store')
cliParser.add_argument('-d', '--debug', default=False, action='store_true')
cliArgs = cliParser.parse_args()

if cliArgs.debug:
    logger.setLevel(Logging.DEBUG)
    dmlogger.setLevel(Logging.DEBUG)
    scCacheLogger.setLevel(Logging.DEBUG)
    logger.debug("DEBUG TURNED ON")
    
dev_env = dotenv_values(".devenv")
prod_env = dotenv_values(".prodenv")

bot_env = dev_env
if('PROD' == cliArgs.env.upper()):
    bot_env = prod_env
    logger.info(f'THIS IS RUNNING IN PRODUCTION MODE AND WILL CONNECT TO PRODUCTION BOT TO THE MAIN JUMPSTART DISCORD SERVER')
else:
    logger.info(f'This is running DEVELOPMENT MODE and the DEVELOPMENT bot will connect to your test server')

intents = discord.Intents.default()
intents.message_content = True

#bot = discord.bot(intents=intents)
bot = commands.Bot(command_prefix=['!'], intents=intents) #command_prefix can be one item - i.e. '!' or a list - i.e. ['!','#','$']

# \[\[([^[][^\]]*)\]\]
# \[\[([^\[\]]+)\]\]
card_fetch_pattern = re.compile("\[\[([^\[\]]+)\]\]", re.IGNORECASE | re.MULTILINE)
card_fetch_pattern_2 = re.compile("!(.+?)!", re.IGNORECASE | re.MULTILINE)

db_con = None
db_cur = None

@bot.event
async def on_ready():
    #print(f'{jsd.jumpstart}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="With these cards I'm never alone!")) #Getting in to it!
    logger.info(f'We have logged in as {bot.user} with status {bot.status}')

    logger.info(f'Loading Database.....')    
    global db_con
    db_con = sqlite3.connect("divorced-dads.db")
    global db_cur 
    db_cur = db_con.cursor()
    logger.info(f'Database Loaded!')

#using @bot.listen() will listen for messages, but will continue processing commands, so having the await bot.process_commands(message) when this is set with @bot.listen() decorator it will fire the command twice.
@bot.event  
async def on_message(message):

    #print(f'{message.created_at}, Guild: {message.guild}, Channel: {message.channel}, Author: {message.author}, Message: {message.content}')
    #print(f'{bot.activity}')

    if message.author == bot.user: #avoid infinite loops
        return
    if isinstance(message.channel, discord.DMChannel):
        dmlogger.info(f'{message.created_at}, Channel: {message.channel}, Author: {message.author}, Message: {message.content}')
        return

    if message.channel.name != 'bot-testing': #only allow processing of messages in the bot-testing channel
        return

    #Fix "auto-completed" en and em dashes
    message.content = message.content.replace('\u2013', '--')
    message.content = message.content.replace('\u2014', '--')
    #Fix fancy single quotes
    message.content = message.content.replace('\u2018', '\'')
    message.content = message.content.replace('\u2019', '\'')
    #Fix fancy double quotes
    message.content = message.content.replace('\u201C', '"')
    message.content = message.content.replace('\u201D', '"')

    #await message.channel.send(f"Got {message.content}")

    cards_to_search = card_fetch_pattern.findall(message.content)
    #append card_fetch_pattern2.findall(message.content)
    if cards_to_search:
        counter = 0
        #await message.channel.send(f"You want me to look up {len(cards_to_search)} cards?")
        for card_to_search in cards_to_search:
            counter = counter + 1
            if counter > 3:
                await message.channel.send(f"You asked for too many cards at once!  Stopping!")
                break
            #await message.channel.send(f"Searching up {card_to_search}")
            startTime = time.time()
            the_card_found = False
            the_card_color = Color.magenta()

            logger.info(f"Searching for Card: {card_to_search}")

            results = db_cur.execute("SELECT * FROM cards LEFT OUTER JOIN card_types on cards.card_type_id = card_types.card_type_id LEFT OUTER JOIN beast_types on cards.beast_type_id = beast_types.beast_type_id LEFT OUTER JOIN sets on cards.set_id = sets.set_id where card_name = ? COLLATE NOCASE", [card_to_search])
            the_results = results.fetchall()

            the_card_found = len(the_results) > 0

            if the_card_found:
                logger.info(f"Search Results:  {the_results}")

                the_card_number = the_results[0][1]
                the_card_name = the_results[0][2]

                the_card_type = the_results[0][11]
                the_card_beast_type = the_results[0][13]

                the_card_attack_value = the_results[0][5]
                the_card_defense_value = the_results[0][6]

                the_card_description = the_results[0][7]

                the_card_special_attributes = the_results[0][8]
                
                the_card_set = the_results[0][15]
                the_set_total_cards = the_results[0][16]

                if the_card_type == "Tool":
                    the_card_color = Color.red()
                elif the_card_type == "Terrain":
                    the_card_color = Color.gold()
                elif the_card_type == "Beast":
                    if the_card_beast_type == "Wood":
                        the_card_color = Color.green()
                    elif the_card_beast_type == "Leather": 
                        the_card_color = Color.dark_orange()                   
                    elif the_card_beast_type == "Concrete":
                        the_card_color = Color.light_grey()
                    elif the_card_beast_type == "Steel":
                        the_card_color = Color.blue()
                    
                endTime = time.time()
                embed = discord.Embed(title=f"{the_card_name} ({the_card_number}/{the_set_total_cards})", color=the_card_color) #can also have url, description, color
                #embed.set_author(name=the_card_name)#, icon_url=the_set_icon_url) #icon_url is actually a url
                #embed.set_thumbnail(url=the_card_imate_url)
                embed.add_field(name="Card Type", value=the_card_type, inline=(the_card_type == "Beast"))
                if(the_card_type == "Beast"):
                    embed.add_field(name="Beast Type", value=the_card_beast_type, inline=True)
                    embed.add_field(name="Attack | Defense", value=f"{the_card_attack_value} | {the_card_defense_value}", inline=False)

                embed.add_field(name="Description", value=the_card_description, inline=False)
                embed.add_field(name="Special Attributes", value=the_card_special_attributes, inline=False)

                embed.add_field(name="Set", value=the_card_set, inline=False)
                embed.set_footer(text=f'Card Search took {endTime - startTime:.5f}s')
                await message.channel.send(embed=embed)
            else:
                logger.info(f"No results for Card Search: {card_to_search}")
                await message.channel.send(f"No card found by the name of '{card_to_search}'")

    #else:
        #await message.channel.send(f"No cards to search here....")

    await bot.process_commands(message) #this will continue processing to allow commands to fire.

@bot.command()
async def quote(ctx):
    quotes = ["Now that we're into it, let's get into it!",
              "Let's get into it!",
              "With these cards, you are never alone!",
              "So choose wisely!",
              "Be sure to follow along at home.",
              "The world is constantly changing.",
              "Have you ever found yourself in this dangerous situation?",
              "And remember to be a top Divorced Dads player you must always be thinking of a BBC.  Bigger Better Combos."]
    await ctx.send(content=f"{random.choice(quotes)}", suppress_embeds=True)
    
@bot.command(aliases=['information', 'fancontent', 'fancontentpolicy', 'license'])
async def info(ctx):
    await ctx.send(content=f"Divocred Dads Card Bot {version}\n\nThis Discord Bot is unofficial Fan Content. Not approved/endorsed by Divorced Dads. Portions of the materials used are property of Divocred Dads. ©Divorced Dads.\n\nSource Code is released under the MIT License https://github.com/tyraziel/Divorced-Dads-Discord-Bot/ -- 2024\n\nWith this bot, we are never alone!", suppress_embeds=True)

bot.run(bot_env['BOT_TOKEN'])