from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.storage = {}
        logger.info("Using local storage mode")

    def ensure_connection(self):
        return True

    def set(self, key: str, value: str) -> bool:
        try:
            self.storage[key] = value
            return True
        except Exception as e:
            logger.error(f"Error in set operation: {str(e)}")
            return False

    def get(self, key: str) -> Optional[str]:
        try:
            return self.storage.get(key)
        except Exception as e:
            logger.error(f"Error in get operation: {str(e)}")
            return None

    def delete(self, key: str) -> bool:
        try:
            self.storage.pop(key, None)
            return True
        except Exception as e:
            logger.error(f"Error in delete operation: {str(e)}")
            return False

    def zadd(self, key: str, mapping: Dict[str, float]) -> bool:
        try:
            if key not in self.storage:
                self.storage[key] = {}
            self.storage[key].update(mapping)
            return True
        except Exception as e:
            logger.error(f"Error in zadd operation: {str(e)}")
            return False

    def zrange(self, key: str, start: int, stop: int, withscores: bool = False) -> Union[List[str], List[tuple]]:
        try:
            data = self.storage.get(key, {})
            sorted_items = sorted(data.items(), key=lambda x: float(x[1]))
            if stop < 0:
                stop = len(sorted_items) + stop + 1
            result = sorted_items[start:stop]
            if withscores:
                return [(item[0], float(item[1])) for item in result]
            return [item[0] for item in result]
        except Exception as e:
            logger.error(f"Error in zrange operation: {str(e)}")
            return []

    def zrevrange(self, key: str, start: int, stop: int, withscores: bool = False) -> Union[List[str], List[tuple]]:
        try:
            result = self.zrange(key, start, stop, withscores=withscores)
            if withscores:
                return [(item[0], float(item[1])) for item in reversed(result)]
            return list(reversed(result))
        except Exception as e:
            logger.error(f"Error in zrevrange operation: {str(e)}")
            return []

    def hset(self, key: str, mapping: Dict[str, Any]) -> bool:
        try:
            if key not in self.storage:
                self.storage[key] = {}
            self.storage[key].update(mapping)
            return True
        except Exception as e:
            logger.error(f"Error in hset operation: {str(e)}")
            return False

    def hgetall(self, key: str) -> Dict[str, str]:
        try:
            return self.storage.get(key, {})
        except Exception as e:
            logger.error(f"Error in hgetall operation: {str(e)}")
            return {}

    def scan_iter(self, pattern: str) -> List[str]:
        try:
            matching_keys = []
            for key in self.storage.keys():
                if pattern.replace("*", "") in key:
                    matching_keys.append(key)
            return matching_keys
        except Exception as e:
            logger.error(f"Error in scan_iter operation: {str(e)}")
            return []

redis_client = RedisClient()

# 添加项目根目录到 Python 路径
root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_path)

# 导入必要的模块
from .models import User, Score
from .database import SessionLocal, engine, Base
from .auth import create_access_token, decode_token, get_password_hash, verify_password

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI()

# 设置模板目录
templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "templates")
logger.info(f"Templates directory: {templates_dir}")
templates = Jinja2Templates(directory=templates_dir)

# 设置静态文件目录
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "static")
logger.info(f"Static directory: {static_dir}")
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
        redis_client.zadd(f"leaderboard:{subject}", {username: score})

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
        scores = redis_client.zrevrange(f"leaderboard:{subject}", 0, -1, withscores=True)
        
        all_scores = []
        for member, score in scores:
            try:
                if isinstance(member, bytes):
                    member = member.decode('utf-8')
                
                # 获取详细信息
                details_key = f"{subject}:{member}:details"
                details = redis_client.hgetall(details_key)
                
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