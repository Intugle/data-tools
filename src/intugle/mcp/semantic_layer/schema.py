from enum import StrEnum


class SQLDialect(StrEnum):
    POSTGRES = "postgresql"
    MSSQL = "mssql"
    SQLITE = "sqlite"

    def __repr__(self):
        return str(self.value)

    @property
    def sql_glot_dialect(
        self,
    ) -> str:
        if self.value == SQLDialect.MSSQL:
            return "tsql"
        elif self.value == SQLDialect.POSTGRES:
            return "postgres"

        return str(self.value)

    @property
    def prompt_dialect(
        self,
    ) -> str:
        mappings = {
            SQLDialect.MSSQL: "Transact-SQL",
            SQLDialect.POSTGRES: "PostgreSQL",
            SQLDialect.SQLITE: "SQlite",
        }
        return mappings.get(self.value, self.value)
