#!/usr/bin/env python3

import logging
import re

import discord
import discord.errors

logger = logging.getLogger('groupoid')

class Groupoid(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inhabit_keys = {}
        self.inhabitants = {}

    def update_topic(self, channel, topic):
        m = re.search(r'\[groupoid:([^\]]*)\]', topic)
        if not m:
            return
        gconf = m.group(1).split(';')
        logger.debug('[update_topic] {}'.format(topic))
        for x in gconf:
            x = x.strip()
            m = re.match(r'(.*)=(.*)', x)
            if not m:
                continue
            name = m.group(1).strip()
            key = m.group(2).strip()
            self.inhabit_keys[key] = (channel, name)
            logger.debug('[update_topic] {} -> {}'.format(key, name))

    def refresh_topics(self):
        self.inhabit_keys.clear()
        for channel in self.get_all_channels():
            logger.debug('[refresh_topics] {}'.format(channel))
            if isinstance(channel, discord.TextChannel):
                topic = channel.topic
                if topic is not None:
                    self.update_topic(channel, topic)

    async def inhabit(self, message, key):
        try:
            (channel, name) = self.inhabit_keys[key]
        except KeyError:
            return await message.channel.send('no such key')
        self.inhabitants[message.author] = key
        return await message.channel.send('**you are {}**'.format(name))

    async def get_webhook(self, channel):
        hooks = await channel.webhooks()
        for hook in hooks:
            if hook.user == self.user:
                logger.debug('[get_webhook] found webhook')
                return hook
        else:
            logger.debug('[get_webhook] creating webhook')
            return await channel.create_webhook(name='groupoid')

    async def handle_message(self, message):
        try:
            key = self.inhabitants[message.author]
            (channel, name) = self.inhabit_keys[key]
        except KeyError:
            return await message.channel.send('not connected; use `!inhabit`')
        hook = await self.get_webhook(channel)
        return await hook.send(message.content, username=name, avatar_url=self.user.avatar_url)

    async def on_ready(self):
        logger.info('logged in as {}'.format(self.user))
        self.refresh_topics()

    async def on_message(self, message):
        if message.author == self.user:
            return
        if not isinstance(message.channel, discord.DMChannel):
            return

        logger.debug('[on_message] {!r}'.format(message.content))

        command = message.content.strip()

        if command == '!help':
            return await message.channel.send(
                'commands:\n'
                '`!help`\n'
                '`!inhabit <key>`\n'
                '`!refresh`\n')

        m = re.match(r'!inhabit (.*)', command)
        if m:
            return await self.inhabit(message, m.group(1))

        if command == '!refresh':
            self.refresh_topics()
            return await message.channel.send('refreshed.')

        if command.startswith('!'):
            return await message.channel.send('unrecognized command.  try `!help`')

        return await self.handle_message(message)

if __name__ == '__main__':
    client = Groupoid(guild_subscriptions=False)
    logging.basicConfig(level=logging.INFO)
    with open('secret_token') as f:
        token = f.read().strip()
    client.run(token)
