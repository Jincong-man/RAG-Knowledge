"""文档分块策略配置"""
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings


def get_splitter() -> RecursiveCharacterTextSplitter:
    """
    获取中文优化的文档分块器
    使用中文标点符号作为分隔符，针对电商文档优化
    """
    return RecursiveCharacterTextSplitter(
        separators=[
            "\n\n",  # 段落分隔
            "\n",    # 换行
            "。",    # 中文句号
            "！",    # 中文感叹号
            "？",    # 中文问号
            "；",    # 中文分号
            "，",    # 中文逗号
            ". ",    # 英文句号
            "! ",    # 英文感叹号
            "? ",    # 英文问号
            "; ",    # 英文分号
            ", ",    # 英文逗号
            " ",     # 空格
            "",      # 字符级（兜底）
        ],
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        length_function=len,  # 按字符数计算（中文友好）
        is_separator_regex=False,
    )
