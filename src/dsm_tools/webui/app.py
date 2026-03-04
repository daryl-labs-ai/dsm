#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DARYL Web UI - Interface d'inspection pour Sharding Memory
Migrated from webui/app.py (buralux/dsm).
"""

import sys
from pathlib import Path

from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Add src to path so dsm_kernel and dsm_modules are importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from dsm_modules.dsm_router.router import ShardRouter
except ImportError as e:
    print(f"❌ Erreur import ShardRouter: {e}")
    ShardRouter = None

app = FastAPI(title="DARYL Web UI", version="0.1")

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

try:
    if ShardRouter:
        daryl = ShardRouter()
        print(f"✅ DARYL ShardRouter initialisé ({len(daryl.shards)} shards)")
    else:
        daryl = None
        print("⚠️ ShardRouter non disponible (import échoué)")
except Exception as e:
    print(f"❌ Erreur initialisation ShardRouter: {e}")
    daryl = None


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/stats")
def stats():
    if not daryl:
        return {"error": "DARYL ShardRouter non disponible"}
    if hasattr(daryl, "get_all_shards_status"):
        try:
            shards_status = daryl.get_all_shards_status()
            total_transactions = sum(s["transactions_count"] for s in shards_status)
            total_importance = sum(s["importance_score"] * s["transactions_count"] for s in shards_status)
            return {
                "total_shards": len(shards_status),
                "total_transactions": total_transactions,
                "total_importance": round(total_importance, 2),
                "shards": shards_status,
                "daryl_status": {
                    "active": daryl is not None,
                    "shards_loaded": len(daryl.shards) if daryl else 0
                }
            }
        except Exception as e:
            return {"error": f"Erreur récupération stats: {e}"}
    return {"error": "Méthode get_all_shards_status() non trouvée"}


@app.get("/shards")
def shards():
    if not daryl:
        return {"error": "DARYL ShardRouter non disponible"}
    try:
        shards_list = daryl.list_shards()
        return {"shards": shards_list, "total": len(shards_list)}
    except Exception as e:
        return {"error": f"Erreur liste shards: {e}"}


@app.get("/shard/{shard_id}")
def shard_detail(shard_id: str):
    if not daryl:
        return {"error": "DARYL ShardRouter non disponible"}
    try:
        shard = daryl.get_shard_by_id(shard_id)
        if not shard:
            return {"error": f"Shard {shard_id} introuvable"}
        shard_data = shard.to_dict()
        transactions = shard_data.get("transactions", [])
        return {
            "shard": shard_data,
            "transactions_count": len(transactions),
            "transactions_preview": transactions[:5]
        }
    except Exception as e:
        return {"error": f"Erreur récupération shard: {e}"}


@app.get("/search")
def search(q: str = Query(..., min_length=1), min_score: float = 0.0, top_k: int = 5):
    if not daryl:
        return {"error": "DARYL ShardRouter non disponible"}
    if not q:
        return {"error": "Paramètre q requis"}
    try:
        if hasattr(daryl, "semantic_search"):
            results = daryl.semantic_search(q, threshold=min_score, top_k=top_k)
        else:
            return {"error": "Méthode semantic_search() non disponible"}
        return {"query": q, "min_score": min_score, "top_k": top_k, "results": results, "total_results": len(results)}
    except Exception as e:
        return {"error": f"Erreur recherche: {e}"}


@app.get("/hybrid")
def hybrid(q: str = Query(..., min_length=1), min_score: float = 0.0, top_k: int = 5):
    if not daryl:
        return {"error": "DARYL ShardRouter non disponible"}
    if not q:
        return {"error": "Paramètre q requis"}
    try:
        if hasattr(daryl, "hybrid_search"):
            results = daryl.hybrid_search(q, threshold=min_score, top_k=top_k)
        else:
            return {"error": "Méthode hybrid_search() non disponible"}
        return {"query": q, "min_score": min_score, "top_k": top_k, "results": results, "total_results": len(results)}
    except Exception as e:
        return {"error": f"Erreur recherche hybride: {e}"}


@app.get("/compress")
def compress():
    if not daryl:
        return {"error": "DARYL ShardRouter non disponible"}
    try:
        if hasattr(daryl, "compress_memory"):
            compression_results = daryl.compress_memory(shard_id=None, force=False)
        else:
            return {"error": "Méthode compress_memory() non disponible"}
        return {"compression_results": compression_results, "timestamp": str(Path(__file__).stat().st_mtime)}
    except Exception as e:
        return {"error": f"Erreur compression: {e}"}


@app.get("/cleanup")
def cleanup():
    if not daryl:
        return {"error": "DARYL ShardRouter non disponible"}
    try:
        if hasattr(daryl, "cleanup_expired"):
            cleanup_results = daryl.cleanup_expired(shard_id=None, dry_run=True)
        else:
            return {"error": "Méthode cleanup_expired() non disponible"}
        return {"cleanup_results": cleanup_results, "timestamp": str(Path(__file__).stat().st_mtime)}
    except Exception as e:
        return {"error": f"Erreur nettoyage TTL: {e}"}


@app.get("/docs")
def docs():
    return {
        "title": "DARYL Web UI API Documentation",
        "version": "0.1",
        "endpoints": {
            "GET /": "Page d'accueil avec formulaire de recherche",
            "GET /stats": "Statistiques globales de DARYL",
            "GET /shards": "Liste de tous les shards",
            "GET /shard/{id}": "Détails d'un shard spécifique",
            "GET /search": "Recherche sémantique (q, min_score, top_k)",
            "GET /hybrid": "Recherche hybride (q, min_score, top_k)",
            "GET /compress": "Compression de mémoire",
            "GET /cleanup": "Nettoyage TTL",
            "GET /docs": "Documentation API"
        }
    }


if __name__ == "__main__":
    import uvicorn
    print("🚀 DARYL Web UI - Démarrage du serveur FastAPI")
    print("📍 Dashboard: http://localhost:8000/")
    uvicorn.run("dsm_tools.webui.app:app", host="0.0.0.0", port=8000, reload=True)
