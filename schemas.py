"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List

# Portfolio-specific schemas

class Project(BaseModel):
    """
    Projects collection schema
    Collection name: "project"
    """
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Short description")
    stack: List[str] = Field(default_factory=list, description="Technologies used")
    github: Optional[str] = Field(None, description="GitHub URL")
    live: Optional[str] = Field(None, description="Live URL if any")
    featured: bool = Field(False, description="Whether to feature on homepage")
    order: int = Field(0, description="Sort order")

class Message(BaseModel):
    """
    Messages collection schema
    Collection name: "message"
    """
    name: str = Field(..., description="Sender name")
    email: EmailStr = Field(..., description="Sender email")
    message: str = Field(..., description="Message body")

# Example schemas (kept for reference)
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = None
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
