"""
Project initialization models for API.
"""

from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, validator
from pathlib import Path


class ProjectInitRequest(BaseModel):
    """Request to initialize a project."""
    project_path: str = Field(..., description="Absolute path to the project directory")
    
    @validator('project_path')
    def validate_path(cls, v):
        """Validate the project path exists and is a directory."""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Path does not exist: {v}")
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {v}")
        return str(path.resolve())


class ProjectStatus(str):
    """Project initialization status."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    INDEXING = "indexing"
    READY = "ready"
    ERROR = "error"


class ProjectInfo(BaseModel):
    """Information about an initialized project."""
    project_path: str
    project_name: str
    status: str
    indexed_files: Optional[int] = None
    total_chunks: Optional[int] = None
    last_indexed: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProjectInitResponse(BaseModel):
    """Response for project initialization."""
    success: bool
    message: str
    project: Optional[ProjectInfo] = None
    

class DirectoryBrowseRequest(BaseModel):
    """Request to browse directories."""
    path: Optional[str] = Field(None, description="Starting path for browsing")
    show_hidden: bool = Field(False, description="Show hidden files/directories")


class DirectoryEntry(BaseModel):
    """Single directory entry."""
    name: str
    path: str
    is_directory: bool
    size: Optional[int] = None
    modified: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DirectoryBrowseResponse(BaseModel):
    """Response for directory browsing."""
    current_path: str
    parent_path: Optional[str] = None
    entries: List[DirectoryEntry]
    can_write: bool = True