
etl = {
    "name": "test_etl",
    "fields": [
        {"id": "patients.first", "name": "first_name"},
        {"id": "patients.last", "name": "last_name"},
        {"id": "allergies.start", "name": "start_date"},
    ],
    "filter": {
        "selections": [{"id": "claims.departmentid", "values": ["3", "20"]}],
    },
}

from intugle.sql_generator import SqlGenerator

# Create a SqlGenerator
sql_generator = SqlGenerator()

# Generate the query
sql_query = sql_generator.generate_query(etl)

# Print the query
print(sql_query)