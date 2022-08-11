import bots.bots as bots


bots_dict = {}


def initialize():
    global bots_dict

    bot = bots.analyst_bot.AnalystBot()
    bots_dict[bot.type] = bot

    bot = bots.grouping_bot.GroupingBot()
    bots_dict[bot.type] = bot

    bot = bots.wordlist_updater_bot.WordlistUpdaterBot()
    bots_dict[bot.type] = bot

    bot = bots.tagging_bot.TaggingBot()
    bots_dict[bot.type] = bot

    bot = bots.nlp_bot.NLPBot()
    bots_dict[bot.type] = bot


def get_registered_bots_info():
    return [bots_dict[key].get_info() for key in bots_dict]


def process_event(event_type, data):
    for key in bots_dict:
        bots_dict[key].process_event(event_type, data)
