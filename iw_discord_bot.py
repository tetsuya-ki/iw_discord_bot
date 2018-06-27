#!python3
# vim: set fileencoding=utf-8 :

################################
# discord bot for infra-workshop

## import
import configparser
import regex
import discord
from os.path import dirname, abspath
from datetime import datetime, timedelta, timezone
from requests import get as httpget
from json import loads as json_load
from xml.sax.saxutils import unescape

## static argment
JST = timezone(timedelta(hours=+9), 'JST')
BASE_DIR = dirname(abspath(__file__))

## regex-pattern for discord channel title
title_regexs = [
    r'\p{Han}',r'\p{Katakana}',r'\p{Hiragana}',r'\p{Latin}',
    r'\p{N}',r'\p{So}',r'\p{Pd}',
    r'[\u00A2-\u00F7]',r'[\u2100-\u2BD1]',
    r'[\u0391-\u03C9]',r'[\u0401-\u0451]',
    r'[\u2010-\u2312]',r'[\u2500-\u254B]',
    r'[\u25A0-\u266F]',r'[\u3000-\u3049]',
    r'[\uDC00-\uDCFF]',r'[\uFF00-\uFFFF]'
    ]
title_regex = r''
for reg in title_regexs:
    title_regex += reg + r'|'
title_regex = title_regex[0:-1] + r'+'

## read config from .ini
inifile = configparser.ConfigParser()
inifile.read(BASE_DIR + '/config.ini')
calendar_url = inifile.get('calendar',r'url')
calendar_day_line = int(inifile.get('calendar',r'day_line'))
discord_token = inifile.get('discord',r'token')
discord_server_id = inifile.get('discord',r'server_id')

################################
# Wordpress

## load today's events from wordpress callender
def get_wp_callender(worpress_url):
    sdt = datetime.now(JST)
    sdt = sdt.replace(hour=calendar_day_line, minute=0, second=0, microsecond=0)
    sdt = sdt.strftime('%Y/%m/%dT%H:%MZ')
    edt = (datetime.now(JST) + timedelta(days=1))
    edt = edt.replace(hour=calendar_day_line-1, minute=59, second=59, microsecond=0)
    edt = edt.strftime('%Y/%m/%dT%H:%MZ')
    API_URI = 'https://' + worpress_url + '/?rest_route=/tribe/events/v1/events'
    url = API_URI + "&start_date=" + sdt + "&end_date=" + edt
    response = httpget(url)
    if response.status_code != 200:
        print("error : " + str(response.status_code))
        return
    wss = json_load(response.text)
    return wss

################################
# Discord

## discord client object
client = discord.Client()

async def get_events():
    ## regex for remove htmltag
    p = regex.compile(r"<[^>]*?>")
    ret = []

    json_event = get_wp_callender(calendar_url)

    ## parse object for post discord
    for e in json_event["events"]:
        event = {}
        event["title"] = str(e["start_date_details"]["month"]) + str(e["start_date_details"]["day"]) + "-" + e["title"]
        msg = ""
        msg += e["title"] + "\n"
        msg += str(e["start_date_details"]["hour"]) + ":" + str(e["start_date_details"]["minutes"])
        msg += " 〜 "
        msg += str(e["end_date_details"]["hour"]) + ":" + str(e["end_date_details"]["minutes"]) + "\n"
        msg += "----" + "\n"
        description = p.sub("", e["description"])
        msg += unescape(description)
        event["description"] = msg

        ret.append(event)    
    return ret

## create discord text channel
async def setup_channel(client, title, message):
    server = client.get_server(discord_server_id)
    # parse for discord channel
    title = ("".join(regex.findall(title_regex,title))).lower()
    # check duplicate
    for channel in server.channels:
        if channel.type == discord.ChannelType.text:
            if channel.name == title:
                print("already_created")
                return 0

    print("Creating Channel...")
    new_chan = await client.create_channel(server, title)
    print("Post Description...")
    await client.send_message(new_chan, message)
    print("OK.")

@client.event
async def on_ready():
    # print('Logged in as')
    # print(client.user.name)
    # print(client.user.id)

    # thread main
    evs = await get_events()
    for ev in evs:
        await setup_channel(client,ev["title"],ev["description"])        
    # end thread
    await client.close()

def main():
    # execute discord api
    client.run(discord_token)

if __name__ == '__main__':
    main()
