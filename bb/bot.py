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

bot = commands.Bot(command_prefix='bb')
bot.remove_command('help')


class BotBroker(commands.Cog):
    def __init__(self, disc_bot):
        self.bot = disc_bot
        with open('bb/bots.json', 'r') as f:
            data = f.read()
        self.bot_list = json.loads(data)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        if not message.content.startswith('bb ') and len(message.content.split(' ')) == 1:
            return
        bot_info = message.content.split(' ')[1]
        bot_info = await self.get_bot(bot_info)
        if not bot_info:
            return
        elif (bot_info['name']) and (not bot_info['id']):
            await message.channel.send(f'Botbroker is currently doing maintenance on {bot_info["name"]}. Check back later.')
            return
        elif bot_info['name'] == 'Help':
            await self.help(message)
        bot_id = bot_info['id']
        lt_year = await self.get_data(bot_id, 'lifetime', '365')
        lt_week = await self.get_data(bot_id, 'lifetime', '7')
        lt_day = await self.get_data(bot_id, 'lifetime', '1')
        r_year = await self.get_data(bot_id, 'renewal', '365')
        r_week = await self.get_data(bot_id, 'renewal', '7')
        r_day = await self.get_data(bot_id, 'renewal', '1')
        avg = await self.set_avg_dict([lt_year, r_year], [lt_week, r_week], [lt_day, r_day])
        avg = await self.iterate_avg(avg)
        lt_year.sort(key=lambda price: price[0])
        r_year.sort(key=lambda price: price[0])
        graph = await self.create_graph(lt_year, r_year, bot_info)
        graph.savefig(f'{bot_id}.png', transparent=True)
        embed, file = await self.create_embed(avg, bot_info)
        await message.channel.send(file=file, embed=embed)
        os.remove(os.path.abspath(f'{bot_id}.png'))
        graph.close()

    async def set_avg_dict(self, year, week, day):
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
        return avg

    async def iterate_avg(self, avg):
        new_avg = {'Lifetime': {}, 'Renewal': {}}
        for key, value in avg['Lifetime'].items():
            new_avg['Lifetime'][key] = await self.get_avg(value)
        for key, value in avg['Renewal'].items():
            new_avg['Renewal'][key] = await self.get_avg(value)
        return new_avg

    async def help(self, message):
        bot_json = self.bot_list.keys()
        bot_names = 'Cyber, Polaris, Nebula, Mekaio, Balko, Dashe, Wrath, Splashforce, Tohru, PD, Prism, Mekpreme, Swftaio, Velox, Adept, Scottbot, SoleAIO, Phantom'
        await message.channel.send("```Bot Broker Sales Activity\n\nUsage:\nbb bot_name\n\nSupported Bots:\n" + bot_names + "```")

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

    async def create_graph(self, lt_year, r_year, bot_info):
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

    async def create_embed(self, avg, bot_info):
        bot_id = bot_info['id']
        embed = discord.Embed(title=f'{bot_info["name"]} Botbroker Prices', colour=0xe74c3c)
        lt = avg['Lifetime']
        r = avg['Renewal']
        for membership in avg:
            for key in avg[membership]:
                embed.add_field(name=f'{membership} {key} Average', value=f'${avg[membership][key]}', inline=True)
        file = discord.File(os.path.abspath(f'{bot_id}.png'), filename='image.png')
        embed.set_image(url='attachment://image.png')
        embed.set_footer(text='Botbroker.io Price Checker | Made by @H3yB4ws#0001')
        return embed, file


bot.add_cog(BotBroker(bot))


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

bot.run(Config.TOKEN)
