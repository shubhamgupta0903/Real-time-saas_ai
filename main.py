from fastapi import FastAPI, Depends, HTTPException
from bson import ObjectId
from bson.errors import InvalidId
from db import collection, users_collection
from auth import create_access_token, verify_token
from models import Component, User
from services import generate_component
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI()

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register authentication router
from auth import router as auth_router
app.include_router(auth_router)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Register a new user
@app.post("/register/")
async def register_user(user: User):
    existing_user = await users_collection.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    hashed_password = pwd_context.hash(user.password)
    await users_collection.insert_one({"username": user.username, "password": hashed_password})
    
    return {"message": "User registered successfully"}

# User login and token generation
@app.post("/login/")
async def login_user(user: User):
    db_user = await users_collection.find_one({"username": user.username})
    if not db_user or not pwd_context.verify(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

# Model for AI component request
from pydantic import BaseModel

class PromptRequest(BaseModel):
    prompt: str

# Generate AI component and store it in MongoDB
@app.post("/generate_component/")
async def generate_saas_component(
    request: PromptRequest, user: dict = Depends(verify_token)
):
    ai_response = generate_component(request.prompt)

    if isinstance(ai_response, dict) and "error" in ai_response:
        raise HTTPException(status_code=500, detail=ai_response["error"])

    # Convert response to a dictionary format
    try:
        ai_response = json.loads(ai_response) if isinstance(ai_response, str) else ai_response
    except json.JSONDecodeError:
        ai_response = {"content": ai_response}  # Store as dict with key "content"

    component_data = {
        "component": ai_response,
        "owner": user["sub"],
        "pinned": False
    }

    await collection.insert_one(component_data)

    return {
        "message": "AI-generated component saved!",
        "component": ai_response
    }

# Retrieve components for the logged-in user
@app.get("/components/")
async def get_user_components(user: dict = Depends(verify_token)):
    user_components = await collection.find({"owner": user["sub"]}).to_list(None)

    for component in user_components:
        component["_id"] = str(component["_id"])  # Convert ObjectId to string

        # Ensure component["component"] is a dictionary
        if isinstance(component["component"], str):
            try:
                component["component"] = json.loads(component["component"])
            except json.JSONDecodeError:
                component["component"] = {"content": component["component"]}  # Wrap in a dict

        # Extract "content" field safely
        component["content"] = component["component"].get("content", None)
        

    return {"components": user_components}

# Pin a component
@app.put("/components/{component_id}/pin")
async def pin_component(component_id: str, user: dict = Depends(verify_token)):
    try:
        object_id = ObjectId(component_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid component ID format")

    result = await collection.update_one(
        {"_id": object_id, "owner": user["sub"]}, {"$set": {"pinned": True}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Component not found")
    
    return {"message": "Component pinned", "component_id": component_id}

# Delete a component
@app.delete("/components/{component_id}")
async def delete_component(component_id: str, user: dict = Depends(verify_token)):
    try:
        object_id = ObjectId(component_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid component ID format")

    result = await collection.delete_one({"_id": object_id, "owner": user["sub"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Component not found")
    
    return {"message": "Component deleted", "component_id": component_id}

# Logout and remove unpinned components
@app.post("/logout/")
async def logout_user(user: dict = Depends(verify_token)):
    await collection.delete_many({"owner": user["sub"], "pinned": False})
    return {"message": "Unpinned components removed on logout"}
