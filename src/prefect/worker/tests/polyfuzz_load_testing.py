import random
from typing import Dict, List
import string
from worker.bots.nlp_bot import NLPBot

nlpbot: NLPBot


def generate_all_keywords(n: int = 60000) -> Dict[str, Dict[str, List[str]]]:
    all_keywords = {}
    for _ in range(n):
        word_length = random.randint(4, 7)  # Generate a random length between 4 and 7
        word = "".join(random.choices(string.ascii_uppercase, k=word_length))  # Generate a random string

        sub_forms_length = random.randint(0, 2)  # Generate a random length between 0 and 2 for sub_forms
        sub_forms = [f"{word}Sub{str(j)}" for j in range(sub_forms_length)]

        all_keywords[word] = {"name:": word, "tag_type": "MISC", "sub_forms": sub_forms}

    return all_keywords


# Generate current_keywords as a random subset of all_keywords
def generate_current_keywords(all_keywords: Dict[str, Dict[str, List[str]]], m: int = 25) -> Dict[str, Dict[str, List[str]]]:
    return dict(random.sample(list(all_keywords.items()), m))
