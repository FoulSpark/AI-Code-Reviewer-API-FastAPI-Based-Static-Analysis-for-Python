import json
from fastapi import FastAPI , HTTPException
from app.Schema.review import ReviewRequest , syntax
from app.Schema.agentic import GenerateRequest, FixRequest, AgenticResponse
from app.Services.review_engine import to_review
from app.Services.agentic_pipeline import run_agentic_task
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

@app.post("/generate", response_model=AgenticResponse)
async def generate_code(request: GenerateRequest):
    try:
        response = await run_agentic_task(
            request.user_request, 
            task_type="generate", 
            force_run=request.force_run
        )
        return response
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fix", response_model=AgenticResponse)
async def fix_code(request: FixRequest):
    try:
        response = await run_agentic_task(
            user_request="", 
            task_type="fix", 
            original_code=request.code, 
            original_issues=request.issues,
            force_run=request.force_run
        )
        return response
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reviews/{review_id}")
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


