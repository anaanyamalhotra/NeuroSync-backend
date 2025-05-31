#!/bin/bash

echo "Installing requirements..."
pip install -r requirements.txt

echo "Downloading TextBlob corpora..."
python -m textblob.download_corpora

echo "Build completed."
