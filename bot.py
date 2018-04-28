import asyncio
import logging
import os.path as osp
import sys

import border as borderutil
from cache import Cache
from channel_registry import ChannelRegistry

try:
    import pytoml
    from discord.ext import commands
    import discord
except ImportError:
    print("Some modules are not installed. Please do:")
    print("\tpip install -r requirements.txt")
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
    def __init__(self, bot, secret_token, delay=5, retry=30):
        self.bot = bot
        self.api_token = secret_token
        if not secret_token:
            logger.error("API token is not filled in! Shutting down now...")
            sys.exit(1)
        self.delay = self._parse_delay(delay)

        async def task():
            delta = self._till_next_time(minimum=10)
            logger.info(f'Next update is scheduled in {delta} seconds.')
            await asyncio.sleep(delta)
            try:
                ev = borderutil.get_event_metadata()
                if not ev.is_active:
                    logger.info(f'Event {ev.id} is not active at this point.')
                elif not ev.has_border:
                    logger.info("The active event doesn't have border")
                else:
                    bd = ev.fetch_border(self.secret_token)
                    await self.bot.update(bd)
                    logger.info('Update succeeds!')
            except IOError as ex:
                logger.error('Connection error: ' + str(ex) + f'. Retry in {retry} seconds.')
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


class BorderBot(commands.Bot):
    def __init__(self, cache_root, secret_token):
        self.cache = Cache(cache_root)
        self.secret_token = secret_token
        self.channels = ChannelRegistry(self.cache.load("channels.json").get_or([]))
        super().__init__(description=description, command_prefix="!")

    async def greet_and_prune(self, msg: str):
        to_be_removed = set()
        for cinfo in self.channels:
            _id = cinfo[0]
            ch = self.get_channel(_id)
            if ch:
                try:
                    await self.send_message(ch, msg)
                except Exception as ex:
                    logger.error(f"Channel #{cinfo[2]} on server {cinfo[1]} causes exception:")
                    logger.error(ex)
                    logger.error('...Now will be removed')
                    to_be_removed.add(_id)
            else:
                logger.error(f"Channel #{cinfo[2]} on server {cinfo[1]} does not exist")
                logger.error('...Now will be pruned')
                to_be_removed.add(_id)
        self.channels.difference_update(to_be_removed)
        self.channels.save(self.cache)

    async def broadcast(self, msg: str):
        to_be_removed = set()
        for cinfo in self.channels:
            _id = cinfo[0]
            ch = self.get_channel(_id)
            try:
                await self.send_message(ch, msg)
            except:
                logger.error(f"Channel #{cinfo[2]} on server {cinfo[1]} does not exist")
                logger.error('...Now will be pruned')
                to_be_removed.add(_id)
        self.channels.difference_update(to_be_removed)
        self.channels.save(self.cache)

    def get_latest_border(self):
        return self.cache.load('border.json')

    def get_prev_border(self):
        return self.cache.load('border-prev.json')

    def save_border(self, border):
        self.cache.save('border.json', borderutil.serialize(border))

    def save_prev(self, border):
        self.cache.save('border-prev.json', border)

    def get_past_border(self, event_code):
        filename = f'border-past{event_code}.json'
        bd = self.cache.load(filename).val
        if not bd:
            logger.info(f'Event {event_code} is not in cache, fetch now')
            ev = borderutil.get_event_metadata(event_code)
            bd = ev.fetch_border(self.secret_token)
            self.cache.save(filename, borderutil.serialize(bd))
        return bd

    def check_permission(self, ctx) -> bool:
        return ctx.message.server and ctx.message.author == ctx.message.server.owner

    def add_channel(self, chan, name, server) -> bool:
        if chan not in self.channels:
            self.channels.add(chan, name, server)
            self.channels.save(self.cache)
            return True
        else:
            return False

    def remove_channel(self, chan):
        if chan in self.channels:
            self.channels.remove(chan)
            self.channels.save(self.cache)

    async def purge(self, chan: discord.Channel) -> int:
        if chan.id in self.channels:
            is_me = lambda m: m.author == self.user
            deleted = await self.purge_from(chan, limit=100, check=is_me)
            return deleted
        else:
            return 0

    async def update(self, bd):
        prev = self.get_latest_border().val
        if prev is None or prev['metadata']['id'] != bd['metadata']['id']:
            prev = None
        await self.broadcast(borderutil.format_with(bd, prev))
        self.save_border(bd)
        self.save_prev(prev)


def initialize(config):
    bot = BorderBot(config['cache_root'], config['api_token'])
    _ = Fetcher(bot, config['api_token'], config['delay'])
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

        if osp.exists('announcement.txt'):
            announce = '```\n' + open('announcement.txt').read() + '```'
            await bot.greet_and_prune(announce)
        else:
            await bot.greet_and_prune(texts['recover'].format(bot.user.name))

    @bot.command(pass_context=True)
    async def add_channel(ctx, channel: discord.Channel):
        """チャンネルを通知リストに追加する（所有者限定）"""
        if not bot.check_permission(ctx):
            await bot.say(texts['no_permission'])
            return
        logger.info(f'Registering channel {channel.name}...')
        if bot.add_channel(channel.id, name=channel.name, server=channel.server.name):
            logger.info(f'Registered channel {channel.name} to list.')
            await bot.send_message(bot.get_channel(channel.id), texts["greet"])
        else:
            logger.info('Channel already registered. Ignored.')

    @bot.command(pass_context=True)
    async def remove_channel(ctx, channel: discord.Channel):
        """チャンネルを通知リストから外す（所有者限定）"""
        if not bot.check_permission(ctx):
            await bot.say(texts['no_permission'])
            return
        logger.info(f'Unregistered channel {channel.name}...')
        bot.remove_channel(channel.id)
        await bot.send_message(bot.get_channel(channel.id), texts["bye"])

    @bot.command()
    async def border(event_code=None):
        """イベントボーダーを表示する"""
        prev = None
        if not event_code:
            try:
                bd = bot.get_latest_border().get()
                prev = bot.get_prev_border().val
            except ValueError:
                await bot.say(texts['cache_miss'])
                return
        else:
            try:
                bd = bot.get_past_border(event_code)
            except IOError:
                await bot.say(texts['event_not_found'])
                return
            except ValueError:
                await bot.say(texts['no_border'])
                return
        await bot.say(borderutil.format_with(bd, prev))

    @bot.command(pass_context=True, hidden=True)
    async def purge(ctx):
        if not bot.check_permission(ctx):
            await bot.say(texts['no_permission'])
            return
        channel = ctx.message.channel
        await bot.say(texts['purge_warning'])
        def confirm(msg):
            return msg in ['y', 'n']
        for _ in range(3):
            resp = await bot.wait_for_message(author=ctx.message.author, check=confirm)
            if resp == 'y':
                await bot.say(texts['purge_confirm'])
            else:
                await bot.say(texts['purge_canceled'])
                return
        deleted = await bot.purge(channel)
        logger.info(f'Deleted {len(deleted)} message(s) from channel {channel.name}')


    return bot


if __name__ == '__main__':
    config = get_config(config_path)
    if not config['token']:
        logger.error("Token is not filled in! Shutting down now...")
        sys.exit(1)
    border_bot = initialize(config)
    border_bot.run(config['token'])
