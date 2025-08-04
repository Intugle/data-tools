from pydantic import BaseModel


class ProfilingOutput(BaseModel):
    count: int
    columns: list[str]
    dtypes: dict[str, str]