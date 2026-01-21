from fastapi import FastAPI
from app.services.prediction import predict_today, get_persisted_predictions_today
from app.services.ranking import rank_predictions
from app.services.analysis import analyze_predictions, get_top_picks

app = FastAPI(title="Foo Ball Bot")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/predictions/today")
def get_predictions_today():
    """Get all predictions for today with ranking"""
    top_predictions = predict_today()
    return {
        "count": len(top_predictions),
        "predictions": top_predictions
    }

@app.get("/predictions/analysis")
def get_predictions_analysis():
    """Get enhanced analysis of today's predictions with pandas insights"""
    all_predictions = get_persisted_predictions_today()
    analysis = analyze_predictions(all_predictions)
    return analysis

@app.get("/predictions/top-picks")
def get_predictions_top_picks(limit: int = 10):
    """Get top picks based on composite scoring"""
    all_predictions = get_persisted_predictions_today()
    top_picks = get_top_picks(all_predictions, limit=limit)
    return {
        "count": len(top_picks),
        "top_picks": top_picks
    }
