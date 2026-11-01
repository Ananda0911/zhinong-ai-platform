"""全局配置：从 .env 读取，模型名集中在此管理。"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 通义千问 DashScope（OpenAI 兼容模式）
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    MODEL_TEXT: str = "qwen-plus"          # 文本对话 / 文案 / RAG 生成
    MODEL_VL: str = "qwen3-vl-plus"       # 病虫害图片识别（qwen-vl-plus 已下线）
    MODEL_EMBEDDING: str = "qwen3.7-text-embedding-flash"  # 向量化（1024 维；text-embedding-v3 已下线）

    # 认证
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 72

    # 政策文档解析：api（MinerU 官方托管 API，按页计费）/ local（本地 MinerU，暂未实现）
    MINERU_MODE: str = "api"
    MINERU_API_TOKEN: str = ""  # https://mineru.net 申请
    MINERU_MODEL_VERSION: str = "vlm"  # pipeline / vlm

    # 存储路径
    DATABASE_URL: str = "sqlite:///./data/app.db"
    UPLOAD_DIR: str = "uploads"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
