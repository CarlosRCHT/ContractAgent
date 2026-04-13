import os
import logging
from docx import Document
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.models.schemas import (
    RedlineRequest, RedlineResponse, ChangeResult,
    ExtractTextRequest, ExtractTextResponse,
)
from app.services.graph_client import graph_client, GraphClientError
from app.services.redline_engine import RedlineEngine
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Redline"])


@router.post(
    "/redline",
    response_model=RedlineResponse,
    summary="Redline a contract with tracked changes",
    description=(
        "Downloads a Word document from SharePoint, applies tracked changes "
        "(insertions/deletions) based on the provided recommendations, adds "
        "Word comments with rationale for each change, and uploads the "
        "redlined document back to SharePoint."
    ),
    responses={
        200: {"description": "Document redlined successfully"},
        400: {"description": "Invalid request"},
        502: {"description": "SharePoint communication error"},
        500: {"description": "Internal processing error"},
    },
)
async def redline_document(request: RedlineRequest) -> RedlineResponse:
    """
    Main endpoint called by Copilot Studio to redline a contract.

    Flow:
    1. Download the Word document from SharePoint via Graph API
    2. Apply tracked changes (w:del/w:ins) for each recommendation
    3. Add Word comments with rationale for each change
    4. Upload the redlined document back to SharePoint
    5. Return results with the URL to the new document
    """
    local_path = ""
    output_path = ""

    try:
        # 1. Download from SharePoint
        logger.info(f"Downloading document from: {request.document_url}")
        try:
            local_path = await graph_client.download_file(request.document_url)
        except GraphClientError as e:
            logger.error(f"SharePoint download failed: {e}")
            raise HTTPException(status_code=502, detail=f"Failed to download document from SharePoint: {e}")

        # 2. Apply redline changes
        logger.info(f"Applying {len(request.recommendations)} changes to document")
        try:
            engine = RedlineEngine(local_path)
        except Exception as e:
            logger.error(f"Failed to open document: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to open Word document: {e}")

        author = request.author or settings.default_author
        recommendations = [
            {
                "original_text": rec.original_text,
                "replacement_text": rec.replacement_text,
                "rationale": rec.rationale,
                "risk_level": rec.risk_level.value,
                "section": rec.section,
            }
            for rec in request.recommendations
        ]

        results = engine.apply_all_changes(recommendations, author=author)

        # 3. Save the redlined document locally
        output_filename = request.output_filename
        if not output_filename:
            if graph_client.is_sharing_link(request.document_url):
                resolved = await graph_client.resolve_sharing_link(request.document_url)
                name, ext = os.path.splitext(resolved["filename"])
            else:
                parsed = graph_client.parse_sharepoint_url(request.document_url)
                name, ext = os.path.splitext(parsed["filename"])
            output_filename = f"{name}_redlined{ext}"

        output_path = os.path.join(settings.temp_dir, output_filename)
        engine.save(output_path)

        # 4. Upload back to SharePoint
        logger.info(f"Uploading redlined document as: {output_filename}")
        try:
            output_url = await graph_client.upload_file(
                output_path, request.document_url, output_filename,
                output_folder_url=request.output_folder_url,
            )
        except GraphClientError as e:
            logger.error(f"SharePoint upload failed: {e}")
            raise HTTPException(status_code=502, detail=f"Failed to upload redlined document: {e}")

        # 5. Build response
        change_results = [
            ChangeResult(
                original_text=r.original_text,
                replacement_text=r.replacement_text,
                applied=r.applied,
                comment_added=r.comment_added,
                error=r.error,
            )
            for r in results
        ]

        applied = sum(1 for r in results if r.applied)
        failed = sum(1 for r in results if not r.applied)
        comments = sum(1 for r in results if r.comment_added)

        if failed == 0:
            status = "success"
        elif applied > 0:
            status = "partial"
        else:
            status = "error"

        summary = (
            f"Applied {applied}/{len(results)} tracked changes with "
            f"{comments} rationale comments. "
        )
        if failed > 0:
            failed_texts = [r.original_text[:40] for r in results if not r.applied]
            summary += f"{failed} changes could not be applied (text not found): {', '.join(failed_texts)}"

        response = RedlineResponse(
            status=status,
            output_url=output_url,
            changes_applied=applied,
            changes_failed=failed,
            comments_added=comments,
            results=change_results,
            summary=summary,
        )
        return JSONResponse(content=response.model_dump(by_alias=True, mode="json"))

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during redline: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")

    finally:
        # Clean up temp files
        if local_path:
            graph_client.cleanup_temp_file(local_path)
        if output_path:
            graph_client.cleanup_temp_file(output_path)


@router.post(
    "/extract-text",
    response_model=ExtractTextResponse,
    summary="Extract plain text from a Word document",
    description=(
        "Downloads a Word document from SharePoint and extracts all "
        "paragraph text as a single plain-text string."
    ),
    responses={
        200: {"description": "Text extracted successfully"},
        400: {"description": "Invalid request"},
        502: {"description": "SharePoint communication error"},
        500: {"description": "Internal processing error"},
    },
)
async def extract_text(request: ExtractTextRequest) -> JSONResponse:
    """Download a Word document from SharePoint and return its plain text."""
    local_path = ""

    try:
        # 1. Download from SharePoint
        logger.info(f"Downloading document for text extraction: {request.document_url}")
        try:
            local_path = await graph_client.download_file(request.document_url)
        except GraphClientError as e:
            logger.error(f"SharePoint download failed: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Failed to download document from SharePoint: {e}",
            )

        # 2. Extract text
        try:
            doc = Document(local_path)
        except Exception as e:
            logger.error(f"Failed to open document: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to open Word document: {e}")

        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n".join(paragraphs)

        # Resolve filename
        if graph_client.is_sharing_link(request.document_url):
            resolved = await graph_client.resolve_sharing_link(request.document_url)
            filename = resolved["filename"]
        else:
            parsed = graph_client.parse_sharepoint_url(request.document_url)
            filename = parsed["filename"]

        response = ExtractTextResponse(
            status="success",
            filename=filename,
            text=text,
            page_count=max(1, len(paragraphs) // 25),
        )
        return JSONResponse(content=response.model_dump(by_alias=True, mode="json"))

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during text extraction: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")

    finally:
        if local_path:
            graph_client.cleanup_temp_file(local_path)
