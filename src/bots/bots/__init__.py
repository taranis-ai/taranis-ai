__all__ = ['base_bot', 'grouping_bot', 'wordlist_updater_bot', 'analyst_bot', 'tagging_bot']
from . import grouping_bot, wordlist_updater_bot, analyst_bot, tagging_bot

bot_list = [
    analyst_bot.AnalystBot(),
    grouping_bot.GroupingBot(),
    wordlist_updater_bot.WordlistUpdaterBot(),
    tagging_bot.TaggingBot()
  ]
