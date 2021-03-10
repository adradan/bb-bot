import discord
from discord.ext import commands
from .config import Config
import json
import aiohttp
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime
import os
import asyncio
import random

#proxy_auth = aiohttp.BasicAuth('zoom8zdjq', 'uT6cMeEWUe')
client = discord.Client()
with open('bb/bots.json', 'r') as f:
    data = f.read()
bot_list = json.loads(data)


async def get_bot(name):
    for key in bot_list:
        if key == name.lower():
            return bot_list[key]
    return False


@client.event
async def on_ready():
    print('Logged in.')


@client.event
async def on_message(message):
    print(f'BB Bot: {message.content}')
    if (message.author == client.user) or (not (message.content.startswith('bb ')) or (len(message.content.split(' ')) != 2)):
        return
    bot_info = message.content.split(' ')[1]
    bot_info = await get_bot(bot_info)
    if not bot_info:
        return
    elif (bot_info['name']) and (not bot_info['id']):
        await message.channel.send(f'Botbroker is currently doing maintenance on {bot_info["name"]}. Check back later.')
        return
    elif bot_info['name'] == 'Help':
        await help(message)
        return
    bot_id = bot_info['id']
    file, embed, graph = await get_bot_info(bot_id, bot_info)
    await message.channel.send(file=file, embed=embed)
    os.remove(os.path.abspath(f'{bot_id}.png'))
    graph.close()


async def get_bot_info(bot_id, bot_info):
    async with aiohttp.ClientSession() as session:
        lt_year = await get_data(bot_id, 'lifetime', '365', session)
        lt_week = await get_data(bot_id, 'lifetime', '7', session)
        lt_day = await get_data(bot_id, 'lifetime', '1', session)
        r_year = await get_data(bot_id, 'renewal', '365', session)
        r_week = await get_data(bot_id, 'renewal', '7', session)
        r_day = await get_data(bot_id, 'renewal', '1', session)
    lt_year.sort(key=lambda price: price[0])
    r_year.sort(key=lambda price: price[0])
    avg_dict = await set_dict([lt_year, r_year], [lt_week, r_week], [lt_day, r_day])
    graph = await create_graph(lt_year, r_year, bot_info)
    graph.savefig(f'{bot_id}.png', transparent=True)
    embed, file = await create_embed(avg_dict, bot_info)
    return file, embed, graph


async def create_embed(avg, bot_info):
    bot_id = bot_info['id']
    embed = discord.Embed(title=f'{bot_info["name"]} Botbroker Prices', colour=0xe74c3c)
    lt = avg['Lifetime']
    r = avg['Renewal']
    for membership in avg:
        for key in avg[membership]:
            embed.add_field(name=f'{membership} {key} Average', value=f'${avg[membership][key]}', inline=True)
    file = discord.File(os.path.abspath(f'{bot_id}.png'), filename='image.png')
    embed.set_image(url='attachment://image.png')
    embed.set_footer(text='Botbroker.io Price Checker | House of Carts')
    return embed, file


async def create_graph(lt_year, r_year, bot_info):
    x_lt = np.array([datetime.strptime(sale[0], '%Y-%m-%dT%H:%M:%S.%fZ') for sale in lt_year])
    y_lt = np.array([sale[1] for sale in lt_year])
    x_r = np.array([datetime.strptime(sale[0], '%Y-%m-%dT%H:%M:%S.%fZ') for sale in r_year])
    y_r = np.array([sale[1] for sale in r_year])
    plt.plot(x_lt, y_lt, label='Lifetime')
    plt.plot(x_r, y_r, label='Renewal')
    plt.legend()
    ax = plt.subplot()
    for side in ax.spines.keys():
        ax.spines[side].set_color('white')
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    plt.title(bot_info['name'] + ' Prices', color='white')
    plt.gcf().autofmt_xdate()
    return plt


async def get_data(bot_id, membership, interval, session: aiohttp.ClientSession):
    proxy = Config.PROXIES[random.randrange(len(Config.PROXIES))].split(':')
    proxy = f'http://{proxy[2]}:{proxy[3]}@{proxy[0]}:{proxy[1]}'

    url = f'https://www.botbroker.io/bots/{bot_id}/chart?key_type={membership}&days={interval}'
    async with session.get(url, proxy=proxy) as resp:
        resp_data = await resp.json()
    return resp_data


async def set_dict(year, week, day):
    avg = {
        "Lifetime": {
            'Yearly': year[0],
            'Weekly': week[0],
            'Daily': day[0]
        },
        "Renewal": {
            'Yearly': year[1],
            'Weekly': week[1],
            'Daily': day[1]
        }
    }
    return await set_avg(avg)


async def set_avg(avg):
    new_avg = {'Lifetime': {}, 'Renewal': {}}
    for key, value in avg['Lifetime'].items():
        new_avg['Lifetime'][key] = await get_avg(value)
    for key, value in avg['Renewal'].items():
        new_avg['Renewal'][key] = await get_avg(value)
    return new_avg


async def get_avg(price_data):
    total = 0
    if not price_data:
        return 0
    for sale in price_data:
        total += int(sale[1])
    return round(total / len(price_data), 2)


async def help(message):
    bot_json = bot_list.keys()
    bot_names = 'Cyber, Polaris, Nebula, Mekaio, Balko, Dashe, Wrath, Splashforce, Tohru, PD, Prism, Mekpreme, Swftaio, Velox, Adept, Scottbot, Phantom, Dragon, Ganesh, Kage'
    await message.channel.send(
        "```Bot Broker Sales Activity\n\nUsage:\nbb bot_name\n\nSupported Bots:\n" + bot_names + "```")

client.run(Config.TOKEN)
