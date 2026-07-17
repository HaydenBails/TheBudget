"""Typed profile-nested TD statement import endpoints."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import load_or_create_import_fingerprint_key, settings
from app.db import get_session
from app.importing import DocumentLimits, stage_pdf_async
from app.importing.errors import (
    DocumentTooLargeError,
    ImportingError,
    UnsupportedDocumentError,
)
from app.parsers import resolve_parser
from app.schemas import (
    ImportCancelResponse,
    ImportCommitRequest,
    ImportCommitResponse,
    ImportDetailResponse,
    ImportErrorResponse,
    ImportNotFoundResponse,
    ImportPreviewResponse,
)
from app.services import (
    ImportAcknowledgementRequiredError,
    ImportConflictError,
    cancel_import,
    commit_import,
    preview_import,
    require_import_batch,
)

router = APIRouter(prefix="/profiles/{profile_id}/imports", tags=["imports"])
SessionDependency = Annotated[Session, Depends(get_session)]
logger = logging.getLogger("spending_tracker.imports")


def get_import_document_limits() -> DocumentLimits:
    """Construct validated document limits from local runtime settings."""

    return DocumentLimits(
        max_bytes=settings.import_max_bytes,
        max_pages=settings.import_max_pages,
        max_extracted_chars=settings.import_max_extracted_chars,
        extraction_timeout_seconds=settings.import_extraction_timeout_seconds,
    )


def get_import_fingerprint_key() -> bytes:
    """Return stable caller-owned HMAC key material without exposing it."""

    return load_or_create_import_fingerprint_key()


LimitsDependency = Annotated[DocumentLimits, Depends(get_import_document_limits)]
FingerprintKeyDependency = Annotated[bytes, Depends(get_import_fingerprint_key)]

_ERROR_RESPONSES = {
    status.HTTP_404_NOT_FOUND: {"model": ImportNotFoundResponse},
    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {"model": ImportErrorResponse},
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {"model": ImportErrorResponse},
    status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": ImportErrorResponse},
    status.HTTP_409_CONFLICT: {"model": ImportErrorResponse},
}


@router.post(
    "/preview",
    response_model=ImportPreviewResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_ERROR_RESPONSES,
)
async def post_import_preview(
    profile_id: int,
    session: SessionDependency,
    statements: Annotated[
        list[UploadFile],
        File(alias="statement", min_length=1, max_length=1),
    ],
    account_id: Annotated[int, Form(gt=0)],
    limits: LimitsDependency,
    fingerprint_key: FingerprintKeyDependency,
):
    """Safely stage one credit-card PDF (issuer auto-detected) and persist its preview."""

    statement = statements[0]
    temp_root = settings.import_temp_root
    if temp_root is not None:
        temp_root = temp_root.expanduser().resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
    try:
        async with stage_pdf_async(
            statement,
            filename=statement.filename or "statement.pdf",
            content_type=statement.content_type or "",
            limits=limits,
            temp_root=temp_root,
            logger=logger,
        ) as document:
            result = preview_import(
                session,
                profile_id,
                account_id,
                document,
                resolve_parser(document),
                fingerprint_key=fingerprint_key,
                logger=logger,
            )
        response = _preview_response(
            result.batch,
            suggested_account_id=result.suggested_account_id,
        )
        if result.batch.duplicate_decision in {
            "blocked_file_hash",
            "blocked_logical_key",
        }:
            return _error_response(
                status.HTTP_409_CONFLICT,
                detail="statement was already previewed or imported",
                code=result.batch.duplicate_decision,
                import_id=result.batch.id,
                duplicate_of_import_id=result.batch.duplicate_of_import_id,
                lifecycle_status=result.batch.status,
            )
        return response
    except DocumentTooLargeError as exc:
        return _error_response(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
            code=exc.code,
        )
    except UnsupportedDocumentError as exc:
        boundary_error = str(exc) in {
            "statement must use the .pdf extension",
            "statement content type must be application/pdf",
            "statement content is not a PDF",
        }
        return _error_response(
            (
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
                if boundary_error
                else status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=str(exc),
            code=exc.code,
        )
    except ImportingError as exc:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
            code=exc.code,
        )
    except ImportConflictError as exc:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
            code="invalid_statement_preview",
        )
    finally:
        await statement.close()


@router.get(
    "/{import_id}",
    response_model=ImportDetailResponse,
    responses={status.HTTP_404_NOT_FOUND: {"model": ImportNotFoundResponse}},
)
def get_import(
    profile_id: int,
    import_id: int,
    session: SessionDependency,
) -> ImportDetailResponse:
    """Return one structured import only within its owning profile."""

    return _detail_response(require_import_batch(session, profile_id, import_id))


@router.post(
    "/{import_id}/commit",
    response_model=ImportCommitResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ImportNotFoundResponse},
        status.HTTP_409_CONFLICT: {"model": ImportErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ImportErrorResponse},
    },
)
def post_import_commit(
    profile_id: int,
    import_id: int,
    values: ImportCommitRequest,
    session: SessionDependency,
):
    """Commit one preview while preserving terminal failure persistence."""

    try:
        result = commit_import(
            session,
            profile_id,
            import_id,
            acknowledge_needs_review=values.acknowledge_needs_review,
            logger=logger,
        )
    except ImportAcknowledgementRequiredError as exc:
        return _error_response(
            status.HTTP_409_CONFLICT,
            detail=str(exc),
            code="acknowledgement_required",
            import_id=import_id,
        )
    except ImportConflictError as exc:
        return _error_response(
            status.HTTP_409_CONFLICT,
            detail=str(exc),
            code="import_conflict",
            import_id=import_id,
        )
    if result.failure_code is not None:
        # Return instead of raising: get_session commits the durable failed
        # lifecycle state while no partial transactions exist.
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="import commit failed",
            code=result.failure_code,
            import_id=result.batch.id,
            lifecycle_status=result.batch.status,
        )
    return ImportCommitResponse(
        import_id=result.batch.id,
        status="committed",
        created_count=result.created_count,
        linked_duplicate_count=result.linked_duplicate_count,
        transaction_ids=[transaction.id for transaction in result.transactions],
    )


@router.post(
    "/{import_id}/cancel",
    response_model=ImportCancelResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ImportNotFoundResponse},
        status.HTTP_409_CONFLICT: {"model": ImportErrorResponse},
    },
)
def post_import_cancel(
    profile_id: int,
    import_id: int,
    session: SessionDependency,
):
    """Idempotently cancel an uncommitted profile-owned preview."""

    try:
        batch = cancel_import(session, profile_id, import_id, logger=logger)
    except ImportConflictError as exc:
        return _error_response(
            status.HTTP_409_CONFLICT,
            detail=str(exc),
            code="import_conflict",
            import_id=import_id,
        )
    return ImportCancelResponse(import_id=batch.id, status="cancelled")


def _detail_response(batch) -> ImportDetailResponse:
    return ImportDetailResponse.model_validate(batch)


def _preview_response(batch, *, suggested_account_id: int | None) -> ImportPreviewResponse:
    return ImportPreviewResponse(
        **_detail_response(batch).model_dump(),
        suggested_account_id=suggested_account_id,
    )


def _error_response(
    response_status: int,
    *,
    detail: str,
    code: str,
    import_id: int | None = None,
    duplicate_of_import_id: int | None = None,
    lifecycle_status: str | None = None,
) -> JSONResponse:
    payload = ImportErrorResponse(
        detail=detail,
        code=code,
        import_id=import_id,
        duplicate_of_import_id=duplicate_of_import_id,
        status=lifecycle_status,
    )
    return JSONResponse(status_code=response_status, content=payload.model_dump())
