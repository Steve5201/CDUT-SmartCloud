# core/crud.py
from sqlalchemy.orm import Session
from typing import Type, TypeVar, Any, Dict, List, Generic

# 定义泛型 T，代表任何 SQLAlchemy ORM 模型
T = TypeVar("T")

class BaseCRUD(Generic[T]):
    """
    最底层的泛型原子操作类（100%解耦，不绑定任何特定字段如 user_id）
    所有条件过滤均通过 Python 的 **kwargs 动态精确匹配实现。
    """

    def __init__(self, model: Type[T]):
        self.model = model

    # ==========================================
    # 1. 增 (Create)
    # ==========================================
    def create(self, db: Session, obj_in: Dict[str, Any]) -> T:
        """原子操作：新增一条记录并落盘"""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # ==========================================
    # 2. 查 (Read)
    # ==========================================
    def get(self, db: Session, id: Any) -> T | None:
        """原子操作：根据主键 ID 直接查询单条记录"""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_by_attributes(self, db: Session, **attrs: Any) -> T | None:
        """
        原子操作：根据任意属性条件精确匹配，查询单条记录。
        例如：crud.get_by_attributes(db, username="lgy")
        """
        return db.query(self.model).filter_by(**attrs).first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: Any = None,
        **attrs: Any
    ) -> List[T]:
        """
        原子操作：根据任意属性精确匹配，查询多条数据，支持分页和排序。
        例如：crud.get_multi(db, skip=0, limit=10, user_id=1)
        """
        query = db.query(self.model).filter_by(**attrs)
        if order_by is not None:
            query = query.order_by(order_by)
        return query.offset(skip).limit(limit).all()

    def count(self, db: Session, **attrs: Any) -> int:
        """原子操作：统计符合条件的记录总数"""
        return db.query(self.model).filter_by(**attrs).count()

    # ==========================================
    # 3. 改 (Update)
    # ==========================================
    def update(self, db: Session, *, db_obj: T, obj_in: Dict[str, Any]) -> T:
        """
        原子操作：传入一个已存在的 ORM 对象，根据传入的字典进行更新。
        （这是最安全的更新方式，保证了数据库连接处于同一事务中）
        """
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_by_id(self, db: Session, id: Any, obj_in: Dict[str, Any]) -> T | None:
        """原子操作：直接根据主键 ID 查出并更新记录"""
        db_obj = self.get(db, id)
        if not db_obj:
            return None
        return self.update(db, db_obj=db_obj, obj_in=obj_in)

    # ==========================================
    # 4. 删 (Delete)
    # ==========================================
    def delete(self, db: Session, id: Any) -> bool:
        """原子操作：根据主键 ID 删除单条记录"""
        db_obj = self.get(db, id)
        if not db_obj:
            return False
        db.delete(db_obj)
        db.commit()
        return True

    def delete_by_attributes(self, db: Session, **attrs: Any) -> int:
        """
        原子操作：根据任意属性条件，批量删除数据，并返回被删除的记录行数。
        例如：crud.delete_by_attributes(db, user_id=1, topic="错题本")
        """
        deleted_count = db.query(self.model).filter_by(**attrs).delete()
        db.commit()
        return deleted_count