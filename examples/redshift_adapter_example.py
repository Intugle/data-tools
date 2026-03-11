"""
Example: Using Intugle with Amazon Redshift

This example demonstrates how to use Intugle to profile and analyze data in Amazon Redshift.

Prerequisites:
1. Install Intugle with Redshift support: pip install intugle[redshift]
2. Configure your profiles.yml with Redshift connection details
3. Have access to a Redshift cluster with sample data
"""

from intugle.adapters.types.redshift.models import RedshiftConfig
from intugle.adapters.types.redshift.redshift import RedshiftAdapter
from intugle.analysis.models import DataSet


def main():
    # Initialize the Redshift adapter
    # This will read configuration from profiles.yml
    adapter = RedshiftAdapter()
    
    print(f"Connected to Redshift source: {adapter.source_name}")
    print(f"Database: {adapter.database}")
    print(f"Schema: {adapter.schema}")
    print("-" * 50)
    
    # Example 1: Profile a table
    print("\n=== Example 1: Profile a Table ===")
    customers_config = RedshiftConfig(
        identifier="customers",
        type="redshift"
    )
    
    profile = adapter.profile(customers_config, "customers")
    print(f"Table: customers")
    print(f"Total rows: {profile.count}")
    print(f"Columns: {', '.join(profile.columns)}")
    print(f"Data types: {profile.dtypes}")
    
    # Example 2: Profile a specific column
    print("\n=== Example 2: Profile a Column ===")
    column_profile = adapter.column_profile(
        data=customers_config,
        table_name="customers",
        column_name="customer_id",
        total_count=profile.count,
        sample_limit=5
    )
    
    print(f"Column: {column_profile.column_name}")
    print(f"Total count: {column_profile.count}")
    print(f"Null count: {column_profile.null_count}")
    print(f"Distinct count: {column_profile.distinct_count}")
    print(f"Uniqueness: {column_profile.uniqueness:.2%}")
    print(f"Completeness: {column_profile.completeness:.2%}")
    print(f"Sample data: {column_profile.sample_data}")
    
    # Example 3: Execute a custom query
    print("\n=== Example 3: Execute a Custom Query ===")
    query = """
    SELECT 
        customer_segment,
        COUNT(*) as customer_count,
        AVG(lifetime_value) as avg_lifetime_value
    FROM customers
    GROUP BY customer_segment
    ORDER BY customer_count DESC
    """
    
    df = adapter.to_df_from_query(query)
    print("Customer segments:")
    print(df.to_string(index=False))
    
    # Example 4: Create a view from a query
    print("\n=== Example 4: Create a View ===")
    view_query = """
    SELECT 
        customer_id,
        customer_name,
        email,
        customer_segment,
        lifetime_value
    FROM customers
    WHERE customer_segment = 'Premium'
    AND lifetime_value > 10000
    """
    
    adapter.create_table_from_query(
        table_name="premium_customers",
        query=view_query,
        materialize="view"
    )
    print("Created view: premium_customers")
    
    # Verify the view was created
    premium_df = adapter.to_df_from_query(
        "SELECT COUNT(*) as count FROM premium_customers"
    )
    print(f"Premium customers count: {premium_df['count'][0]}")
    
    # Example 5: Analyze relationship between tables
    print("\n=== Example 5: Analyze Table Relationships ===")
    customers_dataset = DataSet(
        RedshiftConfig(identifier="customers"),
        name="customers"
    )
    
    orders_dataset = DataSet(
        RedshiftConfig(identifier="orders"),
        name="orders"
    )
    
    # Find how many customer IDs appear in both tables
    intersection = adapter.intersect_count(
        table1=customers_dataset,
        column1_name="customer_id",
        table2=orders_dataset,
        column2_name="customer_id"
    )
    
    print(f"Customers with orders: {intersection}")
    
    # Example 6: Analyze composite key uniqueness
    print("\n=== Example 6: Composite Key Analysis ===")
    orders_config = RedshiftConfig(identifier="orders")
    
    # Check uniqueness of composite key (customer_id, order_date)
    composite_uniqueness = adapter.get_composite_key_uniqueness(
        table_name="orders",
        columns=["customer_id", "order_date"],
        dataset_data=orders_config
    )
    
    print(f"Unique (customer_id, order_date) combinations: {composite_uniqueness}")
    
    # Example 7: Create a materialized view
    print("\n=== Example 7: Create a Materialized View ===")
    materialized_query = """
    SELECT 
        DATE_TRUNC('month', order_date) as month,
        customer_segment,
        COUNT(DISTINCT customer_id) as unique_customers,
        COUNT(*) as order_count,
        SUM(order_total) as total_revenue
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    GROUP BY 1, 2
    """
    
    adapter.create_table_from_query(
        table_name="monthly_segment_metrics",
        query=materialized_query,
        materialize="materialized_view"
    )
    print("Created materialized view: monthly_segment_metrics")
    print("Note: Refresh with: REFRESH MATERIALIZED VIEW monthly_segment_metrics")
    
    print("\n" + "=" * 50)
    print("All examples completed successfully!")


if __name__ == "__main__":
    main()
