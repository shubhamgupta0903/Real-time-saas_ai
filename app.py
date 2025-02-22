from fastapi import FastAPI, Depends, HTTPException
from bson import ObjectId
from db import collection, users_collection
from auth import create_access_token, verify_token
from models import Component, User
from services import generate_component
from passlib.context import CryptContext

app = FastAPI()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Register User
@app.post("/register/")
async def register_user(user: User):
    existing_user = await users_collection.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    hashed_password = pwd_context.hash(user.password)
    await users_collection.insert_one({"username": user.username, "password": hashed_password})
    
    return {"message": "User registered successfully"}

# Login User & Generate Token
@app.post("/login/")
async def login_user(user: User):
    db_user = await users_collection.find_one({"username": user.username})
    if not db_user or not pwd_context.verify(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

# Generate AI Component
@app.post("/generate_component/")
async def generate_saas_component(prompt: str, user: dict = Depends(verify_token)):
    ai_response = generate_component(prompt)

    # Extract the AI-generated content
    content = ai_response["choices"][0]["message"]["content"]

    component_data = {
        "component": {"content": content},
        "owner": user["sub"],
        "pinned": False,
    }
    
    result = await collection.insert_one(component_data)

    return {
        "message": "AI-generated component saved!",
        "component": {
            "id": str(result.inserted_id),  # Convert ObjectId to string
            "content": content,
        },
    }

# Get User Components
@app.get("/components/")
async def get_user_components(user: dict = Depends(verify_token)):
    user_components = await collection.find({"owner": user["sub"]}).to_list(None)

    for component in user_components:
        component["_id"] = str(component["_id"])  # Convert ObjectId to string
        if "component" in component and "content" in component["component"]:
            component["content"] = component["component"]["content"]
        else:
            component["content"] = None  # Handle missing content gracefully
    
    return {"components": user_components}

# Pin a Component
@app.put("/components/{component_id}/pin")
async def pin_component(component_id: str, user: dict = Depends(verify_token)):
    result = await collection.update_one(
        {"_id": ObjectId(component_id), "owner": user["sub"]}, {"$set": {"pinned": True}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Component not found")
    return {"message": "Component pinned", "component_id": component_id}

# Delete AI-Generated Component
@app.delete("/components/{component_id}")
async def delete_component(component_id: str, user: dict = Depends(verify_token)):
    result = await collection.delete_one({"_id": ObjectId(component_id), "owner": user["sub"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Component not found")
    return {"message": "Component deleted", "component_id": component_id}

# Remove all unpinned components on logout
@app.post("/logout/")
async def logout_user(user: dict = Depends(verify_token)):
    await collection.delete_many({"owner": user["sub"], "pinned": False})
    return {"message": "Unpinned components removed on logout"}
