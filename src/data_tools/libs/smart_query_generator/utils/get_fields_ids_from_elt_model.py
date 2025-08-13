from ..models.models import ETLModel


def get_fields_ids_from_etl_model(etl: ETLModel):
    fields = set()
    for field in etl.fields:
        fields.add(field.id)
    return fields
