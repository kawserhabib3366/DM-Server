from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.email_apis import router as email_router 
from routes.gvoice_api import router as gvoice_router 
import os 




app = FastAPI()

# Add CORS middleware (if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust origins as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],              
)

# Include the email router
app.include_router(email_router, prefix="/api", tags=["Email"])

app.include_router(gvoice_router, prefix="/api", tags=["Tasks"])

@app.get("/")
async def root():
    return {"message": "Welcome to the DM SERVER API!"}

@app.get("/api/test")
async def test():
    return {"message": "API working fine"}