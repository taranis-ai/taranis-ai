from worker.bots.analyst_bot import AnalystBot
from worker.bots.grouping_bot import GroupingBot
from worker.bots.ioc_bot import IOCBot
from worker.bots.nlp_bot import NLPBot
from worker.bots.sentiment_analysis_bot import SentimentAnalysisBot
from worker.bots.story_bot import StoryBot
from worker.bots.summary_bot import SummaryBot
from worker.bots.tagging_bot import TaggingBot
from worker.bots.wordlist_bot import WordlistBot
from worker.bots.cybersec_classifier_bot import CyberSecClassifierBot

BOT_REGISTRY = {
    "analyst_bot": AnalystBot,
    "grouping_bot": GroupingBot,
    "ioc_bot": IOCBot,
    "nlp_bot": NLPBot,
    "sentiment_analysis_bot": SentimentAnalysisBot,
    "story_bot": StoryBot,
    "summary_bot": SummaryBot,
    "tagging_bot": TaggingBot,
    "wordlist_bot": WordlistBot,
    "cybersec_classifier_bot": CyberSecClassifierBot,
}
