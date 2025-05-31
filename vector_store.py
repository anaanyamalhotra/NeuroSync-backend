# vector_store.py
import faiss
import numpy as np
import os
import json
import hashlib

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
            return json.load(f)
    return []

# === Save metadata ===
def save_metadata(metadata):
    with open(META_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

# === Add new twin ===
def add_twin(twin, vector):
    index = load_index()
    metadata = load_metadata()

    np_vec = np.array([[
        twin["neurotransmitters"]["dopamine"],
        twin["neurotransmitters"]["serotonin"],
        twin["neurotransmitters"]["oxytocin"],
        twin["neurotransmitters"]["GABA"],
        twin["neurotransmitters"]["cortisol"]
    ]], dtype='float32')

    email_hash = hashlib.sha256(twin["name"].encode()).hexdigest()[:8]

    index.add(np_vec)
    metadata.append({
        "name": twin["name"],
        "gender": twin["gender"],
        "life_stage": twin["life_stage"],
        "timestamp": twin["timestamp"],
        "vector_id": len(metadata)
        "user_id": email_hash
    })

    save_index(index)
    save_metadata(metadata)
