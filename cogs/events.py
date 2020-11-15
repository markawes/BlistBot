import random
import re
import discord
from discord.ext import commands, tasks
import datetime
from textwrap import dedent as wrap

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_join.start()  # pylint: disable=no-member
        self.change_status.start()
        self.update_statuses.start()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.CheckFailure):
            await ctx.send("This command cannot be used in this guild!")

        errors = {
            commands.MissingPermissions: {"msg": "You do not have permissions to run this command."},
            discord.HTTPException: {"msg": "There was an error connecting to Discord. Please try again."},
            commands.CommandInvokeError: {"msg": "There was an issue running the command."},
            commands.NotOwner: {"msg": "You are not the owner."},
        }

        if not isinstance(error, commands.MissingRequiredArgument):
            ets = errors.get(error.__class__)
            if not ets:
                ets = {"msg": "[ERROR]"}

            em = discord.Embed(
                description = ets["msg"].replace("[ERROR]", f"{error}"), color = discord.Color.red())

            try:
                await ctx.send(embed = em)
            except discord.Forbidden:
                pass

        elif isinstance(error, commands.MissingRequiredArgument):
            em = discord.Embed(color = discord.Color.red(),
                               description = f"`{str(error.param).partition(':')[0]}` is a required argument!")
            await ctx.send(embed = em)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id == 743127622053003364:
            if message.attachments or re.findall(r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>", message.content):
                await message.add_reaction("✔")
                await message.add_reaction("❌")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild == self.bot.main_guild and member.bot:
            role = member.guild.get_role(716684129453735936)
            await member.add_roles(role)

        if member.guild == self.bot.verification_guild and member.bot:
            bot_role = self.bot.verification_guild.get_role(763187834219003934)
            await member.add_roles(bot_role)
            overwrites = {
                member.guild.get_role(763177553636098082): discord.PermissionOverwrite(manage_channels = True),
                member.guild.get_role(763187834219003934): discord.PermissionOverwrite(read_messages = False),
                member: discord.PermissionOverwrite(read_messages = True),
            }
            category = await member.guild.create_category(name = member.name, overwrites = overwrites)
            channel = await category.create_text_channel(name = "Testing")
            await category.create_text_channel(name = "Testing-NSFW", nsfw = True)
            await category.create_voice_channel(name = "Voice Testing", bitrate = member.guild.bitrate_limit)

            bot = await self.bot.pool.fetch("SELECT * FROM main_site_bot WHERE id = $1", member.id)

            embed = discord.Embed(
                title = str(member),
                color = discord.Color.blurple(),
                description = wrap(
                    f"""
                    >>> Owner: ``{str(self.bot.main_guild.get_member(bot[0]['main_owner']))}``
                    Prefix: ``{bot[0]['prefix']}``
                    Tags: ``{', '.join(list(bot[0]['tags']))}``
                    Added: ``{bot[0]['joined'].strftime('%D')}``
                    """
                )
            )
            embed.add_field(
                name = "**Links**",
                value = wrap(
                    f"""
                    >>> Privacy Policy: {bot[0]['privacy_policy_url'] or 'None'}
                    Website: {bot[0]['website'] or 'None'}
                    Invite: {bot[0]['invite_url'] or 'Default'}
                    Blist Link: https://blist.xyz/bot/{member.id}/
                    """
                )
            )
            embed.add_field(name = "Short Description", value = bot[0]['short_description'], inline = False)
            embed.add_field(name = "Notes", value = bot[0]['notes'], inline = False)
            embed.set_thumbnail(url = member.avatar_url)
            message = await channel.send(embed = embed)
            await message.pin()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        staff = self.bot.main_guild.get_role(716713561233031239)
        if staff not in before.roles and staff in after.roles:
            await self.bot.mod_pool.execute("INSERT INTO staff VALUES($1, $2)", before.id, datetime.datetime.utcnow())
            await self.bot.pool.execute("UPDATE main_site_user SET staff = True WHERE userid = $1", before.id)
        if staff in before.roles and staff not in after.roles:
            await self.bot.mod_pool.execute("DELETE FROM staff WHERE userid = $1", before.id)
            await self.bot.pool.execute("UPDATE main_site_user SET staff = False WHERE userid = $1", before.id)

        bug_hunter = self.bot.main_guild.get_role(716722789234638860)
        if bug_hunter not in before.roles and bug_hunter in after.roles:
            await self.bot.pool.execute("UPDATE main_site_user SET bug_hunter = True WHERE userid = $1", before.id)
        if bug_hunter in before.roles and bug_hunter not in after.roles:
            await self.bot.pool.execute("UPDATE main_site_user SET bug_hunter = False WHERE userid = $1", before.id)


        admin1 = self.bot.main_guild.get_role(716713266683969626)
        admin2 = self.bot.main_guild.get_role(716713238955556965)
        if admin1 not in before.roles and admin1 in after.roles:
            await self.bot.pool.execute("UPDATE main_site_user SET administrator = True WHERE userid = $1", before.id)
        if admin1 in before.roles and admin1 not in after.roles:
            await self.bot.pool.execute("UPDATE main_site_user SET administrator = False WHERE userid = $1", before.id)
        if admin2 not in before.roles and admin2 in after.roles:
            await self.bot.pool.execute("UPDATE main_site_user SET administrator = True WHERE userid = $1", before.id)
        if admin2 in before.roles and admin2 not in after.roles:
            await self.bot.pool.execute("UPDATE main_site_user SET administrator = False WHERE userid = $1", before.id)

        if before.bot:
            staff_bot = self.bot.main_guild.get_role(777575976124547072)
            if staff_bot not in before.roles and staff_bot in after.roles:
                await self.bot.pool.execute("UPDATE main_site_bot SET staff = True WHERE id = $1", before.id)
            if staff_bot in before.roles and staff_bot not in after.roles:
                await self.bot.pool.execute("UPDATE main_site_bot SET staff = False WHERE id = $1", before.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.guild == self.bot.verification_guild and member.bot:
            category = discord.utils.get(member.guild.categories, name = member.name)
            for channel in category.channels:
                await channel.delete()
            await category.delete()

        if member.guild == self.bot.main_guild:
            if member.bot:
                x = await self.bot.pool.fetch("SELECT * FROM main_site_bot WHERE id = $1", member.id)
                if x:
                    embed = discord.Embed(
                        description = f"{member} ({member.id}) has left the server and is listed on the site! Use `b!delete` to delete the bot",
                        color = discord.Color.red())
                    await self.bot.get_channel(716727091818790952).send(embed = embed)
                    return
            if not member.bot:
                x = await self.bot.pool.fetch("SELECT * FROM main_site_bot WHERE main_owner = $1", member.id)
                if x:
                    for user in x:
                        if user["denied"]:
                            await self.bot.pool.execute("DELETE FROM main_site_bot WHERE id = $1", user["id"])
                            return
                        bots = " \n".join([f"{user['name']} (<@{user['id']}>)"])
                        listed_bots = f"{len(x)} bot listed:" if len(x) == 1 else f"{len(x)} bots listed:"
                        embed = discord.Embed(
                            description = f"{member} ({member.id}) left the server and has {listed_bots}\n\n{bots} \n\nUse the `b!delete` command to delete the bot",
                            color = discord.Color.red())
                        await self.bot.get_channel(716727091818790952).send(embed = embed)

    @tasks.loop(minutes = 30)
    async def check_join(self):
        bots = await self.bot.pool.fetch("SELECT * FROM main_site_bot WHERE approved = True")
        channel = self.bot.main_guild.get_channel(716727091818790952)
        for bot in bots:
            if bot['id'] == 765175524594548737:
                return
            b = self.bot.main_guild.get_member(bot['id'])
            if not b:
                embed = discord.Embed(
                    title = "Bot Has Not Joined!!",
                    description = "The following bot has not joined the Support Server after getting approved...",
                    color = discord.Color.red()
                )
                embed.add_field(
                    name = bot['name'],
                    value = str(
                        discord.utils.oauth_url(bot['id'], guild = self.bot.main_guild)) + "&disable_guild_select=true"
                )
                await channel.send(embed = embed)

    @tasks.loop(minutes = 60) # Minutes = 60 is better than Hours = 1!! This is for you @A Discord User @Soheab_
    async def update_statuses(self):
        bots = await self.bot.pool.fetch("SELECT * FROM main_site_bot WHERE approved = True")
        for bot in bots:
            member_instance = self.bot.main_guild.get_member(bot["id"])
            if member_instance is None:
                # Shouldn't be, but just in case
                pass
            await self.bot.pool.execute("UPDATE main_site_bot SET status = $1 WHERE id = $2", str(member_instance.status), bot["id"])

    @tasks.loop(minutes = 1)
    async def change_status(self):
        approved_bots = await self.bot.pool.fetchval(
            "SELECT COUNT(*) FROM main_site_bot WHERE approved = True AND denied = False")
        users = await self.bot.pool.fetchval("SELECT COUNT(*) FROM main_site_user")
        queued_bots = await self.bot.pool.fetchval(
            "SELECT COUNT(*) FROM main_site_bot WHERE approved = False AND denied = False")
        options = [
            f"with {queued_bots} bots in the queue",
            f"with {approved_bots} approved bots",
            f"with {users} total users"
        ]
        await self.bot.change_presence(activity = discord.Game(name = random.choice(options)))


def setup(bot):
    bot.add_cog(Events(bot))