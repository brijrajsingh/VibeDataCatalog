"""
Generate sample Excel files for testing preview functionality
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_sample_excel_files():
    """Create a variety of Excel files for testing the preview functionality"""
    print("Generating sample Excel files for testing...")
    
    # 1. Simple tabular data
    df_simple = pd.DataFrame({
        'Name': ['John Smith', 'Jane Doe', 'Robert Johnson', 'Emily Williams', 'Michael Brown'],
        'Age': [34, 28, 45, 32, 51],
        'Department': ['IT', 'Marketing', 'Finance', 'HR', 'Operations'],
        'Salary': [75000, 65000, 85000, 60000, 78000],
        'Hire Date': [
            datetime.now() - timedelta(days=365*2),
            datetime.now() - timedelta(days=180),
            datetime.now() - timedelta(days=365*5),
            datetime.now() - timedelta(days=365*1),
            datetime.now() - timedelta(days=365*3)
        ]
    })
    
    df_simple.to_excel('sample_simple.xlsx', index=False)
    print("✓ Created simple Excel file: sample_simple.xlsx")
    
    # 2. Large dataset
    num_rows = 1000
    df_large = pd.DataFrame({
        'ID': range(1, num_rows + 1),
        'Random Number': np.random.randint(1, 1000, size=num_rows),
        'Random Float': np.random.uniform(0, 100, size=num_rows),
        'Category': np.random.choice(['A', 'B', 'C', 'D', 'E'], size=num_rows),
        'Boolean': np.random.choice([True, False], size=num_rows),
        'Date': [datetime.now() - timedelta(days=i) for i in range(num_rows)]
    })
    
    df_large.to_excel('sample_large.xlsx', index=False)
    print("✓ Created large Excel file: sample_large.xlsx")
    
    # 3. Multiple sheets
    with pd.ExcelWriter('sample_multiple_sheets.xlsx') as writer:
        # First sheet - Sales data
        df_sales = pd.DataFrame({
            'Product': ['Product A', 'Product B', 'Product C', 'Product D', 'Product E'],
            'Q1 Sales': [1200, 1500, 950, 2000, 1800],
            'Q2 Sales': [1300, 1450, 1100, 1950, 1700],
            'Q3 Sales': [1250, 1600, 1050, 2100, 1600],
            'Q4 Sales': [1400, 1700, 1200, 2200, 1900]
        })
        df_sales.to_excel(writer, sheet_name='Sales', index=False)
        
        # Second sheet - Customer data
        df_customers = pd.DataFrame({
            'Customer ID': range(1, 6),
            'Customer Name': ['ABC Corp', 'XYZ Ltd', '123 Industries', 'Global Tech', 'Local Shop'],
            'Country': ['USA', 'UK', 'Canada', 'Australia', 'Germany'],
            'Active': [True, True, False, True, True]
        })
        df_customers.to_excel(writer, sheet_name='Customers', index=False)
        
        # Third sheet - Time series
        dates = pd.date_range(start='2023-01-01', periods=30, freq='D')
        df_time = pd.DataFrame({
            'Date': dates,
            'Value': np.random.normal(loc=100, scale=15, size=30)
        })
        df_time.to_excel(writer, sheet_name='Time Series', index=False)
    
    print("✓ Created Excel file with multiple sheets: sample_multiple_sheets.xlsx")
    
    # 4. Excel with various data types
    df_types = pd.DataFrame({
        'Text': ['Plain text', 'With numbers 123', 'With symbols @#$%', 'Very long text ' * 10, ''],
        'Integer': [1, 100, -50, 1000000, 0],
        'Float': [1.23, 45.67, -89.01, 3.14159, 0.0],
        'Date': [datetime.now(), datetime.now() - timedelta(days=1), datetime.now() + timedelta(days=1), 
                datetime(2000, 1, 1), datetime(2030, 12, 31)],
        'Boolean': [True, False, True, False, True],
        'Formula': ['=A2+B2', '=SUM(B2:B6)', '=AVERAGE(C2:C6)', '=TODAY()', '=IF(E2=TRUE,"Yes","No")']
    })
    
    df_types.to_excel('sample_data_types.xlsx', index=False)
    print("✓ Created Excel file with various data types: sample_data_types.xlsx")
    
    print("\nAll sample Excel files created successfully!")
    print("You can upload these files to test the Excel preview functionality in the data catalog.")

if __name__ == "__main__":
    create_sample_excel_files()
