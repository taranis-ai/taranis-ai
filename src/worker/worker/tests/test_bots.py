

def test_initalize_bots():
    import worker.bots as bots
    bots.AnalystBot(),
    bots.GroupingBot(),
    bots.NLPBot(),
    bots.TaggingBot(),
    bots.WordlistUpdaterBot(),
