import bots

bots_dict = {}


def initialize():
    for bot in bots.bot_list:
        register_bot(bot)


def register_bot(bot):
    bots_dict[bot.type] = bot
    bot.initialize()


def get_registered_bots_info():
    bots_info = []
    for key in bots_dict:
        bots_info.append(bots_dict[key].get_info())

    return bots_info


def process_event(event_type, data):
    for key in bots_dict:
        bots_dict[key].process_event(event_type, data)
