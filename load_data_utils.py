"""
Utility module for loading customer and product data from database tables
"""

from connection import connection

class LoadDataUtils:
    """
    Utility class for loading customer and product data from database tables
    """
    
    @staticmethod
    def load_customers():
        """
        Load all customer data from the customer table
        
        Returns:
            list: List of dictionaries containing customer data
        """
        try:
            sql = """
            SELECT 
                id, 
                customerName, 
                Address, 
                phone, 
                Email, 
                refernceBy, 
                mof, 
                vat, 
                project, 
                firstsalesdate, 
                lastpaymentdate, 
                lastsalesdate, 
                balanceLL, 
                balanceusd
            FROM customer 
            ORDER BY id DESC
            """
            
            customers = []
            connection.contogetrows(sql, customers)
            
            # Convert to list of dictionaries for easier access
            customer_list = []
            for customer in customers[0] if customers else []:
                customer_dict = {
                    'id': customer[0],
                    'customerName': customer[1],
                    'Address': customer[2],
                    'phone': customer[3],
                    'Email': customer[4],
                    'refernceBy': customer[5],
                    'mof': customer[6],
                    'vat': customer[7],
                    'project': customer[8],
                    'firstsalesdate': customer[9],
                    'lastpaymentdate': customer[10],
                    'lastsalesdate': customer[11],
                    'balanceLL': customer[12],
                    'balanceusd': customer[13]
                }
                customer_list.append(customer_dict)
            
            return customer_list
            
        except Exception as ex:
            print(f"Error loading customers: {str(ex)}")
            return []
    
    @staticmethod
    def load_products():
        """
        Load all product data from the products table
        
        Returns:
            list: List of dictionaries containing product data
        """
        try:
            sql = """
            SELECT 
                p.id,
                p.ProductName,
                s.Name as SupplierName,
                c.category_name as CategoryName,
                p.Price,
                p.Quantity,
                p.Cost,
                p.CostAmt,
                p.Status,
                p.Vat,
                p.Priceht,
                p.ProductImage
            FROM Product p
            INNER JOIN Supplier s ON p.Supplier = s.id
            INNER JOIN category c ON p.Category = c.id
            ORDER BY p.id DESC
            """
            
            products = []
            connection.contogetrows(sql, products)
            
            # Convert to list of dictionaries for easier access
            product_list = []
            for product in products[0] if products else []:
                product_dict = {
                    'id': product[0],
                    'ProductName': product[1],
                    'SupplierName': product[2],
                    'CategoryName': product[3],
                    'Price': product[4],
                    'Quantity': product[5],
                    'Cost': product[6],
                    'CostAmt': product[7],
                    'Status': product[8],
                    'Vat': product[9],
                    'Priceht': product[10],
                    'ProductImage': product[11]
                }
                product_list.append(product_dict)
            
            return product_list
            
        except Exception as ex:
            print(f"Error loading products: {str(ex)}")
            return []
    
    @staticmethod
    def load_customers_by_id(customer_id):
        """
        Load specific customer by ID
        
        Args:
            customer_id (int): Customer ID to load
            
        Returns:
            dict: Customer data dictionary or None if not found
        """
        try:
            sql = """
            SELECT 
                id, 
                customerName, 
                Address, 
                phone, 
                Email, 
                refernceBy, 
                mof, 
                vat, 
                project, 
                firstsalesdate, 
                lastpaymentdate, 
                lastsalesdate, 
                balanceLL, 
                balanceusd
            FROM customer 
            WHERE id = ?
            """
            
            customer_data = []
            connection.contogetrows(sql, customer_data)
            
            if customer_data and customer_data[0]:
                customer = customer_data[0][0]
                return {
                    'id': customer[0],
                    'customerName': customer[1],
                    'Address': customer[2],
                    'phone': customer[3],
                    'Email': customer[4],
                    'refernceBy': customer[5],
                    'mof': customer[6],
                    'vat': customer[7],
                    'project': customer[8],
                    'firstsalesdate': customer[9],
                    'lastpaymentdate': customer[10],
                    'lastsalesdate': customer[11],
                    'balanceLL': customer[12],
                    'balanceusd': customer[13]
                }
            
            return None
            
        except Exception as ex:
            print(f"Error loading customer by ID: {str(ex)}")
            return None
    
    @staticmethod
    def load_products_by_id(product_id):
        """
        Load specific product by ID
        
        Args:
            product_id (int): Product ID to load
            
        Returns:
            dict: Product data dictionary or None if not found
        """
        try:
            sql = """
            SELECT 
                p.id,
                p.ProductName,
                s.Name as SupplierName,
                c.category_name as CategoryName,
                p.Price,
                p.Quantity,
                p.Cost,
                p.CostAmt,
                p.Status,
                p.Vat,
                p.Priceht,
                p.ProductImage
            FROM Product p
            INNER JOIN Supplier s ON p.Supplier = s.id
            INNER JOIN category c ON p.Category = c.id
            WHERE p.id = ?
            """
            
            product_data = []
            connection.contogetrows(sql, product_data)
            
            if product_data and product_data[0]:
                product = product_data[0][0]
                return {
                    'id': product[0],
                    'ProductName': product[1],
                    'SupplierName': product[2],
                    'CategoryName': product[3],
                    'Price': product[4],
                    'Quantity': product[5],
                    'Cost': product[6],
                    'CostAmt': product[7],
                    'Status': product[8],
                    'Vat': product[9],
                    'Priceht': product[10],
                    'ProductImage': product[11]
                }
            
            return None
            
        except Exception as ex:
            print(f"Error loading product by ID: {str(ex)}")
            return None
    
    @staticmethod
    def load_active_products():
        """
        Load only active products
        
        Returns:
            list: List of dictionaries containing active product data
        """
        try:
            sql = """
            SELECT 
                p.id,
                p.ProductName,
                s.Name as SupplierName,
                c.category_name as CategoryName,
                p.Price,
                p.Quantity,
                p.Cost,
                p.CostAmt,
                p.Status,
                p.Vat,
                p.Priceht,
                p.ProductImage
            FROM Product p
            INNER JOIN Supplier s ON p.Supplier = s.id
            INNER JOIN category c ON p.Category = c.id
            WHERE p.Status = 'Active'
            ORDER BY p.id DESC
            """
            
            products = []
            connection.contogetrows(sql, products)
            
            # Convert to list of dictionaries for easier access
            product_list = []
            for product in products[0] if products else []:
                product_dict = {
                    'id': product[0],
                    'ProductName': product[1],
                    'SupplierName': product[2],
                    'CategoryName': product[3],
                    'Price': product[4],
                    'Quantity': product[5],
                    'Cost': product[6],
                    'CostAmt': product[7],
                    'Status': product[8],
                    'Vat': product[9],
                    'Priceht': product[10],
                    'ProductImage': product[11]
                }
                product_list.append(product_dict)
            
            return product_list
            
        except Exception as ex:
            print(f"Error loading active products: {str(ex)}")
            return []

# Example usage and testing
if __name__ == "__main__":
    # Test loading customers
    customers = LoadDataUtils.load_customers()
    print(f"Loaded {len(customers)} customers")
    if customers:
        print("First customer:", customers[0])
    
    # Test loading products
    products = LoadDataUtils.load_products()
    print(f"Loaded {len(products)} products")
    if products:
        print("First product:", products[0])
    
    # Test loading specific customer
    customer = LoadDataUtils.load_customers_by_id(1)
    print("Customer by ID 1:", customer)
    
    # Test loading specific product
    product = LoadDataUtils.load_products_by_id(1)
    print("Product by ID 1:", product)
    
    # Test loading active products
    active_products = LoadDataUtils.load_active_products()
    print(f"Loaded {len(active_products)} active products")
