import os
import requests as rq
import dotenv as dv

import discord
from discord.ext.commands import Bot
from discord.ext import commands
from discord_slash import SlashCommand

global save_number

def extract_content(content):
    """ """
    extracted = []
    error_msg = []
    version = "0.0.0.0"

    lines = str(content).split('\\n')
    for ii in range(len(lines)):
        if lines[ii].__contains__("FireyCallouts, Version"):
            version = lines[ii].split("Version=")[1].split(",")[0]
        elif lines[ii].__contains__("[FireyCallouts]"):
            extracted.append(lines[ii].replace("\\r", "").replace("\\", ""))
        elif lines[ii].__contains__("EXCEPTION"):
            error_msg = lines[ii:]
            break;

    return version, extracted, error_msg



def main():
    """ """

    global save_number

    # Load .env
    dv.load_dotenv()

    # Prepare variables for log checking
    save_number = 0
    latest_version = os.getenv("PUBLICV")

    extracted = os.getenv("ALLOWED")[1:-1]
    vip_users = extracted.split(",")

    guild_ids = [int(os.getenv("GUILDID"))]

    attach_channels = ["support", "admin", "testingsuite", "vip"]

    # Create client
    client = commands.Bot(command_prefix = '!')
    slash = SlashCommand(client, sync_commands=True)

    # On startup
    @client.event
    async def on_ready():
        print("MrBottinger is now active.")

    # Message event
    @client.event
    async def on_message(message):

        if not str(message.author.id) in vip_users or True:
            attachments = message.attachments
            for attachment in attachments:
                if attachment:
                    content_type = attachment.content_type
                    if 'text' in content_type.lower():
                        if str(message.channel) not in attach_channels:
                            await message.reply("Upload your log files in the support channel.")
                            await message.delete()
                            return

                        print("Sent: text. Approved.")
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
                            await message.reply("The log will be saved for further investigation. Thanks for uploading.")
                            with open("log_" + str(save_number) + ".log", "w") as file:
                                for line in fireylog:
                                    file.write(line + "\n")
                                for line in error_msg:
                                    file.write(line + "\n")
                            save_number += 1

                    elif not 'image' in content_type.lower() or "video" in content_type.lower():
                        print("Sent: restricted file type. Not approved.")
                        await message.reply("The file type '" + content_type + "' is not allowed.")
                        await message.delete()
                        break
                    else:
                        print("Sent: image or video. Approved.")

        if message.author == client.user:
            return

        if message.content == "!Test":
            await message.channel.send("Test")

    """
    @slash.slash(name="ping", guild_ids=guild_ids)
    async def _ping(ctx):
        await ctx.send(f"Pong! ({client.latency*1000}ms)")
    """


    client.run(os.getenv('TOKEN'))


if __name__ == "__main__":
    main()
