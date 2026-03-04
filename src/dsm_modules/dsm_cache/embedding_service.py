#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EmbeddingService - Service d'embeddings pour DARYL Sharding Memory
Migrated from embedding_service.py (buralux/dsm).
"""

import json
import hashlib
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Union

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class DummyModel:
    """Modèle factice pour les tests (évite le téléchargement)"""

    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.dimension = 384

    def encode(self, texts, convert_to_numpy=True, normalize_embeddings=False, **kwargs):
        if isinstance(texts, str):
            texts = [texts]
        embeddings = []
        for text in texts:
            s = sum(ord(c) for c in text.strip().lower()) % 1000
            arr = []
            for i in range(384):
                np.random.seed(s + i * 1000)
                val = (np.random.rand() - 0.5) * 2.0
                arr.append(val)
            embeddings.append(arr)
        return np.array(embeddings, dtype=np.float32)


class EmbeddingService:
    """Service pour générer et mettre en cache des embeddings"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", model: Optional[Union[str, DummyModel]] = None):
        self.model_name = model_name
        self.model = model
        self.cache = {}
        self._real_model = None
        self._dimension = 384
        print(f"✅ EmbeddingService initialisé (model_name: {model_name})")

    def _get_model(self):
        if self.model is not None:
            return self.model
        if self._real_model is not None:
            return self._real_model
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            print("⚠️ sentence-transformers non disponible. Utilisation DummyModel.")
            self.model = DummyModel(self.model_name)
            self._real_model = self.model
            self._dimension = self.model.dimension
            return self.model
        try:
            print(f"📥 Chargement du modèle réel: {self.model_name}")
            self._real_model = SentenceTransformer(self.model_name)
            self._dimension = self._real_model.get_sentence_embedding_dimension()
            print(f"✅ Modèle réel chargé: {self.model_name} (dimension: {self._dimension})")
            return self._real_model
        except Exception as e:
            print(f"❌ Erreur chargement modèle réel: {e}")
            print("⚠️ Utilisation DummyModel en cas d'échec.")
            self.model = DummyModel(self.model_name)
            self._real_model = self.model
            self._dimension = self.model.dimension
            return self.model

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        text_hash = self._hash_text(text)
        if text_hash in self.cache:
            return self.cache[text_hash]
        try:
            model = self._get_model()
            embedding = model.encode(text, convert_to_numpy=False)
            if hasattr(embedding, 'tolist'):
                embedding = embedding.tolist()
            elif isinstance(embedding, np.ndarray):
                embedding = embedding.tolist()
            # Single text may return batch of 1
            if isinstance(embedding, list) and len(embedding) == 1 and isinstance(embedding[0], list):
                embedding = embedding[0]
            self.cache[text_hash] = embedding
            return embedding
        except Exception as e:
            print(f"❌ Erreur génération embedding: {e}")
            return None

    def batch_generate_embeddings(self, texts: List[str]) -> Dict[str, Optional[List[float]]]:
        results = {}
        try:
            model = self._get_model()
            embeddings = model.encode(texts, convert_to_numpy=False)
            if hasattr(embeddings, 'tolist'):
                embeddings = embeddings.tolist()
            elif isinstance(embeddings, np.ndarray):
                embeddings = embeddings.tolist()
            if isinstance(embeddings, list) and len(embeddings) > 0 and not isinstance(embeddings[0], list):
                embeddings = [embeddings]
            for text, embedding in zip(texts, embeddings):
                text_hash = self._hash_text(text)
                results[text_hash] = embedding
            return results
        except Exception as e:
            print(f"❌ Erreur génération batch: {e}")
            return {}

    def _hash_text(self, text: str) -> str:
        normalized = text.strip().lower()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def get_cache_stats(self) -> Dict[str, int]:
        return {
            "cache_size": len(self.cache),
            "model_name": self.model_name,
            "model_type": "DummyModel" if isinstance(self.model, DummyModel) else "SentenceTransformer",
            "embedding_dimension": self._dimension
        }

    def clear_cache(self):
        self.cache.clear()
        print("🗑️ Cache d'embeddings vidé")

    def save_cache_to_file(self, file_path: str):
        try:
            cache_serializable = {
                k: v.tolist() if hasattr(v, 'tolist') else v
                for k, v in self.cache.items()
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(cache_serializable, f, indent=2, ensure_ascii=False)
            print(f"✅ Cache sauvegardé dans {file_path}")
        except Exception as e:
            print(f"❌ Erreur sauvegarde cache: {e}")

    def load_cache_from_file(self, file_path: str):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            self.cache = cache_data
            print(f"✅ Cache chargé depuis {file_path} ({len(cache_data)} embeddings)")
        except Exception as e:
            print(f"❌ Erreur chargement cache: {e}")
