"""Main FastAPI application entry point."""
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.database import get_db, init_db, close_db
from app.models import User, RoleEnum, ActivityLog, ActionEnum
from app.schemas import LoginRequest, TokenResponse, HealthResponse
from app.auth import verify_password, create_access_token, HASHED_EVENT_PASSWORD
from app.dependencies import limiter
from app import admin_routes, user_routes
from app.logging_config import logger

# Create FastAPI application
app = FastAPI(
    title="Wedding Face Recognition API",
    description="Backend API for wedding photo face recognition system",
    version="1.0.0"
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(admin_routes.router)
app.include_router(user_routes.router)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting Wedding Face Recognition API")
    logger.info(f"CORS origins: {settings.cors_origins_list}")
    
    # Initialize database tables
    await init_db()
    logger.info("Database initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Shutting down Wedding Face Recognition API")
    await close_db()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow()
    )


@app.post("/auth/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return JWT token.
    
    Args:
        request: Login request with password and role
        db: Database session
        
    Returns:
        JWT token and user information
    """
    try:
        # Verify password
        if not verify_password(request.password, HASHED_EVENT_PASSWORD):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Parse role
        try:
            role = RoleEnum(request.role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role. Must be 'admin' or 'user'"
            )
        
        # Check if user exists or create new user
        # In this system, we don't have username, so we create a new user each time
        # or we could use role-based lookup. For simplicity, let's create a unique user per session.
        # Actually, let's use a simpler approach: find or create user by role
        # For this wedding app, we'll create a new user record for each login to track sessions
        
        user = User(role=role, last_login=datetime.utcnow())
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Log login activity
        activity_log = ActivityLog(
            user_id=user.id,
            action=ActionEnum.login,
            photo_count=None
        )
        db.add(activity_log)
        await db.commit()
        
        # Create access token
        access_token = create_access_token(
            data={"sub": str(user.id), "role": role.value}
        )
        
        logger.info(f"User logged in: {user.id} with role {role.value}")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            role=role.value
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
