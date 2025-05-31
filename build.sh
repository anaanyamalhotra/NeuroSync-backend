#!/usr/bin/env bash
mkdir -p nltk_data
python3 -m textblob.download_corpora
python3 -m nltk.downloader -d ./nltk_data punkt averaged_perceptron_tagger wordnet brown movie_reviews
