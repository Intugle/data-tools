
import pandas as pd


class DataProductPlan:
    """
    A helper class to manage and modify a data product plan DataFrame.
    """
    def __init__(self, df: pd.DataFrame):
        if not isinstance(df, pd.DataFrame):
            raise TypeError("df must be a pandas DataFrame.")
        self._df = df.copy()
        if '_is_active' not in self._df.columns:
            self._df['_is_active'] = True

    @property
    def name(self) -> str:
        """Gets the name of the data product."""
        return self._df['Data Product Name'].iloc[0]

    @name.setter
    def name(self, new_name: str):
        """Sets the name of the data product."""
        self._df['Data Product Name'] = new_name

    @property
    def description(self) -> str:
        """Gets the description of the data product."""
        return self._df['Data Product Description'].iloc[0]

    @description.setter
    def description(self, new_description: str):
        """Sets the description of the data product."""
        self._df['Data Product Description'] = new_description

    def rename_attribute(self, old_name: str, new_name: str):
        """Renames an attribute."""
        if old_name not in self._df['Attribute Name'].values:
            raise ValueError(f"Attribute '{old_name}' not found in the plan.")
        if new_name in self._df['Attribute Name'].values:
            raise ValueError(f"Attribute '{new_name}' already exists in the plan.")
        self._df.loc[self._df['Attribute Name'] == old_name, 'Attribute Name'] = new_name

    def set_attribute_description(self, attribute_name: str, new_description: str):
        """Sets the description for a specific attribute."""
        if attribute_name not in self._df['Attribute Name'].values:
            raise ValueError(f"Attribute '{attribute_name}' not found in the plan.")
        self._df.loc[self._df['Attribute Name'] == attribute_name, 'Attribute Description'] = new_description

    def set_attribute_classification(self, attribute_name: str, new_classification: str):
        """Sets the classification for a specific attribute."""
        if new_classification not in ['Dimension', 'Measure']:
            raise ValueError("Classification must be either 'Dimension' or 'Measure'.")
        if attribute_name not in self._df['Attribute Name'].values:
            raise ValueError(f"Attribute '{attribute_name}' not found in the plan.")
        self._df.loc[self._df['Attribute Name'] == attribute_name, 'Attribute Classification'] = new_classification

    def disable_attribute(self, attribute_name: str):
        """Disables an attribute from the final output."""
        if attribute_name not in self._df['Attribute Name'].values:
            raise ValueError(f"Attribute '{attribute_name}' not found in the plan.")
        self._df.loc[self._df['Attribute Name'] == attribute_name, '_is_active'] = False

    def enable_attribute(self, attribute_name: str):
        """Enables an attribute for the final output."""
        if attribute_name not in self._df['Attribute Name'].values:
            raise ValueError(f"Attribute '{attribute_name}' not found in the plan.")
        self._df.loc[self._df['Attribute Name'] == attribute_name, '_is_active'] = True

    def to_df(self) -> pd.DataFrame:
        """Returns the final DataFrame with active attributes."""
        return self._df[self._df['_is_active']].drop(columns=['_is_active'])

    def __str__(self) -> str:
        """Provides a string representation of the data product plan."""
        if self._df.empty:
            return "Data Product Plan (empty)"

        name = self.name
        description = self.description
        
        attributes_str = ""
        for _, row in self._df.iterrows():
            status = "" if row['_is_active'] else " (Disabled)"
            attributes_str += f"  - {row['Attribute Name']}{status} ({row['Attribute Classification']}): {row['Attribute Description']}\n"

        return (
            f"Data Product: {name}\n"
            f"Description: {description}\n"
            f"Attributes:\n{attributes_str}"
        )

    def _repr_html_(self) -> str:
        """Provides a rich HTML representation for Jupyter notebooks."""
        if self._df.empty:
            return "<div><b>Data Product Plan (empty)</b></div>"

        name = self.name
        description = self.description

        html = "<div>"
        html += f"  <h3>Data Product: {name}</h3>"
        html += f"  <p><b>Description:</b> {description}</p>"
        html += "  <h4>Attributes:</h4>"
        html += "  <table border=\"1\" style=\"width:100%; border-collapse: collapse;\">"
        html += "    <tr><th>Attribute Name</th><th>Classification</th><th>Description</th><th>Status</th></tr>"
        for _, row in self._df.iterrows():
            status = "Active" if row['_is_active'] else "Disabled"
            html += "    <tr>"
            html += f"      <td>{row['Attribute Name']}</td>"
            html += f"      <td>{row['Attribute Classification']}</td>"
            html += f"      <td>{row['Attribute Description']}</td>"
            html += f"      <td>{status}</td>"
            html += "    </tr>"
        html += "  </table>"
        html += "</div>"
        return html

    def display(self):
        """Prints the string representation of the plan."""
        print(str(self))