from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import shutil
import os
import traceback
import asyncio
import zipfile
import io
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from app.analyzer import ImageAnalyzer, analyze_image_sync
from app.profiler import DatasetProfiler

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.executor = ProcessPoolExecutor()
    yield
    app.state.executor.shutdown()

app = FastAPI(title="AI视觉数据特征分析平台", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """默认入口：导航页"""
    return templates.TemplateResponse("mode_selection.html", {"request": request})

@app.get("/micro", response_class=HTMLResponse)
async def read_micro_analysis(request: Request):
    """微观·单图透视"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/macro", response_class=HTMLResponse)
async def read_macro_analysis(request: Request):
    """宏观·数据集全览"""
    return templates.TemplateResponse("dataset_analysis.html", {"request": request})

async def process_files(files: List[UploadFile], loop, executor):
    """通用文件处理逻辑：支持普通图片和ZIP压缩包"""
    final_results = []
    pending_tasks = [] # (content, filename)
    
    for file in files:
        content = await file.read()
        filename = file.filename.lower()
        
        # 1. 处理 ZIP 压缩包
        if filename.endswith('.zip'):
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    for zname in zf.namelist():
                        if zname.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tiff', '.tif')):
                            # 过滤掉 __MACOSX 等隐藏文件
                            if '__MACOSX' in zname or zname.startswith('.'):
                                continue
                            zcontent = zf.read(zname)
                            # 使用原始文件名作为标识
                            pending_tasks.append((zcontent, f"{filename}/{zname}"))
            except Exception as e:
                final_results.append({
                    "filename": filename,
                    "status": "error",
                    "message": f"ZIP解压失败: {str(e)}"
                })
        
        # 2. 处理普通图片
        elif file.content_type.startswith("image/") or filename.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tiff', '.tif')):
             pending_tasks.append((content, file.filename))
             
        else:
            final_results.append({
                "filename": file.filename,
                "status": "error",
                "message": "不支持的文件类型"
            })

    # 并发执行图片分析
    if pending_tasks:
        futures = []
        for content, fname in pending_tasks:
            futures.append(loop.run_in_executor(executor, analyze_image_sync, content, fname))
            
        task_results = await asyncio.gather(*futures)
        final_results.extend(task_results)
        
    return final_results

@app.post("/analyze")
async def analyze_images(request: Request, files: List[UploadFile] = File(...)):
    """单图分析接口：返回列表详情"""
    loop = asyncio.get_running_loop()
    executor = request.app.state.executor
    results = await process_files(files, loop, executor)
    return JSONResponse(content=results)

@app.post("/analyze/dataset")
async def analyze_dataset(request: Request, files: List[UploadFile] = File(...)):
    """数据集分析接口：返回宏观报告"""
    loop = asyncio.get_running_loop()
    executor = request.app.state.executor
    
    # 1. 先进行全量单图分析
    raw_results = await process_files(files, loop, executor)
    
    # 2. 聚合分析
    profiler = DatasetProfiler(raw_results)
    report = profiler.profile()
    
    return JSONResponse(content={
        "summary": report,
        "total_files": len(raw_results),
        "sample_details": raw_results[:10] # 仅返回前10条作为样本展示，避免数据量过大
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
