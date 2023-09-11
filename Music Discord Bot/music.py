import discord
from discord.ext import commands 
import yt_dlp as youtube_dl
import asyncio

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=False, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []

    @commands.command(description="joins a voice channel")
    async def join(self, ctx):
        if ctx.author.voice is None:
            await ctx.send("You're not in a voice channel!")
        voice_channel = ctx.author.voice.channel
        if ctx.voice_client is None:
            await voice_channel.connect()
        else:
            await ctx.voice_client.move_to(voice_channel)

    @commands.command(description="streams music | adds a song to the queue while paused")
    async def play(self, ctx, *, query):
        async with ctx.typing():
            try:
                data = await self.search_youtube(query)
                url = data.get('url')
                title = data.get('title', 'Unknown Title')
            except youtube_dl.utils.DownloadError:
                return await ctx.send("No results found for the given query.")

            if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
                title = await self.add_to_queue(ctx, query)
                if title:
                    await ctx.send(f"**{title}** added to the queue.")
                else:
                    await ctx.send("Could not add the song to the queue. Please try again.")
            else:
                await self.play_song(ctx, url, title)

    async def search_youtube(self, query):
        loop = self.bot.loop
        query = query + '[official audio]'
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        if 'entries' in data:
            # Take the first item from the search results
            data = data['entries'][0]
        return data
    
    async def play_song(self, ctx, url, title):
        player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
        ctx.voice_client.play(player, after=lambda e: self.play_next(ctx) if e is None else None)
        embed = discord.Embed(title="Now playing", description=f"[{title}]({url}) [{ctx.author.mention}]")
        await ctx.send(embed=embed)
    
    async def add_to_queue(self, ctx, song):
        async with ctx.typing():
            try:
                data = await self.search_youtube(song)
                url = data.get('url')
                title = data.get('title', 'Unknown Title')
                self.queue.append((url, title))  # Add the song (url, title) tuple to the queue
                return title
            except youtube_dl.utils.DownloadError:
                return None
            
    def play_next(self, ctx):
        if self.queue:
            url, title = self.queue.pop(0)  # Get the first song in the queue
            asyncio.run_coroutine_threadsafe(self.play_song(ctx, url, title), self.bot.loop)
    
    @commands.command(description="shows the current queue")
    async def queue(self, ctx):
        if not self.queue:
            return await ctx.send("The queue is empty.")
        queue_list = '\n'.join(f"{index + 1}. {title}" for index, (_, title) in enumerate(self.queue))
        embed = discord.Embed(title="Music Queue", description=queue_list)
        await ctx.send(embed=embed)
    
    @commands.command(description="pauses music")
    async def pause(self, ctx):
        ctx.voice_client.pause()
        await ctx.send("Paused ⏸️")
    
    @commands.command(description="resumes music")
    async def resume(self, ctx):
        ctx.voice_client.resume()
        await ctx.send("Resuming ⏯️")

    @commands.command(description="stops and disconnects the bot from voice")
    async def leave(self, ctx):
        await ctx.voice_client.disconnect()

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

def setup(bot):
    bot.add_cog(Music(bot))
        
