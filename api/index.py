from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
import sys
from pathlib import Path
from typing import List
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加项目根目录到 Python 路径
root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_path)

# 导入必要的模块
from backend.models import User, Score
from .database import SessionLocal, engine, Base
from backend.auth import create_access_token, decode_token, get_password_hash, verify_password
from backend.redis_client import redis_client

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI()

# 设置模板目录
templates_dir = os.path.join(root_path, "backend", "templates")
templates = Jinja2Templates(directory=templates_dir)

# 设置静态文件目录
static_dir = os.path.join(root_path, "backend", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """注册页面"""
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """处理注册请求"""
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # 创建新用户
    hashed_password = get_password_hash(password)
    new_user = User(username=username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    
    return RedirectResponse(url="/login", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """处理登录请求"""
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid username or password")
    
    access_token = create_access_token(data={"sub": username})
    response = RedirectResponse(url="/submit_score", status_code=303)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@app.get("/submit_score", response_class=HTMLResponse)
async def submit_score_page(request: Request):
    """提交分数页面"""
    return templates.TemplateResponse("submit_score.html", {"request": request})

@app.post("/submit_score")
async def submit_score(
    request: Request,
    subject: str = Form(...),
    score: float = Form(...),
    db: Session = Depends(get_db)
):
    """处理分数提交"""
    if score < 0 or score > 10:
        raise HTTPException(status_code=400, detail="Score must be between 0 and 10")

    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_token(access_token)
        username = payload.get("sub")
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 添加分数到 Redis 排行榜
        await redis_client.zadd(f"leaderboard:{subject}", {username: score})

        # 保存分数到数据库
        new_score = Score(user_id=user.id, subject=subject, score=score)
        db.add(new_score)
        db.commit()

        return RedirectResponse(url=f"/leaderboard/{subject}", status_code=303)
    except Exception as e:
        logger.error(f"Error submitting score: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/leaderboard/{subject}", response_class=HTMLResponse)
async def leaderboard_page(
    request: Request,
    subject: str,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    """排行榜页面"""
    try:
        # 从 Redis 获取排行榜数据
        scores = await redis_client.zrevrange(f"leaderboard:{subject}", 0, -1, withscores=True)
        
        all_scores = []
        for member, score in scores:
            try:
                if isinstance(member, bytes):
                    member = member.decode('utf-8')
                
                # 获取详细信息
                details_key = f"{subject}:{member}:details"
                details = await redis_client.hgetall(details_key)
                
                score_info = {
                    "username": member,
                    "score": float(score),
                    "judge_count": int(float(details.get("judge_count", 1))) if details else 1
                }
                
                all_scores.append(score_info)
                
            except Exception as e:
                logger.error(f"Error processing score for {member}: {str(e)}")
                continue

        # 计算分页
        total_items = len(all_scores)
        total_pages = (total_items + page_size - 1) // page_size
        page = min(max(1, page), total_pages) if total_pages > 0 else 1
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_scores = all_scores[start_idx:end_idx]

        return templates.TemplateResponse(
            "leaderboard.html",
            {
                "request": request,
                "subject": subject,
                "leaderboard": paginated_scores,
                "current_page": page,
                "total_pages": total_pages
            }
        )
    except Exception as e:
        logger.error(f"Error displaying leaderboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 