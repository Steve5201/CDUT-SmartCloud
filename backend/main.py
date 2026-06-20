# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 引入各大纯净路由模块
from routers import auth, session, agent, file, admin

app = FastAPI(
    title="CDUT SmartCloud Backend",
    description="成理智云 - 具备自愈与多模态文件引用能力的 AI 助教平台",
    version="2.0.0"
)

# CORS 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由（分门别类，强内聚）
app.include_router(auth.router)
app.include_router(session.router)
app.include_router(agent.router)
app.include_router(file.router)
app.include_router(admin.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to CDUT SmartCloud Enterprise API! 🚀"}