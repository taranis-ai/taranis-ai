import random
import time
from typing import Dict, List
import string
import numpy as np
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


def load_testing_polyfuzz(all_keywords_size: int = 60000, current_keywords_size: int = 25, iterations: int = 500):
    all_keywords = generate_all_keywords(all_keywords_size)

    # Create a list to hold the execution times
    execution_times = []
    result_keywords = {}
    for i in range(iterations):
        current_keywords = generate_current_keywords(all_keywords, current_keywords_size)
        start_time = time.time()
        from_list, to_list = nlpbot.polyfuzz(list(all_keywords.keys()), list(current_keywords.keys()))
        result_keywords |= nlpbot.update_keywords_from_polyfuzz(from_list, to_list, all_keywords, current_keywords)
        end_time = time.time()

        execution_times.append(end_time - start_time)
        if i % 10 == 0:
            print(f"Completed {i} iterations")
            print(f"Average execution time: {np.mean(execution_times)} seconds")
            print(f"Total execution time: {np.sum(execution_times)} seconds")

    print(result_keywords)
    print(len(result_keywords))
    # Compute the mean execution time
    print(f"Average execution time: {np.mean(execution_times)} seconds")
    print(f"Total execution time: {np.sum(execution_times)} seconds")


if __name__ == "__main__":
    nlpbot = NLPBot()
    load_testing_polyfuzz(50000, 25, 100)
