# vector_store.py
import faiss
import numpy as np
import os
import json
import hashlib
from datetime import datetime

VECTOR_DIM = 5  # dopamine, serotonin, oxytocin, GABA, cortisol
INDEX_PATH = "vector_store/faiss_index.index"
META_PATH = "vector_store/metadata.json"

os.makedirs("vector_store", exist_ok=True)

# === Load or create index ===
def load_index():
    if os.path.exists(INDEX_PATH):
        return faiss.read_index(INDEX_PATH)
    return faiss.IndexFlatL2(VECTOR_DIM)

# === Save index ===
def save_index(index):
    faiss.write_index(index, INDEX_PATH)

# === Load metadata ===
def load_metadata():
    if os.path.exists(META_PATH):
        with open(META_PATH, "r") as f:
            metadata = json.load(f)
        updated = False
        clean_metadata = []
        for entry in metadata:
            if not isinstance(entry, dict):
                continue
            if "timestamp" not in entry:
                entry["timestamp"] = datetime.utcnow().isoformat()
                updated = True
            clean_metadata.append(entry)
        if updated:
            save_metadata(clean_metadata)
        return clean_metadata
    return []

# === Save metadata ===
def save_metadata(metadata):
    with open(META_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

# === Add new twin to store ===
def add_twin(twin, vector=None):
    index = load_index()
    metadata = load_metadata()

    if vector is None:
        vector = np.array([[
            twin["neurotransmitters"]["dopamine"],
            twin["neurotransmitters"]["serotonin"],
            twin["neurotransmitters"]["oxytocin"],
            twin["neurotransmitters"]["GABA"],
            twin["neurotransmitters"]["cortisol"]
        ]], dtype='float32')
    
    index.add(vector)
    
    user_id = hashlib.sha256(twin["name"].encode()).hexdigest()[:8]
    metadata.append({
        "name": twin["name"],
        "gender": twin["gender"],
        "life_stage": twin["life_stage"],
        "age_range": twin["age_range"],
        "neurotransmitters": twin.get("neurotransmitters"),
        "timestamp": twin.get("timestamp", datetime.utcnow().isoformat()),
        "vector_id": len(metadata),
        "user_id": user_id
    })

    save_index(index)
    save_metadata(metadata)

# === Search for similar twins ===
def search_similar_twins(query_vector, top_k=5, filters=None):
    index = load_index()
    metadata = load_metadata()

    query = np.array([[
        query_vector["dopamine"],
        query_vector["serotonin"],
        query_vector["oxytocin"],
        query_vector["GABA"],
        query_vector["cortisol"]
    ]], dtype='float32')

    if index.ntotal == 0:
        return []

    distances, indices = index.search(query, top_k)

    similar = []
    for i, idx in enumerate(indices[0]):
        if idx >= len(metadata):
            continue
        entry = metadata[idx]
        if filters:
            match = all(entry.get(k) == v for k, v in filters.items())
            if not match:
                continue
        entry["distance"] = float(distances[0][i])
        similar.append(entry)
    return similar

