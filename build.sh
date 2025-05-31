#!/usr/bin/env bash

# Step 1: Install Python packages from requirements.txt
pip install -r requirements.txt

# Step 2: Make nltk_data directory
mkdir -p nltk_data

# Step 3: Download TextBlob corpora
python3 -m textblob.download_corpora

# Step 4: Download NLTK corpora
python3 -m nltk.downloader -d ./nltk_data punkt averaged_perceptron_tagger wordnet brown movie_reviews

