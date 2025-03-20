from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from natural_language_query import handle_query

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