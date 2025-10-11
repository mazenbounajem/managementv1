from reports import Reports, export_csv

# Test the export_csv function directly
def test_csv_export():
    print("Testing CSV export function...")
    
    # Get some sample data
    data = Reports.fetch_expenses()
    print(f"Data length: {len(data)}")
    
    if data:
        headers = list(data[0].keys())
        headers = [h.replace('_', ' ').title() for h in headers]
        print(f"Headers: {headers}")
        print(f"First row: {data[0]}")
        
        # Test the export function
        try:
            csv_data = export_csv(data, headers)
            print(f"CSV data type: {type(csv_data)}")
            print(f"CSV data length: {len(csv_data)}")
            print("CSV export successful!")
        except Exception as e:
            print(f"Error in CSV export: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("No data to export")

if __name__ == "__main__":
    test_csv_export()
