from typing import Any
from sqlalchemy import func, or_
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import Select

from core.model.base_model import BaseModel
from core.model.word_list import WordList


class OSINTSource(BaseModel):
    """OSINT source model.

    Attributes:
        id: Primary key
        name: Name of the source
        description: Description of the source
        collector: Type of collector to use
        state: Current state of the source
        parameters: JSON parameters for the collector
        last_collected: Timestamp of last collection
        last_attempted: Timestamp of last collection attempt
        last_error_message: Last error message if collection failed
    """

    __tablename__ = "osint_source"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str]
    collector: Mapped[str]
    state: Mapped[str]
    parameters: Mapped[dict] = mapped_column(default=dict)

    word_lists: Mapped[list["WordList"]] = relationship("WordList", secondary="osint_source_word_list", back_populates="osint_sources")

    def __init__(
        self,
        id: int | None = None,
        name: str | None = None,
        description: str | None = None,
        collector: str | None = None,
        state: str | None = None,
        parameters: dict | None = None,
        word_lists: list | None = None,
    ):
        self.id = id
        self.name = name or ""
        self.description = description or ""
        self.collector = collector or ""
        self.state = state or ""
        self.parameters = parameters or {}
        self.word_lists = word_lists or []

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OSINTSource":
        word_lists = [WordList.find(word_list_id) for word_list_id in data.get("word_lists", [])]
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            description=data.get("description"),
            collector=data.get("collector"),
            state=data.get("state"),
            parameters=data.get("parameters"),
            word_lists=word_lists,
        )

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["word_lists"] = [word_list.id for word_list in self.word_lists]
        return data

    def to_detail_dict(self) -> dict[str, Any]:
        data = self.to_dict()
        data["word_lists"] = [word_list.to_dict() for word_list in self.word_lists]
        return data

    @classmethod
    def get_filter_query_with_joins(cls, filter_args: dict) -> Select:
        """Get filter query with joins.

        Arguments:
            filter_args: filter arguments

        Returns:
            Query with joins
        """
        query = cls.get_filter_query(filter_args)

        if "word_list" in filter_args:
            query = query.join(WordList, cls.word_lists)

        return query

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        """Get filter query.

        Arguments:
            filter_args: filter arguments

        Returns:
            Query
        """
        query = cls.get_base_query()

        if search := filter_args.get("search"):
            query = query.filter(
                or_(
                    func.lower(cls.name).like(func.lower(f"%{search}%")),
                    func.lower(cls.description).like(func.lower(f"%{search}%")),
                )
            )

        return query

    @classmethod
    def get_all_for_api(cls, filter_args: dict) -> tuple[list[dict[str, Any]], int]:
        query = cls.get_filter_query_with_joins(filter_args)
        return super().get_all_for_api_from_query(query, filter_args)
