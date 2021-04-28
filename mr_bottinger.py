import os
import requests as rq
import dotenv as dv

import discord
from discord.ext import commands
from discord_slash.utils.manage_commands import create_option
from discord_slash import SlashCommand, SlashContext

global log_id
global pasted_logs

async def extract_content(content):
    """Extract content from log files"""
    extracted = []
    error_msg = []
    version = "0.0.0.0"

    lines = str(content).split('\\n')
    for ii in range(len(lines)):
        if lines[ii].__contains__("FireyCallouts, Version"):
            version = lines[ii].split("Version=")[1].split(",")[0]
        elif lines[ii].__contains__("[FireyCallouts]"):
            extracted.append(lines[ii].replace("\\r", "").replace("\\", ""))
        elif lines[ii].lower().__contains__("exception"):
            error_msg = lines[ii:]
            break

    return version, extracted, error_msg


async def warn_user(user: str = ""):
    """Check for existence of the user id in the warning files"""

    with open("warns/warn2.txt", "r+") as w2:
        if user in w2.read():
            return 3
        else:
            with open("warns/warn1.txt", "r+") as w1:
                if user in w1.read():
                    w2.write(user)
                    return 2
                else:
                    w1.write(user)
                    return 1


async def warn_remove(user_id: str, file: int):
    """Remove warnings from a user"""

    if file != 1 and file != 2:
        return False
    
    found = False
    with open("warns/warn"+str(file)+".txt", "r") as f:
        lines = f.readlines()

    if user_id in lines:
        found = True
        lines.remove(user_id)

    with open("warns/warn"+str(file)+".txt", "w") as f:
        f.writelines(lines)

    return found


def main():
    """Main method to start bot"""

    global log_id
    global pasted_logs
    logs_dir = "logs/"
    pasted_logs = []

    # Load .env
    dv.load_dotenv()

    # Prepare variables for log checking
    log_id = 0
    latest_version = os.getenv("PUBLICV")

    vip_users = os.getenv("ALLOWED")[1:-1].split(",")
    bad_words = os.getenv("BADWORDS")[1:-1].split(",")

    guild_ids = [int(os.getenv("GUILDID"))]

    attach_channels = ["support", "admin", "testingsuite", "vip"]

    filter_chat = False

    # Create client
    client = commands.Bot(command_prefix="!", intents=discord.Intents.all())
    slash = SlashCommand(client, sync_commands=True)

    # On startup
    @client.event
    async def on_ready():
        print("MrBottinger is now active.")

    # Message event
    @client.event
    async def on_message(message):
        """On sent messages"""
        global log_id

        if message.author == client.user:# or message.author.id in vip_users:
            return

        if any(word in str(message.content) for word in bad_words) and filter_chat:
            warn = await warn_user(str(message.author.id))
            if warn < 3:
                await message.reply("Your message contains inappropirate wording. Warnings: " + str(warn))
            else:
                await message.guild.ban(message.author, reason="3 Warnings")
                await message.reply("User banned.")
            await message.delete()
            return


        attachments = message.attachments
        for attachment in attachments:
            if attachment:
                content_type = attachment.content_type
                if 'text' in content_type.lower():
                    if str(message.channel) not in attach_channels:
                        await message.reply("Upload your log files in the support channel.")
                        await message.delete()
                        return
                    elif str(message.channel) == "testingsuite":
                        return

                    content = await attachment.read()
                    version, fireylog, error_msg = extract_content(content)

                    if version == "0.0.0.0":
                        await message.reply("Unable to extract FireyCallouts version. FireyCallouts was not"
                                            "loaded in this session.")
                    elif(version != latest_version):
                        await message.reply("You have loaded FireyCallouts version " + version + ", but the "
                                            "latest version is " + latest_version + "; Please download the "
                                            "newest version on lspdfr.com: "
                                            "https://www.lcpdfr.com/downloads/gta5mods/scripts/33086-fireycallouts/")
                    elif(len(fireylog) == 0):
                        await message.reply("There was no log instance found for FireyCallouts.")
                    elif(len(error_msg) == 0):
                        await message.reply("The log does not contain an exception message. Please make sure to "
                                            "upload the complete RagePluginHook.log")
                    else:
                        await message.reply("The log will be saved for further investigation. Thanks for uploading. "
                                            "Your log ID is " + str(log_id) + ".")
                        with open(logs_dir + "log_" + str(log_id) + ".log", "w") as file:
                            for line in fireylog:
                                file.write(line + "\n")
                            for line in error_msg:
                                file.write(line + "\n")

                        log_id += 1

                elif not 'image' in content_type.lower() or "video" in content_type.lower():
                    warn = await warn_user(str(message.author.id))
                    if warn < 3:
                        await message.reply("The file type '" + content_type + "' is not allowed. Warnings: " + str(warn))
                    else:
                        await message.guild.ban(message.author, reason="3 Warnings")
                        await message.reply("User banned.")
                    await message.delete()
                    break
                else:
                    continue

        if not attachments:
            if str(message.content)[:8] == "!report ":
                user = str(message.author)
                reported = str(message.content)[8:]
                with open("reports.txt", "a") as f:
                    f.write(user + "\t" + reported + "\n")
                await message.reply("Your report has been saved.")


    # Ping command
    @slash.slash(name="ping", description="Show your ping.", guild_ids=guild_ids)
    async def _ping(ctx): # Defines a new "context" (ctx) command called "ping."
        await ctx.send(f"Pong! ({client.latency*1000}ms)")

    # Upload command
    @slash.slash(name="upload", description="Upload a log to pastebin.",
                 options=[create_option(name="logid", description="The log ID of the log that should be uploaded.",
                          option_type=3,required=True)], guild_ids=guild_ids)
    async def _upload(ctx, logid: str):
        if logid.isdigit():
            if int(logid) < log_id and logid not in pasted_logs:
                try:
                    await ctx.send(content="Sending log " + logid, file=discord.File('./logs/log_'+logid+".log"))
                except:
                    await ctx.send(content="Failed to upload log.")
        else:
            await ctx.send(content="The specified log ID is invalid.")

    # Filter command
    @slash.slash(name="filter", description="Set chat filtering",
                 options=[create_option(name="state", description="True / False",
                                        option_type=3, required=True)], guild_ids=guild_ids)
    async def _filter(ctx, state: str):
        filter_chat = True if state == "True" else False
        await ctx.send("Chat filtering and warning system is now " + ("enabled" if filter_chat else "disabled"))

    # Unwarn command
    @slash.slash(name="unwarn", description="Remove warnings from user",
                 options=[create_option(name="user", description="Name of the user",
                                        option_type=6, required=True),
                          create_option(name="amount", description="Amount of warnings to remove (max. 2 possible)",
                                        option_type=4, required=True)], guild_ids=guild_ids)
    async def _unwarn(ctx, user: discord.User, amount: int):
        found = await warn_remove(str(user.id), 2)
        if amount == 1:
            if not found:
                found = await warn_remove(str(user.id), 1)
                if not found:
                    await ctx.send("Removed 0 warnings from user "+str(user)+". Warnings left: 0.")
                else:
                    await ctx.send("Removed 1 warning from user "+str(user)+". Warnings left: 0.")
            else:
                await ctx.send("Removed 1 warning from user "+str(user)+". Warnings left: 1.")
        elif amount > 1:
            await warn_remove(str(user.id), 1)
            await ctx.send("Removed all warnings from user "+str(user)+". Warnings left: 0.")

    # Warn command
    @slash.slash(name="warn", description="Warn a user",
                 options=[create_option(name="user", description="Name of the user",
                                        option_type=6, required=True),
                          create_option(name="reason", description="Reason for the warning",
                                        option_type=3, required=False)], guild_ids=guild_ids)
    async def warn(ctx, user: discord.Member, reason: str = "None"):
        user_id = user.id
        warn = await warn_user(str(user_id))
        if warn < 3:
            await ctx.send("User " + str(user) + " has been warned. Reason: " + reason + "; Warnings: " + str(warn))
        else:
            await ctx.guild.ban(user, reason="3 Warnings")
            await ctx.reply("User banned due to third warning.")

    # Run bot
    client.run(os.getenv('TOKEN'))


if __name__ == "__main__":
    main()
