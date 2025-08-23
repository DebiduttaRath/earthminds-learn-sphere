from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from services.document_service import document_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class DocumentIngestRequest(BaseModel):
    title: str
    content: str
    source: str
    subject: str
    grade_level: str
    document_type: str = "textbook"
    metadata: Optional[Dict[str, Any]] = None


class BulkIngestRequest(BaseModel):
    documents: List[DocumentIngestRequest]


class DocumentUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DocumentSearchRequest(BaseModel):
    query: str
    subject: Optional[str] = None
    grade_level: Optional[str] = None
    limit: int = 10


@router.post("/ingest")
async def ingest_document(
    request: DocumentIngestRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Ingest a single document for vector search"""
    try:
        if not request.title.strip():
            raise HTTPException(status_code=400, detail="Document title cannot be empty")
        
        if not request.content.strip():
            raise HTTPException(status_code=400, detail="Document content cannot be empty")
        
        if len(request.content) < 50:
            raise HTTPException(status_code=400, detail="Document content too short (minimum 50 characters)")
        
        result = await document_service.ingest_document(
            title=request.title.strip(),
            content=request.content.strip(),
            source=request.source,
            subject=request.subject,
            grade_level=request.grade_level,
            document_type=request.document_type,
            metadata=request.metadata
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "status": "success",
            "message": "Document ingested successfully",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting document: {e}")
        raise HTTPException(status_code=500, detail="Failed to ingest document")


@router.post("/bulk-ingest")
async def bulk_ingest_documents(
    request: BulkIngestRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Bulk ingest multiple documents"""
    try:
        if not request.documents:
            raise HTTPException(status_code=400, detail="No documents provided")
        
        if len(request.documents) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 documents allowed per batch")
        
        # Convert to document service format
        documents_data = []
        for doc in request.documents:
            documents_data.append({
                "title": doc.title,
                "content": doc.content,
                "source": doc.source,
                "subject": doc.subject,
                "grade_level": doc.grade_level,
                "document_type": doc.document_type,
                "metadata": doc.metadata or {}
            })
        
        result = await document_service.bulk_ingest_documents(documents_data)
        
        return {
            "status": "success",
            "message": f"Processed {len(request.documents)} documents",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk ingest: {e}")
        raise HTTPException(status_code=500, detail="Failed to bulk ingest documents")


@router.post("/search")
async def search_documents(
    request: DocumentSearchRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Search documents using vector similarity"""
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Search query cannot be empty")
        
        from services.vector_service import vector_service
        
        results = await vector_service.search_similar_documents(
            query=request.query.strip(),
            subject=request.subject,
            grade_level=request.grade_level,
            limit=request.limit
        )
        
        return {
            "query": request.query,
            "results": results,
            "count": len(results),
            "filters": {
                "subject": request.subject,
                "grade_level": request.grade_level
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to search documents")


@router.get("/list")
async def list_documents(
    subject: Optional[str] = None,
    grade_level: Optional[str] = None,
    source: Optional[str] = None,
    document_type: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db_session)
):
    """List documents with optional filters"""
    try:
        if limit > 100:
            raise HTTPException(status_code=400, detail="Maximum limit is 100")
        
        documents = await document_service.search_documents(
            subject=subject,
            grade_level=grade_level,
            source=source,
            document_type=document_type,
            limit=limit
        )
        
        return {
            "documents": documents,
            "count": len(documents),
            "filters": {
                "subject": subject,
                "grade_level": grade_level,
                "source": source,
                "document_type": document_type,
                "limit": limit
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific document by ID"""
    try:
        result = await document_service.get_document(document_id)
        
        if "error" in result:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document")


@router.put("/{document_id}")
async def update_document(
    document_id: str,
    request: DocumentUpdateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Update a document"""
    try:
        if not any([request.title, request.content, request.metadata]):
            raise HTTPException(status_code=400, detail="At least one field must be provided for update")
        
        result = await document_service.update_document(
            document_id=document_id,
            title=request.title,
            content=request.content,
            metadata=request.metadata
        )
        
        if "error" in result:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "status": "success",
            "message": "Document updated successfully",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating document: {e}")
        raise HTTPException(status_code=500, detail="Failed to update document")


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a document and its chunks"""
    try:
        result = await document_service.delete_document(document_id)
        
        if "error" in result:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "status": "success",
            "message": "Document deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.get("/statistics/overview")
async def get_document_statistics(
    db: AsyncSession = Depends(get_db_session)
):
    """Get statistics about ingested documents"""
    try:
        stats = await document_service.get_document_statistics()
        
        if "error" in stats:
            raise HTTPException(status_code=500, detail=stats["error"])
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document statistics")


@router.post("/upload")
async def upload_document_file(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    source: str = "upload",
    subject: str = "general",
    grade_level: str = "unspecified",
    document_type: str = "textbook",
    db: AsyncSession = Depends(get_db_session)
):
    """Upload and ingest a document file"""
    try:
        # Validate file type
        allowed_types = ["text/plain", "application/pdf", "text/markdown"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Allowed types: {', '.join(allowed_types)}"
            )
        
        # Read file content
        content = await file.read()
        
        # Handle different file types
        if file.content_type == "text/plain":
            text_content = content.decode("utf-8")
        elif file.content_type == "text/markdown":
            text_content = content.decode("utf-8")
        elif file.content_type == "application/pdf":
            # For PDF, you would need a PDF parsing library like PyPDF2 or pdfplumber
            # For now, return an error message
            raise HTTPException(
                status_code=400,
                detail="PDF processing not implemented. Please convert to text format."
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        # Use filename as title if not provided
        document_title = title or file.filename or "Untitled Document"
        
        # Ingest the document
        result = await document_service.ingest_document(
            title=document_title,
            content=text_content,
            source=source,
            subject=subject,
            grade_level=grade_level,
            document_type=document_type,
            metadata={
                "filename": file.filename,
                "file_size": len(content),
                "content_type": file.content_type,
                "upload_method": "file_upload"
            }
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "status": "success",
            "message": f"File '{file.filename}' uploaded and ingested successfully",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document file: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload and ingest document file")


@router.get("/subjects/list")
async def get_available_subjects(
    db: AsyncSession = Depends(get_db_session)
):
    """Get list of available subjects from ingested documents"""
    try:
        from sqlalchemy import select, distinct
        from models import Document
        
        query = select(distinct(Document.subject)).where(Document.subject.isnot(None))
        result = await db.execute(query)
        subjects = [row[0] for row in result.fetchall()]
        
        return {
            "subjects": sorted(subjects),
            "count": len(subjects)
        }
        
    except Exception as e:
        logger.error(f"Error getting subjects: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve subjects")


@router.get("/grades/list")
async def get_available_grade_levels(
    db: AsyncSession = Depends(get_db_session)
):
    """Get list of available grade levels from ingested documents"""
    try:
        from sqlalchemy import select, distinct
        from models import Document
        
        query = select(distinct(Document.grade_level)).where(Document.grade_level.isnot(None))
        result = await db.execute(query)
        grade_levels = [row[0] for row in result.fetchall()]
        
        return {
            "grade_levels": sorted(grade_levels),
            "count": len(grade_levels)
        }
        
    except Exception as e:
        logger.error(f"Error getting grade levels: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve grade levels")
