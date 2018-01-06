import asyncio
import logging
import sys
import os.path as osp
import pytoml
import border as borderutil
from datetime import timedelta
import threading, time
from cache import Cache

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
        return pytoml.load(open(path))
    else:
        logger.error("Missing config file! Shutting down now...")
        sys.exit(1)

class Fetcher(object):
    def __init__(self, delay=5, retry=30):
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
                    print('Update succeeds!')
                    await bot.update(bd)
                    bot.cache.save('border.json', borderutil.serialize(bd))
            except IOError as ex:
                print('Connection error: ' + str(ex) + f'. Retry in {retry} seconds.')
                await asyncio.sleep(retry)
            asyncio.ensure_future(task())

        asyncio.ensure_future(task())


    def _till_next_time(self, minimum=0):
        now = borderutil.get_japan_time()
        s = (now.minute % 30) * 60 + now.second
        return max(1800 - s + self.delay, minimum)

    def _parse_delay(self, delay):
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

class BorderBot(commands.Bot):
    def __init__(self):
        self.cache = Cache()
        self.channels = set(self.cache.load("channels.json").get_or([]))
        super().__init__(description=description, command_prefix="!")

    async def broadcast(self, msg: str):
        for _id in self.channels:
            await self.send_message(self.get_channel(_id), msg)

    def get_latest_border(self):
        return self.cache.load('border.json').get()

    def add_channel(self, chan: int) -> bool:
        if chan not in self.channels:
            self.channels.add(chan)
            self.cache.save('channels.json', list(self.channels))
            return True
        else:
            return False

    def remove_channel(self, chan: int):
        if chan in self.channels:
            self.channels.remove(chan)
            self.cache.save('channels.json', list(self.channels))

    async def purge(self, chan: discord.Channel) -> int:
        if chan.id in self.channels:
            is_me = lambda m: m.author == self.user
            deleted = await self.purge_from(chan, limit=100, check=is_me)
            return deleted
        else:
            return 0

    async def update(self, bd):
        await self.broadcast(borderutil.format(bd))


def initialize():
    bot = BorderBot()
    texts = get_config(text_path)['test']

    @bot.event
    async def on_ready():
        servers = len(bot.servers)
        channels = sum(1 for c in bot.get_all_channels())
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

        await bot.broadcast(texts['recover'])

    @bot.command()
    async def add_channel(chan: discord.Channel):
        logger.info(f'Registering channel {chan.name}...')
        if bot.add_channel(chan.id):
            logger.info(f'Registered channel {chan.name} to list.')
            await bot.send_message(bot.get_channel(chan.id), texts["greet"].format(bot.user.name))
        else:
            logger.info('Channel already registered. Ignored.')

    @bot.command()
    async def remove_channel(chan: discord.Channel):
        logger.info(f'Unregistering channel {chan.name}...')
        bot.remove_channel(chan.id)
        await bot.send_message(bot.get_channel(chan.id), texts["bye"])

    @bot.command()
    async def border():
         try:
             bd = bot.get_latest_border()
         except:
             await bot.say(texts['cache_miss'])
             return
         await bot.say(borderutil.format(bd))

    @bot.command(pass_context=True)
    async def purge(ctx):
        chan = ctx.message.channel
        await bot.purge(chan)
        logger.info(f'Deleted {len(deleted)} message(s) from channel {chan.name}')

    return bot


if __name__ == '__main__':
    config = get_config(config_path)
    fetcher = Fetcher(config['delay'])
    bot = initialize()
    bot.run(config['token'])
