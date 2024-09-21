#!/usr/bin/env python3

import requests
import json
import datetime
import argparse

from time import sleep
from discord_webhook import DiscordWebhook, DiscordEmbed
from types import SimpleNamespace as Namespace

def get_runs(url):
    r = requests.get(url)
    runs = json.loads(r.text, object_hook=lambda d: Namespace(**d))

    runs.data.reverse()
    return runs.data

def get_users(run):
    users_str = ''
    users = []
    for u in run.players.data:
      #  r = requests.get(u.uri)
      #  ux = json.loads(r.text, object_hook=lambda d: Namespace(**d))
        if users_str == '':
            users_str = u.names.international
        else:
            users_str = users_str + ", " + u.names.international

        users.append(u)

    return (users_str, users)

def get_game(run):
    return (run.game.data.names.international, run.game.data)

def get_category(run):
    return (run.category.data.name, run.category.data)

def get_category_variables(run):
    r = requests.get('https://www.speedrun.com/api/v1/categories/{}/variables'.format(run.category.data.id))
    variables = json.loads(r.text, object_hook=lambda d: Namespace(**d))

    return variables.data

def get_variables(run):
    variables = get_category_variables(run)
    run_variables = vars(run.values)

    result = []
    for variable in variables:
        if variable.id in run_variables:
            result.append((variable, run_variables[variable.id]))

    return result

def generate_webhooks(webhook_url, webhook_name, runs):
    for run in runs:
        (users_str, users) = get_users(run)
        (game_name, game) = get_game(run)
        (cat_name, category) = get_category(run)
        variables = get_variables(run)
        has_rt = run.times.realtime is not None
        tm = str(datetime.timedelta(seconds=run.times.primary_t))
        has_igt = run.times.ingame is not None and run.times.ingame != run.times.primary
        igt = str(datetime.timedelta(seconds=run.times.ingame_t))
        url = run.weblink
        print ('{}: {} - {} - {} \n {}\n\n'.format(users,game,category,tm,url))

        webhook = DiscordWebhook(url=webhook_url, username=webhook_name)
        cover_art = getattr(game.assets, 'cover-small').uri
        embed = DiscordEmbed(title='Game', description=game_name)
        embed.set_thumbnail(url=cover_art)
        for user in users:
            embed.add_embed_field(name='Runner', value=user.names.international)
        embed.set_author(name='Run verified!',url=run.weblink)
        embed.set_timestamp(timestamp=datetime.datetime.fromisoformat(run.submitted))
        embed.add_embed_field(name='Category', value='[{}]({})'.format(cat_name, category.weblink))
        if run.level.data is not None:
            embed.add_embed_field(name='Level', value=run.level.data.name)
        for var_data in variables:
            embed.add_embed_field(name=var_data[0].name, value=vars(var_data[0].values.values)[var_data[1]].label)
        embed.add_embed_field(name='Time', value='[{}]({})'.format(tm, run.weblink))
        if has_igt:
            embed.add_embed_field(name='In-game Time', value='[{}]({})'.format(igt, run.weblink))
        embed.set_footer(text='Submitted ')
        webhook.add_embed(embed)
        sleep(5)
        webhook.execute()

def print_runs(runs):
    for run in runs:
        print('{} - {} - {}'.format(run.game.data.names.international,run.players, run.category.data.name))

def read_runfile(filename):
    with open(filename) as json_file:
        old_runs = json.load(json_file)
        return old_runs

def read_config(filename):
    with open(filename) as json_file:
        return json.load(json_file)

def write_runfile(old_runs, filename):
    with open(filename, 'w') as json_file:
        json.dump(old_runs, json_file)

def get_games(series):
    r = requests.get('https://www.speedrun.com/api/v1/series/{}/games'.format(series))
    ux = json.loads(r.text, object_hook=lambda d: Namespace(**d))
    return ux.data



def main():
    parser = argparse.ArgumentParser(description='Update a discord channel with runs from speedrun.com',fromfile_prefix_chars='@')
    parser.add_argument('--config', dest='config', help='Path to JSON configuration file')
    parser.add_argument('--webhook', dest='webhook', help='Webhook URL [optional]')
    parser.add_argument('--name', dest='name', help='Webhook name to override the default [optional]')


    args = parser.parse_args()
    if args.config is None:
        parser.print_help()
        exit(1)


    config = read_config(args.config)

    if args.webhook is None:
        webhook_url = config['webhook']
    else:
        webhook_url = args.webhook
    if args.name is None:
        webhook_name = config['name']
    else:
        webhook_name = args.name
    api_url = 'https://www.speedrun.com/api/v1/runs?embed=game,category,level,players&'+'&'.join(config['params'])

    print(api_url + '\n')

    series = None
    try:
        series = config['series']
    except KeyError:
        pass

    raw_runs = []
    if series is not None and series != "":
        games = get_games(series) # /series/{series}/games
        for game in games:
            raw_runs.extend(get_runs(api_url+'&game='+game.id))
            sleep(5)
    else:
        raw_runs.extend(get_runs(api_url))

    old_runs = []
    try:
        old_runs.extend(read_runfile(config['runfile']))
    except:
        pass

    
    runs = list(filter(lambda r: r.id not in old_runs, raw_runs))

    print_runs(runs)
    generate_webhooks(webhook_url, webhook_name, runs)

    old_runs.extend(run.id for run in runs)

    write_runfile(old_runs, config['runfile'])
 

if __name__ == "__main__":
    main()
