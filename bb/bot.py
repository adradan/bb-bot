import discord
from discord.ext import commands, tasks
from .config import Config
import json
import aiohttp
import requests
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime
import os


class Botbroker(commands.Cog):
    def __init__(self, discBot):
        self.bot = discBot
        with open('bb/bots.json', 'r') as f:
            data = f.read()
        self.bot_list = json.loads(data)

    @commands.command(name='bb', brief='Searches botbroker for bot prices')
    async def _bb(self, ctx: commands.Context, arg):
        bot_info = await self.get_bot(arg)
        if not bot_info:
            return
        elif (bot_info['name']) and (not bot_info['id']):
            await ctx.send(f'Botbroker is currently doing maintenance on {bot_info["name"]}. Check back later.')
            return
        bot_id = bot_info['id']
        lt_year = await self.get_data(bot_id, 'lifetime', '365')
        lt_week = await self.get_data(bot_id, 'lifetime', '7')
        lt_day = await self.get_data(bot_id, 'lifetime', '1')
        r_year = await self.get_data(bot_id, 'renewal', '365')
        r_week = await self.get_data(bot_id, 'renewal', '7')
        r_day = await self.get_data(bot_id, 'renewal', '1')
        avg = {
            "Lifetime": {
                'Yearly': lt_year,
                'Weekly': lt_week,
                'Daily': lt_day
            },
            "Renewal": {
                'Yearly': r_year,
                'Weekly': r_week,
                'Daily': r_day
            }
        }
        for key, value in avg['Lifetime'].items():
            avg['Lifetime'][key] = await self.get_avg(value)
        for key, value in avg['Renewal'].items():
            avg['Renewal'][key] = await self.get_avg(value)
        lt_year.sort(key=lambda price: price[0])
        r_year.sort(key=lambda price: price[0])
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
        plt.savefig(f'{bot_id}.png', transparent=True)
        embed = discord.Embed(title=f'{bot_info["name"]} Botbroker Prices', colour=0xe74c3c)
        lt = avg['Lifetime']
        r = avg['Renewal']
        for membership in avg:
            for key in avg[membership]:
                embed.add_field(name=f'{membership} {key} Average', value=f'${avg[membership][key]}', inline=True)
        file = discord.File(os.path.abspath(f'{bot_id}.png'), filename='image.png')
        embed.set_image(url='attachment://image.png')
        embed.set_footer(text='Botbroker.io Price Checker | Made by @H3yB4ws#0001')
        await ctx.send(file=file, embed=embed)
        os.remove(os.path.abspath(f'{bot_id}.png'))
        plt.close()

    async def get_bot(self, arg):
        for key in self.bot_list:
            if key == arg.lower():
                return self.bot_list[key]
        return False

    async def get_data(self, bot_id: str, membership: str, interval: str):
        url = f'https://www.botbroker.io/bots/{bot_id}/chart?key_type={membership}&days={interval}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
        return data

    async def get_avg(self, data):
        total = 0
        if not data:
            return 0
        for sale in data:
            total += int(sale[1])
        return round(total / len(data), 2)


intents = discord.Intents.all()
bot = commands.Bot(command_prefix='', case_insensitive=False, description='Botbroker Prices', intents=intents)
bot.add_cog(Botbroker(bot))


@bot.event
async def on_ready():
    print(f'Logged in as: {bot.user}')


bot.run(Config.TOKEN)
