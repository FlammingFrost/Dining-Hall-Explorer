import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from natural_language_query import handle_query
import subprocess

app = FastAPI()

# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve index.html when accessing the root URL
@app.get("/")
def read_root():
    return FileResponse("static/index.html")

class QueryRequest(BaseModel):
    query: str

@app.post("/query")
def query_api(request: QueryRequest):
    response = handle_query(request.query)
    print(f"Response: {response}")
    return {"answer": response}

@app.post("/update-database")
def update_database():
    try:
        result = subprocess.run(["python3", "daily_update.py"], capture_output=True, text=True)
        return {"status": "success", "output": result.stdout}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Ensure FastAPI runs on Cloud Run's required port
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)