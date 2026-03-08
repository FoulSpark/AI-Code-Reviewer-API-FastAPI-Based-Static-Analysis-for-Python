import json
from fastapi import FastAPI , HTTPException
from app.Schema.review import ReviewRequest , syntax
from app.Services.review_engine import to_review
from app.db.storage import init_db , save_review ,get_review_by_id
app = FastAPI()




@app.on_event("startup")
def startup_event():
    init_db()

@app.post("/review",response_model=syntax)
def review_code(code:ReviewRequest):
    review = to_review(code.code)
    save_review(code.code,review)
    return review


@app.get("/review/{review_by_ID}")
def get_review(review_id:str):
    row = get_review_by_id(review_id)

    if not row:
        raise HTTPException(status_code=404,detail="Review Not Found")
    
    return {
        "review_id": row["review_id"],
        "status": row["status"],
        "overall_score": row["overall_score"],
        "summary": row["summary"],
        "issues": json.loads(row["issues_json"]),
        "metrics": json.loads(row["metrics_json"]),
        "submitted_code": row["submitted_code"],
        "created_at": row["created_at"]
    }


