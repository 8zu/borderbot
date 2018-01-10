import asyncio
import logging
import os.path as osp
import sys

import pytoml

import border as borderutil
from border_bot import BorderBot

try:
    from discord.ext import commands
    import discord
except ImportError:
    print("Discord.py is not installed.\n"
          "Consult the guide for your operating system "
          "and do ALL the steps in order.\n"
          "https://twentysix26.github.io/Red-Docs/\n")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger = logging.getLogger('borderbot')
logger.addHandler(handler)

description = """This is a bot to record and post to registered channel latest border of MLTD"""
config_path = "./config.toml"
text_path = './translation.toml'


def get_config(path):
    if osp.exists(path):
        return pytoml.load(open(path, "r", encoding="UTF-8"))
    else:
        logger.error("Missing config file! Shutting down now...")
        sys.exit(1)


class Fetcher(object):
    def __init__(self, bot, delay=5, retry=30):
        self.bot = bot
        self.delay = self._parse_delay(delay)

        async def task():
            delta = self._till_next_time(minimum=10)
            print(f'Next update is scheduled in {delta} seconds.')
            await asyncio.sleep(delta)
            try:
                ev = borderutil.get_latest_event_metadata()
                if not ev.is_active:
                    print(f'Event {ev.id} is not active at this point.')
                elif not ev.has_border:
                    print("The active event doesn't have borde")
                else:
                    bd = ev.fetch_border()
                    await self.bot.update(bd)
                    print('Update succeeds!')
            except IOError as ex:
                print('Connection error: ' + str(ex) + f'. Retry in {retry} seconds.')
                await asyncio.sleep(retry)
            asyncio.ensure_future(task())

        asyncio.ensure_future(task())

    def _till_next_time(self, minimum=0):
        now = borderutil.get_japan_time()
        s = (now.minute % 30) * 60 + now.second
        return max(1800 - s + self.delay, minimum)

    @staticmethod
    def _parse_delay(delay):
        if type(delay) is int:
            return delay
        if type(delay) is str:
            ms = delay.split('m')
            if len(ms) == 2:
                return int(ms[0]) * 60 + int(ms[1])
            elif len(ms) == 1:
                return int(ms[0])
        logger.error("Delay is not in the right format, using a default of 10 seconds")
        return 10


def initialize(config):
    bot = BorderBot(config['cache_root'])
    _ = Fetcher(bot, config['delay'])
    texts = get_config(text_path)['jpn']

    @bot.event
    async def on_ready():
        servers = len(bot.servers)
        channels = sum(1 for _ in bot.get_all_channels())
        registered = len(bot.channels)

        print('--------------')
        print('| Border bot |')
        print('--------------')
        print('Logged in as')
        print(bot.user.name)
        print(bot.user.id)
        print(f'to {servers} servers, {channels} channels')
        print(f'registered to post in {registered} channels')
        print()

        await bot.broadcast(texts['greet'].format(bot.user.name))

    @bot.command()
    async def add_channel(channel: discord.Channel):
        logger.info(f'Registering channel {channel.name}...')
        if bot.add_channel(channel.id):
            logger.info(f'Registered channel {channel.name} to list.')
            await bot.send_message(bot.get_channel(channel.id), texts["greet"].format(bot.user.name))
        else:
            logger.info('Channel already registered. Ignored.')

    @bot.command()
    async def remove_channel(channel: discord.Channel):
        logger.info(f'Unregistered channel {channel.name}...')
        bot.remove_channel(channel.id)
        await bot.send_message(bot.get_channel(channel.id), texts["bye"])

    @bot.command()
    async def border():
        try:
            bd = bot.get_latest_border().get()
        except ValueError:
            await bot.say(texts['cache_miss'])
            return
        prev = bot.get_prev_border().val
        await bot.say(borderutil.format_with(bd, prev))

    @bot.command()
    async def past_border(event_code):
        try:
            bd = bot.get_past_border(event_code)
            await bot.say(borderutil.format_with(bd, None))
        except IOError:
            await bot.say(texts['no_border'])

    @bot.command(pass_context=True)
    async def purge(context):
        channel = context.message.channel
        await bot.purge(channel)
        logger.info(f'Deleted {len(deleted)} message(s) from channel {channel.name}')

    return bot


if __name__ == '__main__':
    config = get_config(config_path)
    border_bot = initialize(config)
    border_bot.run(config['token'])
