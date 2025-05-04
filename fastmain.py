from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from router import router
from models import Base, engine

# 创建FastAPI应用实例
app = FastAPI()

# 解决跨域问题，允许指定的源访问
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 包含所有路由
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)