# advanced_reports.py
class AdvancedFinancialReports:
    
    @staticmethod
    def income_statement(from_date, to_date, compare_with_previous=False):
        """Generate Profit & Loss Statement"""
        result = {
            'revenue': {
                'sales': 0,
                'services': 0,
                'other_income': 0
            },
            'cost_of_goods': {
                'purchases': 0,
                'inventory_change': 0
            },
            'expenses': {
                'operating': [],
                'administrative': [],
                'selling': []
            },
            'gross_profit': 0,
            'net_profit': 0
        }
        
        # Revenue from sales
        sales_data = []
        connection.contogetrows("""
            SELECT 
                SUM(total_amount) as total_sales,
                SUM(discount_amount) as discounts,
                COUNT(*) as transaction_count
            FROM sales 
            WHERE sale_date BETWEEN ? AND ? 
            AND payment_status = 'completed'
        """, sales_data, (from_date, to_date))
        
        # Service revenue if applicable
        service_data = []
        connection.contogetrows("""
            SELECT SUM(amount) FROM appointments 
            WHERE appointment_date BETWEEN ? AND ?
            AND status = 'completed'
        """, service_data, (from_date, to_date))
        
        # Categorize expenses by type
        expense_data = []
        connection.contogetrows("""
            SELECT et.expense_type_name, SUM(e.amount)
            FROM expenses e
            JOIN expense_types et ON e.expense_type = et.expense_type_name
            WHERE e.expense_date BETWEEN ? AND ?
            GROUP BY et.expense_type_name
        """, expense_data, (from_date, to_date))
        
        return result
    
    @staticmethod
    def balance_sheet(as_of_date):
        """Generate Balance Sheet"""
        return {
            'assets': {
                'current_assets': {
                    'cash': 0,
                    'accounts_receivable': 0,
                    'inventory': 0
                },
                'fixed_assets': {
                    'equipment': 0,
                    'furniture': 0,
                    'accumulated_depreciation': 0
                }
            },
            'liabilities': {
                'current_liabilities': {
                    'accounts_payable': 0,
                    'accrued_expenses': 0
                },
                'long_term_liabilities': {}
            },
            'equity': {
                'retained_earnings': 0,
                'current_earnings': 0
            }
        }
    
    @staticmethod
    def cash_flow_statement(from_date, to_date):
        """Generate Cash Flow Statement with operating, investing, financing activities"""
        cash_flow = {
            'operating_activities': {
                'net_income': 0,
                'depreciation': 0,
                'changes_in_receivables': 0,
                'changes_in_payables': 0,
                'changes_in_inventory': 0
            },
            'investing_activities': {
                'asset_purchases': 0,
                'asset_sales': 0
            },
            'financing_activities': {
                'capital_investments': 0,
                'dividends': 0
            },
            'net_cash_flow': 0,
            'beginning_cash': 0,
            'ending_cash': 0
        }
        return cash_flow