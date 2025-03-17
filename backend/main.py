from fastapi import FastAPI, Depends, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import SessionLocal, User, Score, Student, get_db
from backend.auth import create_access_token, decode_token, get_password_hash, verify_password
from backend.config import TEMPLATES_DIR, STATIC_DIR, ALLOWED_ORIGINS, DEBUG
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
import pandas as pd
import numpy as np
import logging
import os
import io
import openpyxl
import sys

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

# 创建 FastAPI 应用
app = FastAPI(title="实时排行榜", debug=DEBUG)

# 在应用启动时测试Redis连接
@app.on_event("startup")
async def startup_event():
    """在应用启动时测试Redis连接"""
    logger.info("Testing Redis connection on startup...")
    try:
        if redis_client.ensure_connection():
            logger.info("Redis connection test successful")
        else:
            logger.warning("Redis connection test failed")
            logger.info("Using local storage instead of Redis")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        logger.info("Using local storage instead of Redis")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 设置模板目录
templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
templates = Jinja2Templates(directory=templates_dir)

# 设置静态文件目录
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 配置模板
templates.env.globals.update(enumerate=enumerate)

# 创建Excel模板
def create_excel_template():
    df = pd.DataFrame(columns=['班级/Class', '姓名/Name', '分数/Score'])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Score Template')
        worksheet = writer.sheets['Score Template']
        # 设置列宽
        worksheet.set_column('A:C', 15)
    output.seek(0)
    return output

@app.get("/download_template")
async def download_template():
    """下载评分模板"""
    try:
        # 创建示例数据
        data = {
            '班级/Class': ['三年级一班', '三年级二班'],
            '姓名/Name': ['张三', '李四'],
            '分数/Score': [8.5, 9.0]
        }
        
        # 创建DataFrame
        df = pd.DataFrame(data)
        logger.info(f"Created template DataFrame with columns: {df.columns.tolist()}")
        
        # 根据请求的格式创建相应的文件
        format = request.query_params.get('format', 'excel')
        
        if format == 'csv':
            # 创建CSV文件
            temp_file = "score_template.csv"
            df.to_csv(temp_file, index=False, encoding='utf-8-sig')  # 使用 UTF-8 with BOM 以支持中文
            return FileResponse(
                temp_file,
                filename="score_template.csv",
                media_type="text/csv"
            )
        else:
            # 创建Excel文件
            temp_file = "score_template.xlsx"
            with pd.ExcelWriter(
                temp_file,
                engine='xlsxwriter',
                engine_kwargs={'options': {'nan_inf_to_errors': True}}
            ) as writer:
                # 写入数据
                df.to_excel(writer, sheet_name='Score Template', index=False)
                
                # 获取 workbook 和 worksheet 对象
                workbook = writer.book
                worksheet = writer.sheets['Score Template']
                
                # 设置列宽
                worksheet.set_column('A:A', 20)  # 班级列
                worksheet.set_column('B:B', 15)  # 姓名列
                worksheet.set_column('C:C', 12)  # 分数列
                
                # 创建格式
                header_format = workbook.add_format({
                    'bold': True,
                    'font_size': 11,
                    'bg_color': '#E0E0E0',
                    'border': 1,
                    'text_wrap': True,
                    'align': 'center',
                    'valign': 'vcenter'
                })
                
                score_format = workbook.add_format({
                    'num_format': '0.0',  # 一位小数
                    'align': 'center',
                    'border': 1
                })
                
                text_format = workbook.add_format({
                    'align': 'left',
                    'border': 1,
                    'text_wrap': True,
                    'valign': 'vcenter'
                })
                
                # 应用标题格式
                for col, column_name in enumerate(df.columns):
                    worksheet.write(0, col, column_name, header_format)
                    logger.info(f"Writing column header: {column_name}")
                
                # 应用数据格式
                for row in range(len(df)):
                    worksheet.write(row + 1, 0, df.iloc[row, 0], text_format)  # 班级
                    worksheet.write(row + 1, 1, df.iloc[row, 1], text_format)  # 姓名
                    worksheet.write_number(row + 1, 2, float(df.iloc[row, 2]), score_format)  # 分数
                
                # 添加数据验证（限制分数范围为0-10）
                score_validation = {
                    'validate': 'decimal',
                    'criteria': 'between',
                    'minimum': 0,
                    'maximum': 10,
                    'input_title': '分数范围',
                    'input_message': '请输入0到10之间的分数，可以包含一位小数',
                    'error_title': '输入错误',
                    'error_message': '分数必须在0到10之间'
                }
                worksheet.data_validation('C2:C1000', score_validation)
                
                # 设置分数列的默认格式
                worksheet.set_column('C:C', 12, score_format)
                
                # 冻结首行
                worksheet.freeze_panes(1, 0)
                
                logger.info("Excel template created successfully")

            return FileResponse(
                temp_file,
                filename="score_template.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        logger.error(f"Error creating template file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"创建模板文件时出错: {str(e)}\nError creating template file: {str(e)}"
        )

@app.post("/upload_scores")
async def upload_scores(
    request: Request,
    subject: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """处理多个Excel或CSV文件上传并计算平均分"""
    try:
        # 测试Redis连接
        try:
            logger.info("Testing Redis connection before processing upload...")
            redis_client.ensure_connection()
            logger.info("Redis connection confirmed")
        except Exception as e:
            logger.error(f"Redis connection error before processing: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Redis服务器连接失败: {str(e)}\nRedis connection failed: {str(e)}"
            )

        # 验证评委身份
        access_token = request.cookies.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=401, 
                detail="请先登录\nPlease login first"
            )
        
        try:
            payload = decode_token(access_token)
            judge_username = payload.get("sub")
            if not judge_username:
                raise HTTPException(status_code=401, detail="Invalid token: missing username")
            
            # 验证用户是否存在
            user = db.query(User).filter(User.username == judge_username).first()
            if not user:
                raise HTTPException(status_code=401, detail="Invalid token: user not found")
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

        # 处理所有上传的文件
        all_scores = {}  # 用于存储所有学生的所有分数
        error_messages = []
        success_count = 0
        file_count = len(files)

        logger.info(f"Processing {file_count} files")

        for file_index, file in enumerate(files, 1):
            try:
                contents = await file.read()
                logger.info(f"Processing file {file_index}/{file_count}: {file.filename}, size: {len(contents)} bytes")
                
                # 根据文件扩展名决定处理方式
                if file.filename.lower().endswith('.csv'):
                    # 处理CSV文件
                    df = pd.read_csv(io.BytesIO(contents), encoding='utf-8-sig')
                    headers = df.columns.tolist()
                else:
                    # 处理Excel文件
                    workbook = openpyxl.load_workbook(io.BytesIO(contents), data_only=True)
                    worksheet = workbook.active
                    
                    # 获取标题行
                    headers = []
                    for cell in worksheet[1]:
                        value = cell.value
                        headers.append(str(value or '').strip())
                
                # 检查必要的列
                required_columns = {
                    '班级/Class': ['班级/Class', '班级', 'Class'],
                    '姓名/Name': ['姓名/Name', '姓名', 'Name'],
                    '分数/Score': ['分数/Score', '分数', 'Score']
                }
                
                # 找到每个必要列的索引
                column_indices = {}
                missing_columns = []
                for key, valid_names in required_columns.items():
                    found = False
                    for i, header in enumerate(headers):
                        if header in valid_names:
                            column_indices[key] = i
                            found = True
                            break
                    if not found:
                        missing_columns.append(key)
                
                if missing_columns:
                    error_msg = f"文件 {file.filename} 缺少以下必要的列：\n" + "\n".join(missing_columns)
                    logger.error(error_msg)
                    error_messages.append(error_msg)
                    continue
                
                # 处理数据
                if file.filename.lower().endswith('.csv'):
                    # 处理CSV数据
                    for row_idx, row in df.iterrows():
                        try:
                            class_name = str(row[headers[column_indices['班级/Class']]]).strip()
                            student_name = str(row[headers[column_indices['姓名/Name']]]).strip()
                            score_value = row[headers[column_indices['分数/Score']]]
                            
                            # 验证班级和姓名
                            if not class_name or not student_name:
                                error_messages.append(f"文件 {file.filename} 第 {row_idx + 2} 行的班级或姓名为空")
                                continue
                            
                            # 处理分数
                            try:
                                if pd.isna(score_value):
                                    raise ValueError("分数不能为空")
                                
                                score = float(score_value)
                                if not (0 <= score <= 10):
                                    raise ValueError(f"分数 {score} 超出范围(0-10)")
                                
                                # 将分数添加到学生的分数列表中
                                student_key = f"{class_name}:{student_name}"
                                if student_key not in all_scores:
                                    all_scores[student_key] = []
                                all_scores[student_key].append(score)
                                success_count += 1
                                
                            except (ValueError, TypeError) as e:
                                error_messages.append(
                                    f"文件 {file.filename} 第 {row_idx + 2} 行的分数格式不正确: '{score_value}'\n"
                                    f"错误信息: {str(e)}"
                                )
                                continue
                                
                        except Exception as e:
                            error_messages.append(f"处理文件 {file.filename} 第 {row_idx + 2} 行时出错: {str(e)}")
                            continue
                else:
                    # 处理Excel数据
                    for row_idx, row in enumerate(worksheet.iter_rows(min_row=2), start=2):
                        try:
                            class_name = str(row[column_indices['班级/Class']].value or '').strip()
                            student_name = str(row[column_indices['姓名/Name']].value or '').strip()
                            score_cell = row[column_indices['分数/Score']]
                            
                            # 验证班级和姓名
                            if not class_name or not student_name:
                                error_messages.append(f"文件 {file.filename} 第 {row_idx} 行的班级或姓名为空")
                                continue
                            
                            # 处理分数
                            try:
                                score_value = score_cell.value
                                if score_value is None or (isinstance(score_value, str) and not score_value.strip()):
                                    raise ValueError("分数不能为空")
                                
                                if isinstance(score_value, (int, float)):
                                    score = float(score_value)
                                else:
                                    score_str = str(score_value).strip()
                                    score_str = score_str.replace('。', '.').replace('，', '.').replace(',', '.')
                                    score = float(score_str)
                                
                                if not (0 <= score <= 10):
                                    raise ValueError(f"分数 {score} 超出范围(0-10)")
                                
                                # 将分数添加到学生的分数列表中
                                student_key = f"{class_name}:{student_name}"
                                if student_key not in all_scores:
                                    all_scores[student_key] = []
                                all_scores[student_key].append(score)
                                success_count += 1
                                
                            except (ValueError, TypeError) as e:
                                error_messages.append(
                                    f"文件 {file.filename} 第 {row_idx} 行的分数格式不正确: '{score_cell.value}'\n"
                                    f"错误信息: {str(e)}"
                                )
                                continue
                                
                        except Exception as e:
                            error_messages.append(f"处理文件 {file.filename} 第 {row_idx} 行时出错: {str(e)}")
                            continue
                        
            except Exception as e:
                error_messages.append(f"处理文件 {file.filename} 时出错: {str(e)}")
                continue

        # 计算并保存平均分
        try:
            # 统计每个学生的评分情况
            student_stats = {}
            for student_key, scores in all_scores.items():
                class_name, student_name = student_key.split(':')
                if len(scores) < 1:
                    error_messages.append(f"学生 {class_name} 班的 {student_name} 没有有效的分数")
                    continue

                # 计算统计数据
                avg_score = sum(scores) / len(scores)
                min_score = min(scores)
                max_score = max(scores)
                score_range = max_score - min_score
                judge_count = len(scores)
                
                student_stats[student_key] = {
                    "class_name": class_name,
                    "student_name": student_name,
                    "scores": scores,
                    "avg_score": avg_score,
                    "min_score": min_score,
                    "max_score": max_score,
                    "score_range": score_range,
                    "judge_count": judge_count
                }

                # 保存到Redis
                try:
                    # 保存平均分到排行榜
                    redis_client.zadd(f"leaderboard:{subject}", {f"{class_name}:{student_name}": avg_score})
                    
                    # 保存详细评分信息
                    details_key = f"{subject}:{class_name}:{student_name}:details"
                    redis_client.hset(details_key, mapping={
                        "avg_score": str(avg_score),
                        "min_score": str(min_score),
                        "max_score": str(max_score),
                        "score_range": str(score_range),
                        "judge_count": str(judge_count)
                    })
                    
                    # 保存每个评分
                    for i, score in enumerate(scores):
                        score_key = f"{subject}:{class_name}:{student_name}:judge{i+1}"
                        redis_client.set(score_key, score)
                    
                    logger.info(f"Saved scores for {student_key}: {student_stats[student_key]}")
                except Exception as e:
                    error_messages.append(f"保存学生 {student_name} 的分数时出错: {str(e)}")
                    continue

            # 生成统计信息
            if student_stats:
                total_students = len(student_stats)
                total_judges = sum(stats["judge_count"] for stats in student_stats.values())
                avg_judges = total_judges / total_students if total_students > 0 else 0
                students_with_3plus = sum(1 for stats in student_stats.values() if stats["judge_count"] >= 3)
                
                stats_key = f"stats:{subject}"
                redis_client.hset(stats_key, mapping={
                    "total_students": str(total_students),
                    "total_judges": str(total_judges),
                    "avg_judges": str(avg_judges),
                    "students_with_3plus": str(students_with_3plus),
                    "last_update": datetime.now().isoformat()
                })
                
                logger.info(f"Subject {subject} stats: total_students={total_students}, "
                          f"avg_judges={avg_judges:.2f}, students_with_3plus={students_with_3plus}")
        
        except Exception as e:
            logger.error(f"Error processing scores: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"处理分数时出错: {str(e)}\nError processing scores: {str(e)}"
            )

        # 如果有错误，返回错误信息
        if error_messages:
            if success_count > 0:
                message = (
                    f"成功导入 {success_count} 条记录。\n"
                    f"处理了 {file_count} 个文件。\n"
                    f"平均每个学生有 {avg_judges:.1f} 位评委评分。\n"
                    f"有 {students_with_3plus} 名学生获得了3位及以上评委的评分。\n"
                    f"以下记录导入失败：\n" + "\n".join(error_messages)
                )
            else:
                message = "\n".join(error_messages)
            raise HTTPException(status_code=400, detail=message)
        
        return RedirectResponse(url=f"/leaderboard/{subject}", status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"意外错误: {str(e)}\nUnexpected error: {str(e)}"
        )

# 错误处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP error {exc.status_code}: {exc.detail}")
    error_message = f"错误代码: {exc.status_code}\n{exc.detail}"
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "detail": error_message},
        status_code=exc.status_code,
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    error_type = type(exc).__name__
    error_message = str(exc)
    logger.error(f"General error ({error_type}): {error_message}")
    logger.exception("Detailed traceback:")  # 这会打印完整的堆栈跟踪
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request, 
            "detail": f"系统错误 ({error_type}): {error_message}\n如果问题持续存在，请联系管理员。"
        },
        status_code=500,
    )

# Home page
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    logger.info("Accessing home page")
    return templates.TemplateResponse("index.html", {"request": request})

# Login page
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    logger.info("Accessing login page")
    return templates.TemplateResponse("login.html", {"request": request})

# Register page
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    logger.info("Accessing register page")
    return templates.TemplateResponse("register.html", {"request": request})

# Submit score page
@app.get("/submit_score", response_class=HTMLResponse)
async def submit_score_page(request: Request):
    logger.info("Accessing submit score page")
    return templates.TemplateResponse("submit_score.html", {"request": request})

# Leaderboard page
@app.get("/leaderboard/{subject}", response_class=HTMLResponse)
async def leaderboard_page(
    request: Request,
    subject: str,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    try:
        # 获取Redis中的所有分数（实时排行榜）
        redis_scores = redis_client.zrevrange(f"leaderboard:{subject}", 0, -1, withscores=True)
        logger.debug(f"Redis scores for {subject}: {redis_scores}")

        # 处理Redis分数
        all_scores = []
        for key, avg_score in redis_scores:
            try:
                parts = key.split(':')
                if len(parts) >= 2:
                    class_name = parts[0]
                    student_name = parts[1]
                    
                    # 获取详细信息
                    details_key = f"{subject}:{class_name}:{student_name}:details"
                    details = redis_client.hgetall(details_key)
                    
                    if details:
                        score_info = {
                            "class_name": class_name,
                            "student_name": student_name,
                            "average": float(avg_score),
                            "judge_count": int(float(details.get("judge_count", 0))),
                            "min_score": float(details.get("min_score", avg_score)),
                            "max_score": float(details.get("max_score", avg_score)),
                            "score_range": float(details.get("score_range", 0))
                        }
                    else:
                        # 如果没有详细信息，使用基本信息
                        score_info = {
                            "class_name": class_name,
                            "student_name": student_name,
                            "average": float(avg_score),
                            "judge_count": 1,
                            "min_score": float(avg_score),
                            "max_score": float(avg_score),
                            "score_range": 0
                        }
                    
                    all_scores.append(score_info)
                    logger.debug(f"Processed score: {score_info}")
                    
            except Exception as e:
                logger.error(f"Error processing leaderboard entry: {str(e)}")
                continue

        # 按平均分降序排序
        all_scores.sort(key=lambda x: (-x["average"], -x["judge_count"], x["score_range"]))

        # 计算分页信息
        total_items = len(all_scores)
        total_pages = (total_items + page_size - 1) // page_size
        page = min(max(1, page), total_pages) if total_pages > 0 else 1
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_scores = all_scores[start_idx:end_idx]

        # 获取统计信息
        stats_key = f"stats:{subject}"
        stats = redis_client.hgetall(stats_key) or {}
        
        stats_info = {
            "total_students": int(float(stats.get("total_students", len(all_scores)))),
            "avg_judges": float(stats.get("avg_judges", 0)),
            "students_with_3plus": int(float(stats.get("students_with_3plus", 0))),
            "last_update": stats.get("last_update", "N/A")
        }

        logger.info(f"Processed {len(paginated_scores)} scores for subject {subject} (page {page}/{total_pages})")

        return templates.TemplateResponse(
            "leaderboard.html", 
            {
                "request": request, 
                "subject": subject, 
                "leaderboard": paginated_scores,
                "stats": stats_info,
                "current_page": page,
                "total_pages": total_pages,
                "total_items": total_items
            }
        )
    except Exception as e:
        logger.error(f"Error rendering leaderboard: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取排行榜数据时出错: {str(e)}\nError fetching leaderboard data: {str(e)}"
        )

# Login form submission
@app.post("/login", response_class=RedirectResponse)
async def login_form(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=400, 
                detail="用户名或密码错误\nInvalid username or password"
            )
        
        # 创建访问令牌
        access_token = create_access_token(data={"sub": username})
        response = RedirectResponse(url="/submit_score", status_code=303)
        response.set_cookie(
            key="access_token", 
            value=access_token,
            httponly=True,
            samesite='lax'
        )
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"登录过程中出现错误: {str(e)}\nError during login: {str(e)}"
        )

# Register form submission
@app.post("/register", response_class=RedirectResponse)
async def register_form(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == username).first()  # Corrected query
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(password)
    new_user = User(username=username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/login", status_code=303)

# Submit score form submission
@app.post("/submit_score", response_class=RedirectResponse)
async def submit_score_form(
    request: Request,
    subject: str = Form(...),
    score: float = Form(...),
    db: Session = Depends(get_db)
):
    # Server-side validation
    if score < 0 or score > 10:
        raise HTTPException(status_code=400, detail="Score must be between 0 and 10.")

    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(access_token)
        username = payload.get("sub")
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Add score to Redis leaderboard
        redis_client.zadd(f"leaderboard:{subject}", {username: score})

        # Save score to SQLite database
        new_score = Score(user_id=user.id, subject=subject, score=score, timestamp=datetime.utcnow())
        db.add(new_score)
        db.commit()

        return RedirectResponse(url=f"/leaderboard/{subject}", status_code=303)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/api/leaderboards")
async def get_leaderboards():
    """获取所有可用的排行榜科目"""
    try:
        # 获取所有分数键
        score_keys = redis_client.scan_iter("scores:*")
        # 提取科目名称
        subjects = set()
        for key in score_keys:
            # 从键名中提取科目名称 (scores:subject:*)
            parts = key.split(":")
            if len(parts) >= 2:
                subjects.add(parts[1])
        
        return {"subjects": sorted(list(subjects))}
    except Exception as e:
        logger.error(f"获取排行榜列表时出错: {str(e)}")
        raise HTTPException(status_code=500, detail="获取排行榜列表失败")

@app.get("/leaderboard/{subject}/fullscreen", response_class=HTMLResponse)
async def leaderboard_fullscreen(
    request: Request,
    subject: str,
    db: Session = Depends(get_db)
):
    try:
        # 获取Redis中的所有分数（实时排行榜）
        redis_scores = redis_client.zrevrange(f"leaderboard:{subject}", 0, -1, withscores=True)
        logger.debug(f"Redis scores for {subject} fullscreen: {redis_scores}")

        # 处理Redis分数
        all_scores = []
        for key, avg_score in redis_scores:
            try:
                parts = key.split(':')
                if len(parts) >= 2:
                    class_name = parts[0]
                    student_name = parts[1]
                    
                    # 获取详细信息
                    details_key = f"{subject}:{class_name}:{student_name}:details"
                    details = redis_client.hgetall(details_key)
                    
                    if details:
                        score_info = {
                            "class_name": class_name,
                            "student_name": student_name,
                            "average": float(avg_score),
                            "judge_count": int(float(details.get("judge_count", 0))),
                            "min_score": float(details.get("min_score", avg_score)),
                            "max_score": float(details.get("max_score", avg_score)),
                            "score_range": float(details.get("score_range", 0))
                        }
                    else:
                        score_info = {
                            "class_name": class_name,
                            "student_name": student_name,
                            "average": float(avg_score),
                            "judge_count": 1,
                            "min_score": float(avg_score),
                            "max_score": float(avg_score),
                            "score_range": 0
                        }
                    
                    all_scores.append(score_info)
                    logger.debug(f"Processed score for fullscreen: {score_info}")
                    
            except Exception as e:
                logger.error(f"Error processing leaderboard entry for fullscreen: {str(e)}")
                continue

        # 按平均分降序排序
        all_scores.sort(key=lambda x: (-x["average"], -x["judge_count"], x["score_range"]))

        logger.info(f"Processed {len(all_scores)} scores for fullscreen display")

        return templates.TemplateResponse(
            "leaderboard_fullscreen.html", 
            {
                "request": request, 
                "subject": subject, 
                "leaderboard": all_scores
            }
        )
    except Exception as e:
        logger.error(f"Error rendering fullscreen leaderboard: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取排行榜数据时出错: {str(e)}\nError fetching leaderboard data: {str(e)}"
        )

@app.get("/leaderboard/{subject}/winners", response_class=HTMLResponse)
async def winners_display(request: Request, subject: str, count: int = 5):
    try:
        # 获取排行榜数据
        redis_scores = redis_client.zrevrange(f"leaderboard:{subject}", 0, -1, withscores=True)
        all_scores = []
        
        for member, score in redis_scores:
            try:
                # 解码 bytes 为字符串
                if isinstance(member, bytes):
                    member = member.decode('utf-8')
                
                # 从字符串中提取班级和姓名
                class_name, student_name = member.split(':')
                
                # 获取详细信息
                details_key = f"{subject}:{class_name}:{student_name}:details"
                details = redis_client.hgetall(details_key)
                
                score_info = {
                    "class_name": class_name,
                    "student_name": student_name,
                    "average": float(score),
                    "judge_count": int(float(details.get("judge_count", 1))),
                    "min_score": float(details.get("min_score", score)),
                    "max_score": float(details.get("max_score", score)),
                    "score_range": float(details.get("score_range", 0))
                }
                
                all_scores.append(score_info)
                logger.info(f"Processed winner: {score_info}")
                
            except Exception as e:
                logger.error(f"Error processing winner {member}: {str(e)}")
                continue
            
        # 按平均分数排序
        all_scores.sort(key=lambda x: (-x["average"], -x["judge_count"], x["score_range"]))
        
        # 限制显示的获奖者数量
        count = max(min(count, len(all_scores)), 1)  # 确保count在1和总数之间
        winners = all_scores[:count]
        
        return templates.TemplateResponse(
            "winners_display.html",
            {
                "request": request,
                "subject": subject,
                "winners": winners
            }
        )
    except Exception as e:
        logger.error(f"Error in winners display: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}