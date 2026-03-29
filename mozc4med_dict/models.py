from datetime import datetime

from pydantic import BaseModel


class PosType(BaseModel):
    id: int
    left_id: int
    right_id: int
    description: str
    category: str | None = None


class ImportBatch(BaseModel):
    id: int
    source_type: str
    source_url: str | None = None
    file_name: str
    file_sha256: str | None = None
    record_count: int | None = None
    imported_by: str | None = None
    imported_at: datetime | None = None
    notes: str | None = None


class MozcDictEntry(BaseModel):
    reading: str
    left_id: int
    right_id: int
    cost: int
    surface_form: str

    def to_tsv_line(self) -> str:
        return f"{self.reading}\t{self.left_id}\t{self.right_id}\t{self.cost}\t{self.surface_form}"
