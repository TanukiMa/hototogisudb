from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PosType(BaseModel):
    id: int
    left_id: int
    right_id: int
    description: str
    category: Optional[str] = None


class ImportBatch(BaseModel):
    id: int
    source_type: str
    source_url: Optional[str] = None
    file_name: str
    file_sha256: Optional[str] = None
    record_count: Optional[int] = None
    imported_by: Optional[str] = None
    imported_at: Optional[datetime] = None
    notes: Optional[str] = None


class MozcDictEntry(BaseModel):
    reading: str
    left_id: int
    right_id: int
    cost: int
    surface_form: str

    def to_tsv_line(self) -> str:
        return f"{self.reading}\t{self.left_id}\t{self.right_id}\t{self.cost}\t{self.surface_form}"
