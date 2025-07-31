from prefect import flow, task
from core.log import logger
from models.bot import BotTaskRequest 
from worker.core_api import CoreApi
import worker.bots  


@task
def get_bot_config(bot_id: int):
    """Get bot configuration from CoreApi"""
    logger.info(f"[bot_task] Getting bot config for {bot_id}")
    
    core_api = CoreApi()
    bot_config = core_api.get_bot_config(bot_id)
    
    if not bot_config:
        raise ValueError(f"Bot with id {bot_id} not found")
        
    return bot_config


@task
def execute_bot_by_config(bot_config: dict, filter_params: dict | None = None):
    """Execute bot using config"""
    logger.info(f"[bot_task] Executing bot by config")
    
    bot_type = bot_config.get("type")
    if not bot_type:
        raise ValueError("Bot has no type")

    bots = {
        "analyst_bot": worker.bots.AnalystBot(),
        "grouping_bot": worker.bots.GroupingBot(),
        "tagging_bot": worker.bots.TaggingBot(),
        "wordlist_bot": worker.bots.WordlistBot(),
        "nlp_bot": worker.bots.NLPBot(),
        "story_bot": worker.bots.StoryBot(),
        "ioc_bot": worker.bots.IOCBot(),
        "summary_bot": worker.bots.SummaryBot(),
        "sentiment_analysis_bot": worker.bots.SentimentAnalysisBot(),
        "cybersec_classifier_bot": worker.bots.CyberSecClassifierBot(),
    }
    
    bot = bots.get(bot_type)
    if not bot:
        raise ValueError("Bot type not implemented")

    bot_params = bot_config.get("parameters")
    if not bot_params:
        raise ValueError("Bot has no parameters")

    if filter_params:
        bot_params["filter"] = filter_params

    return bot.execute(bot_params)


@flow(name="bot-task-flow")
def bot_task_flow(request: BotTaskRequest):
    try:
        logger.info(f"[bot_task_flow] Starting bot task")
        
        # Get bot config 
        bot_config = get_bot_config(request.bot_id)
        
        # Execute bot 
        result = execute_bot_by_config(bot_config, request.filter)
        
        logger.info(f"[bot_task_flow] Bot task completed successfully")
        
        return result

    except Exception as e:
        logger.exception(f"[bot_task_flow] Bot task failed")
        raise