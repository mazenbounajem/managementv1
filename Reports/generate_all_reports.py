#!/usr/bin/env python3
"""
Script to generate all business reports using ReportLab
"""

import os
import sys
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def generate_sales_report():
    """Generate sales performance report"""
    try:
        from Reports.sales_performance_report import SalesPerformanceReport
        report = SalesPerformanceReport()
        success = report.generate_report("Reports/sales_performance_report.pdf")
        return success
    except Exception as e:
        print(f"Error generating sales report: {e}")
        return False

def generate_inventory_report():
    """Generate inventory report"""
    try:
        from Reports.inventory_report import InventoryReport
        report = InventoryReport()
        success = report.generate_report("Reports/inventory_report.pdf")
        return success
    except Exception as e:
        print(f"Error generating inventory report: {e}")
        return False

def generate_financial_report():
    """Generate financial report"""
    try:
        from Reports.financial_report import FinancialReport
        report = FinancialReport()
        success = report.generate_report("Reports/financial_report.pdf")
        return success
    except Exception as e:
        print(f"Error generating financial report: {e}")
        return False

def generate_stock_inventory_report():
    """Generate stock inventory report"""
    try:
        from stockreports.inventory_report import InventoryReport
        report = InventoryReport()
        success = report.generate_report("stockreports/inventory_report.pdf")
        return success
    except Exception as e:
        print(f"Error generating stock inventory report: {e}")
        return False

def generate_low_stock_alert_report():
    """Generate low stock alert report"""
    try:
        from stockreports.low_stock_alert_report import LowStockAlertReport
        report = LowStockAlertReport()
        success = report.generate_report("stockreports/low_stock_alert_report.pdf")
        return success
    except Exception as e:
        print(f"Error generating low stock alert report: {e}")
        return False

def generate_stock_movement_report():
    """Generate stock movement report"""
    try:
        from stockreports.stock_movement_report import StockMovementReport
        report = StockMovementReport()
        success = report.generate_report("stockreports/stock_movement_report.pdf")
        return success
    except Exception as e:
        print(f"Error generating stock movement report: {e}")
        return False

def generate_category_inventory_report():
    """Generate category inventory report"""
    try:
        from stockreports.category_inventory_report import CategoryInventoryReport
        report = CategoryInventoryReport()
        success = report.generate_report("stockreports/category_inventory_report.pdf")
        return success
    except Exception as e:
        print(f"Error generating category inventory report: {e}")
        return False

def main():
    """Main function to generate all reports"""
    print("=" * 50)
    print("Business Reports Generator")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Ensure Reports directory exists
    os.makedirs("Reports", exist_ok=True)

    reports = [
        ("Sales Performance Report", generate_sales_report),
        ("Inventory Report", generate_inventory_report),
        ("Financial Report", generate_financial_report),
        ("Stock Inventory Report", generate_stock_inventory_report),
        ("Low Stock Alert Report", generate_low_stock_alert_report),
        ("Stock Movement Report", generate_stock_movement_report),
        ("Category Inventory Report", generate_category_inventory_report)
    ]

    results = []

    for report_name, report_func in reports:
        print(f"Generating {report_name}...")
        try:
            success = report_func()
            if success:
                print(f"[SUCCESS] {report_name} generated successfully")
                results.append((report_name, "SUCCESS"))
            else:
                print(f"[FAILED] Failed to generate {report_name}")
                results.append((report_name, "FAILED"))
        except Exception as e:
            print(f"[ERROR] Error generating {report_name}: {e}")
            results.append((report_name, "ERROR"))
        print()

    # Summary
    print("=" * 50)
    print("Generation Summary:")
    print("=" * 50)

    for report_name, status in results:
        status_icon = "[OK]" if status == "SUCCESS" else "[FAIL]"
        print(f"{status_icon} {report_name}: {status}")

    successful_reports = sum(1 for _, status in results if status == "SUCCESS")
    print(f"\nTotal Reports Generated: {successful_reports}/{len(results)}")

    if successful_reports == len(results):
        print("\n[SUCCESS] All reports generated successfully!")
        print("Reports saved in the following folders:")
        print("[Reports folder]:")
        for report_name, status in results[:3]:  # First 3 are in Reports folder
            if status == "SUCCESS":
                filename = report_name.lower().replace(" ", "_") + ".pdf"
                print(f"  - Reports/{filename}")
        print("[stockreports folder]:")
        for report_name, status in results[3:]:  # Remaining are in stockreports folder
            if status == "SUCCESS":
                filename = report_name.lower().replace(" ", "_") + ".pdf"
                print(f"  - stockreports/{filename}")
    else:
        print(f"\n[WARNING] {len(results) - successful_reports} report(s) failed to generate.")

    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
