from datetime import datetime
from connection import connection
import traceback

class TrialBalanceReportGenerator:
    """
    Expert ERP Trial Balance Report Engine with Bottom-Up Totals and Grand Balance.
    Ensures all joins are string-based to prevent conversion crashes.
    """

    def __init__(self, from_date, to_date, company_name="ManagementOS", short_name="nave", account_filter=None):
        self.from_date = from_date
        self.to_date = to_date
        self.company_name = company_name
        self.short_name = short_name
        self.account_filter = account_filter
        self.timestamp = datetime.now().strftime("%d-%b-%Y %H:%M:%S")

    def fetch_raw_data(self):
        sql = """
            SELECT 
                COALESCE(CAST(ax_num.number AS VARCHAR(50)), CAST(ax_id.number AS VARCHAR(50)), CAST(l.AccountNumber AS VARCHAR(50))) as full_code,
                COALESCE(CAST(ax_num.account_name AS VARCHAR(255)), CAST(ax_id.account_name AS VARCHAR(255)), CAST(l.Name_en AS VARCHAR(255))) as account_name,
                NULL as currency_symbol,
                1.0 as exchange_rate,
                atl.debit,
                atl.credit,
                CAST(atl.account_number AS VARCHAR(50)) as ledger_base
            FROM accounting_transaction_lines atl
            INNER JOIN accounting_transactions at 
                ON CAST(atl.jv_id AS VARCHAR(50)) = CAST(at.jv_id AS VARCHAR(50))
            LEFT JOIN auxiliary ax_num 
                ON CAST(atl.auxiliary_id AS VARCHAR(50)) = CAST(ax_num.number AS VARCHAR(50))
            LEFT JOIN auxiliary ax_id 
                ON CAST(atl.auxiliary_id AS VARCHAR(50)) = CAST(ax_id.id AS VARCHAR(50))
            LEFT JOIN Ledger l 
                ON CAST(atl.account_number AS VARCHAR(50)) = CAST(l.AccountNumber AS VARCHAR(50))
            WHERE 1=1
        """
        params = []
        if self.from_date:
            sql += " AND CAST(at.transaction_date AS DATE) >= ?"
            params.append(self.from_date)
        if self.to_date:
            sql += " AND CAST(at.transaction_date AS DATE) <= ?"
            params.append(self.to_date)
        if self.account_filter:
            sql += " AND (CAST(atl.account_number AS VARCHAR(50)) LIKE ? OR CAST(ax_num.number AS VARCHAR(50)) LIKE ? OR CAST(ax_id.number AS VARCHAR(50)) LIKE ?)"
            f = f"{self.account_filter}%"; params.extend([f, f, f])

        data = []
        try: connection.contogetrows_with_params(sql, data, tuple(params))
        except Exception as e: raise e
        
        headers = ['full_code', 'account_name', 'currency', 'exchange_rate', 'debit_true', 'credit_true', 'ledger_base']
        rows = []
        for r in data:
            rd = dict(zip(headers, r))
            for k in ['debit_true', 'credit_true', 'exchange_rate']: rd[k] = float(rd[k] or 0)
            rd['debit_3'] = rd['debit_true'] * rd['exchange_rate']
            rd['credit_3'] = rd['credit_true'] * rd['exchange_rate']
            rows.append(rd)
        return rows

    def process_hierarchy(self, raw_rows):
        if not raw_rows: return []

        leaf_aggregates = {}
        for row in raw_rows:
            code = row['full_code'] or row['ledger_base'] or "UNKNOWN"
            name = row['account_name'] or "Unknown Account"
            key = (code, name, "USD")
            if key not in leaf_aggregates:
                leaf_aggregates[key] = {'debit_true': 0.0, 'credit_true': 0.0, 'debit_3': 0.0, 'credit_3': 0.0}
            leaf_aggregates[key]['debit_true'] += row['debit_true']
            leaf_aggregates[key]['credit_true'] += row['credit_true']
            leaf_aggregates[key]['debit_3'] += row['debit_3']
            leaf_aggregates[key]['credit_3'] += row['credit_3']

        hierarchy_totals = {}
        for (code, name, cy), vals in leaf_aggregates.items():
            base = str(code).split('.')[0]
            for i in range(len(base), 0, -1):
                p = base[:i]
                if p not in hierarchy_totals:
                    hierarchy_totals[p] = {'debit_true': 0.0, 'credit_true': 0.0, 'debit_3': 0.0, 'credit_3': 0.0}
                hierarchy_totals[p]['debit_true'] += vals['debit_true']
                hierarchy_totals[p]['credit_true'] += vals['credit_true']
                hierarchy_totals[p]['debit_3'] += vals['debit_3']
                hierarchy_totals[p]['credit_3'] += vals['credit_3']

        leaf_codes = {k[0] for k in leaf_aggregates.keys()}
        unique_codes = sorted(list(leaf_codes | set(hierarchy_totals.keys())))
        
        tree = {}
        for code in unique_codes:
            if '.' in code: parent = code.split('.')[0]
            else: parent = code[:-1] if len(code) > 1 else None
            if parent not in tree: tree[parent] = []
            tree[parent].append(code)

        report_data = []
        def traverse(code):
            if code is None: return
            if code in leaf_codes:
                matches = [k for k in leaf_aggregates.keys() if k[0] == code]
                for key in matches:
                    vals = leaf_aggregates[key]
                    report_data.append(self.format_row(code, key[1], key[2], vals['debit_true'], vals['credit_true'], vals['debit_3'], vals['credit_3'], is_summary=False))
            if code in tree:
                for child in sorted(tree[code]): traverse(child)
                stats = hierarchy_totals[code]
                name = self.get_ledger_name(code)
                report_data.append(self.format_row(f"TOTAL {code}", name, '', stats['debit_true'], stats['credit_true'], stats['debit_3'], stats['credit_3'], is_summary=True))
            elif code not in leaf_codes and code in hierarchy_totals:
                stats = hierarchy_totals[code]
                name = self.get_ledger_name(code)
                report_data.append(self.format_row(f"TOTAL {code}", name, '', stats['debit_true'], stats['credit_true'], stats['debit_3'], stats['credit_3'], is_summary=True))

        grand_debit = 0.0; grand_credit = 0.0
        if None in tree:
            for root_code in sorted(tree[None]):
                traverse(root_code)
                # Calculate Grand Totals based on root types (Level 1)
                stats = hierarchy_totals[root_code]
                grand_debit += stats['debit_true']
                grand_credit += stats['credit_true']

        # GRAND TOTAL LINE
        diff = abs(grand_debit - grand_credit)
        status = " (BALANCED)" if diff < 0.01 else f" (OUT OF BALANCE: {diff:,.2f})"
        report_data.append(self.format_row("GRAND TOTAL", status, '', grand_debit, grand_credit, grand_debit, grand_credit, is_summary=True))
        
        return report_data

    def get_ledger_name(self, code):
        try:
            res = []
            connection.contogetrows("SELECT CAST(Name_en AS VARCHAR(255)) FROM Ledger WHERE CAST(AccountNumber AS VARCHAR(50)) = ?", res, (str(code),))
            return res[0][0] if res else "Summary Account"
        except: return "Summary Account"

    def format_row(self, code, name, cy, d_t, c_t, d_3, c_3, is_summary=False):
        bt = d_t - c_t
        b3 = d_3 - c_3
        def fmtr(v): return f"{v:,.2f}" if v else "0.00"
        return {
            'Description': f"{code} {name}", 'Cy': cy or 'USD',
            'Debit true': fmtr(d_t), 'Credit true': fmtr(c_t), 'Balance Debit true': fmtr(max(0.0, bt)), 'Balance Credit true': fmtr(max(0.0, -bt)),
            'Debit 3': fmtr(d_t), 'Credit 3 ref': fmtr(c_t), 'Balance Debit 3': fmtr(max(0.0, b3)), 'Balance Credit 3': fmtr(max(0.0, -b3)),
            'is_summary': is_summary
        }
