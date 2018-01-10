import sys

from cache import Cache

import border as borderutil

try:
    from discord.ext import commands
    import discord
except ImportError:
    print("Discord.py is not installed.\n"
          "Consult the guide for your operating system "
          "and do ALL the steps in order.\n"
          "https://twentysix26.github.io/Red-Docs/\n")
    sys.exit(1)

description = """This is a bot to record and post to registered channel latest border of MLTD"""


class BorderBot(commands.Bot):
    def __init__(self, cache_root):
        self.cache = Cache(cache_root)
        self.channels = set(self.cache.load("channels.json").get_or([]))
        super().__init__(description=description, command_prefix="!")

    async def broadcast(self, msg: str):
        for _id in self.channels:
            await self.send_message(self.get_channel(_id), msg)

    def get_latest_border(self):
        return self.cache.load('border.json')

    def get_prev_border(self):
        return self.cache.load('border-prev.json')

    def save_border(self, border):
        self.cache.save('border.json', borderutil.serialize(border))

    def save_prev(self, border):
        self.cache.save('border-prev.json', border)

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

    @staticmethod
    def get_past_border(event_code):
        return borderutil.get_past_event_border(event_code)

    async def purge(self, chan: discord.Channel) -> int:
        if chan.id in self.channels:
            is_me = [lambda m: m.author == self.user]
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
