import pytest

from data_tools.libs.smart_query_generator.models.models import (
    ETLModel,
    FieldsModel,
    FilterModel,
    SelectionModel,
    SortByModel,
)
from data_tools.sql_generator import SqlGenerator

PROJECT_BASE = "/home/juhel-phanju/Documents/backup/MIGRATION/codes/poc/dbt/ecom/ecom/models"


def get_test_data():
    inputs = {
        "with_different_filters_and_sort": ETLModel(
            name="test_etl",
            fields=[
                FieldsModel(id="order_items.price", name="price", category="measure", measure_func="count"),
            ],
            filter=FilterModel(
                selections=[SelectionModel(id="products.product_id", values=["aaa", "bbb"])],
                sort_by=[SortByModel(id="orders.order_id", direction="desc")],
            ),
        ),
        "filter_sort": ETLModel(
            name="test_etl",
            fields=[
                FieldsModel(
                    id="products.product_length_cm", name="product_length", category="measure", measure_func="count"
                ),
                FieldsModel(id="order_items.price", name="price", category="measure", measure_func="count"),
            ],
            filter=FilterModel(
                selections=[SelectionModel(id="products.product_id", values=["aaa", "bbb"])],
                sort_by=[SortByModel(id="orders.order_id", direction="desc")],
            ),
        ),
    }
    outputs = {
        "filter_sort": "SELECT count(products.product_length_cm) as `product_length`, count(order_items.price) as `price` FROM `orders` LEFT JOIN `order_items` ON order_items.order_id = orders.order_id LEFT JOIN `products` ON order_items.product_id = products.product_id WHERE (products.product_id IN '['aaa', 'bbb']') ORDER BY `orders`.`order_id` DESC",  # noqa: E501
        "with_different_filters_and_sort": "SELECT count(order_items.price) as `price` FROM `orders` LEFT JOIN `order_items` ON order_items.order_id = orders.order_id LEFT JOIN `products` ON order_items.product_id = products.product_id WHERE (products.product_id IN '['aaa', 'bbb']') ORDER BY `orders`.`order_id` DESC",  # noqa: E501
    }

    for key in inputs:
        yield [inputs[key], outputs[key]]


@pytest.mark.parametrize(
    "etl, query",
    get_test_data(),
)
def test_query_generator(etl, query):
    sql_generator = SqlGenerator(project_base=PROJECT_BASE)

    out_query = sql_generator.generate_query(etl)

    assert query == out_query
