#!/usr/bin/env python3

import nltk
from transformers import AutoModelForSeq2SeqLM
from sentence_transformers import SentenceTransformer

hf_models = [
    "facebook/bart-large-cnn",
    "T-Systems-onsite/mt5-small-sum-de-en-v2",
]

transformers_models = [
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
]

for model in hf_models:
    print(f"Downloading {model}")
    AutoModelForSeq2SeqLM.from_pretrained(model)

for model in transformers_models:
    print(f"Downloading {model}")
    SentenceTransformer(model)

nltk.download("stopwords")

print("All models downloaded successfully.")
