from bots.grouping_bot import GroupingBot
from bots.analyst_bot import AnalystBot
from bots.wordlist_updater_bot import WordlistUpdaterBot

bots = {}


def initialize():
    register_bot(AnalystBot())
    register_bot(GroupingBot())
    register_bot(WordlistUpdaterBot())


def register_bot(bot):
    bots[bot.type] = bot
    bot.initialize()


def get_registered_bots_info():
    bots_info = []
    for key in bots:
        bots_info.append(bots[key].get_info())

    return bots_info


def process_event(event_type, data):
    for key in bots:
        bots[key].process_event(event_type, data)
