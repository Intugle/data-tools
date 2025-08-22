import pytest

from intugle.core.settings import settings
from intugle.libs.smart_query_generator.models.models import (
    ETLModel,
    FieldsModel,
    FilterModel,
    SelectionModel,
    SortByModel,
)
from intugle.sql_generator import SqlGenerator

# PROJECT_BASE = "/home/juhel-phanju/Documents/backup/MIGRATION/codes/poc/dbt/ecom/ecom/models"


def get_test_data():
    inputs = {
        "with_different_filters_and_sort": ETLModel(
            name="test_etl",
            fields=[
                FieldsModel(
                    id="claims_transactions.amount", name="claim_amount", category="measure", measure_func="sum"
                ),
            ],
            filter=FilterModel(
                selections=[SelectionModel(id="patients.first", values=["aaa", "bbb"])],
                sort_by=[SortByModel(id="encounters.code", direction="desc")],
            ),
        ),
        "filter_sort": ETLModel(
            name="test_etl",
            fields=[
                FieldsModel(id="patients.first", name="patients_name"),
                FieldsModel(
                    id="claims_transactions.amount", name="claim_amount", category="measure", measure_func="sum"
                ),
            ],
            # filter=FilterModel(selections=[])
        ),
    }
    outputs = {
        "filter_sort": "SELECT sum(claims_transactions.amount) as `claim_amount` FROM `encounters` LEFT JOIN `patients` ON encounters.patient = patients.id LEFT JOIN `claims_transactions` ON claims_transactions.patientid = patients.id WHERE (patients.first IN '['aaa', 'bbb']') ORDER BY `encounters`.`code` DESC",  # noqa: E501
        "with_different_filters_and_sort": "SELECT count(order_items.price) as `price` FROM `orders` LEFT JOIN `order_items` ON order_items.order_id = orders.order_id LEFT JOIN `products` ON order_items.product_id = products.product_id WHERE (products.product_id IN '['aaa', 'bbb']') ORDER BY `orders`.`order_id` DESC",  # noqa: E501
    }

    for key in inputs:
        yield [inputs[key], outputs[key]]


@pytest.mark.parametrize(
    "etl, query",
    get_test_data(),
)
def test_query_generator(etl, query):
    sql_generator = SqlGenerator(project_base=settings.PROJECT_BASE)

    out_query = sql_generator.generate_query(etl)
    print(out_query)

    # assert query == out_query
