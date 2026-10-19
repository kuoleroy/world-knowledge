"""骨架数据（阶段 / 学科 / 知识传统）的响应模型。"""

from app.schemas.common import CamelModel


class StageOut(CamelModel):
    """教育阶段。"""

    id: str
    display_name: str
    core_question: str
    relation: str
    epistemology: str


class DisciplineOut(CamelModel):
    """学科大类。"""

    id: str
    display_name: str
    name_zh: str


class TraditionOut(CamelModel):
    """知识传统标签。"""

    id: str
    display_name: str
    meaning: str
