USE [POSDb]
GO
/****** Object:  Table [dbo].[appointments]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[appointments](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[customer_id] [int] NULL,
	[employee_id] [int] NULL,
	[service_type] [nvarchar](100) NULL,
	[appointment_date] [date] NOT NULL,
	[appointment_time] [time](7) NOT NULL,
	[status] [nvarchar](50) NULL DEFAULT ('pending'),
	[notes] [nvarchar](1000) NULL,
	[created_at] [datetime] NULL DEFAULT (getdate()),
	[updated_at] [datetime] NULL DEFAULT (getdate()),
	[service_id] [int] NULL,
	[duration_minutes] [int] NULL DEFAULT ((30)),
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[Auxiliary]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Auxiliary](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[LedgerId] [int] NOT NULL,
	[ParentId] [int] NULL,
	[AccountNumber] [int] NOT NULL,
	[GroupAccountId] [int] NULL,
	[JobAccountId] [int] NULL,
	[ShortCut] [nvarchar](50) NULL,
	[Name] [nvarchar](100) NOT NULL,
	[Status] [int] NOT NULL,
	[UpdateDate] [datetime] NOT NULL,
	[TimeStamp] [timestamp] NOT NULL,
 CONSTRAINT [PK_Auxiliary] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[Auxiliary_temp]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Auxiliary_temp](
	[id] [int] NOT NULL,
	[LedgerId] [int] NOT NULL,
	[ParentId] [int] NULL,
	[AccountNumber] [int] NOT NULL,
	[GroupAccountId] [int] NULL,
	[JobAccountId] [int] NULL,
	[ShortCut] [nvarchar](50) NULL,
	[Name] [nvarchar](100) NOT NULL,
	[Status] [int] NOT NULL,
	[UpdateDate] [datetime] NOT NULL,
	[TimeStamp] [timestamp] NOT NULL
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[cash_drawer]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[cash_drawer](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[current_balance] [decimal](10, 2) NULL DEFAULT ((0.00)),
	[last_updated] [datetime] NULL DEFAULT (getdate()),
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[cash_drawer_operations]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[cash_drawer_operations](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[operation_date] [datetime] NULL DEFAULT (getdate()),
	[operation_type] [nvarchar](10) NULL,
	[amount] [decimal](10, 2) NOT NULL,
	[user_id] [int] NULL,
	[notes] [nvarchar](255) NULL,
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[categories]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[categories](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[category_name] [nvarchar](100) NOT NULL,
	[description] [nvarchar](500) NULL,
	[created_at] [datetime] NULL DEFAULT (getdate()),
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[company_info]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[company_info](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[company_name] [varchar](255) NOT NULL,
	[address] [varchar](255) NULL,
	[city] [varchar](100) NULL,
	[state] [varchar](100) NULL,
	[zip_code] [varchar](20) NULL,
	[phone] [varchar](50) NULL,
	[email] [varchar](100) NULL,
	[website] [varchar](100) NULL,
	[logo_path] [varchar](255) NULL,
	[created_at] [datetime] NULL DEFAULT (getdate()),
	[updated_at] [datetime] NULL DEFAULT (getdate()),
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
SET ANSI_PADDING OFF
GO
/****** Object:  Table [dbo].[currencies]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[currencies](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[currency_code] [varchar](10) NOT NULL,
	[currency_name] [varchar](100) NOT NULL,
	[symbol] [varchar](10) NULL,
	[exchange_rate] [decimal](15, 6) NULL DEFAULT ((1.000000)),
	[is_active] [bit] NULL DEFAULT ((1)),
	[created_at] [datetime] NULL DEFAULT (getdate()),
	[updated_at] [datetime] NULL DEFAULT (getdate()),
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY],
UNIQUE NONCLUSTERED 
(
	[currency_code] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
SET ANSI_PADDING OFF
GO
/****** Object:  Table [dbo].[customer_receipt]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[customer_receipt](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[manual_reference] [varchar](255) NULL,
	[payment_date] [datetime] NULL,
	[customer_id] [int] NULL,
	[amount] [decimal](10, 2) NULL,
	[payment_method] [varchar](50) NULL,
	[status] [varchar](50) NULL,
	[notes] [text] NULL,
	[created_at] [datetime] NULL DEFAULT (getdate()),
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]

GO
SET ANSI_PADDING OFF
GO
/****** Object:  Table [dbo].[customers]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[customers](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[customer_name] [nvarchar](200) NOT NULL,
	[email] [nvarchar](100) NULL,
	[phone] [nvarchar](20) NULL,
	[address] [nvarchar](500) NULL,
	[city] [nvarchar](100) NULL,
	[state] [nvarchar](100) NULL,
	[balance] [decimal](10, 2) NULL,
	[zip_code] [nvarchar](20) NULL,
	[created_at] [datetime] NULL CONSTRAINT [DF__customers__creat__31EC6D26]  DEFAULT (getdate()),
	[is_active] [bit] NULL CONSTRAINT [DF__customers__is_ac__32E0915F]  DEFAULT ((1)),
 CONSTRAINT [PK__customer__3213E83FF18CDA1E] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY],
 CONSTRAINT [UQ__customer__AB6E6164C3F4D776] UNIQUE NONCLUSTERED 
(
	[email] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[employees]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[employees](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[first_name] [nvarchar](100) NOT NULL,
	[last_name] [nvarchar](100) NOT NULL,
	[email] [nvarchar](100) NULL,
	[phone] [nvarchar](20) NULL,
	[address] [nvarchar](500) NULL,
	[city] [nvarchar](100) NULL,
	[state] [nvarchar](100) NULL,
	[zip_code] [nvarchar](20) NULL,
	[hire_date] [date] NOT NULL,
	[position] [nvarchar](100) NOT NULL,
	[department] [nvarchar](100) NULL,
	[salary] [decimal](10, 2) NULL,
	[role_id] [int] NULL,
	[is_active] [bit] NULL DEFAULT ((1)),
	[termination_date] [date] NULL,
	[created_at] [datetime] NULL DEFAULT (getdate()),
	[updated_at] [datetime] NULL DEFAULT (getdate()),
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY],
UNIQUE NONCLUSTERED 
(
	[email] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[expense_types]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[expense_types](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[expense_type_name] [varchar](100) NOT NULL,
	[description] [varchar](255) NULL,
	[created_at] [datetime] NULL DEFAULT (getdate()),
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
SET ANSI_PADDING OFF
GO
/****** Object:  Table [dbo].[expenses]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[expenses](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[expense_date] [date] NOT NULL,
	[expense_type] [varchar](100) NOT NULL,
	[description] [varchar](255) NULL,
	[amount] [decimal](10, 2) NOT NULL,
	[payment_method] [varchar](50) NULL DEFAULT ('Cash'),
	[payment_status] [varchar](20) NULL DEFAULT ('completed'),
	[invoice_number] [varchar](50) NULL,
	[notes] [text] NULL,
	[created_by] [varchar](100) NULL,
	[created_at] [datetime] NULL DEFAULT (getdate()),
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]

GO
SET ANSI_PADDING OFF
GO
/****** Object:  Table [dbo].[Ledger]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Ledger](
	[Id] [int] IDENTITY(1,1) NOT NULL,
	[AccountNumber] [int] NOT NULL,
	[SubNumber] [int] NULL,
	[ParentId] [int] NULL,
	[Name_en] [nvarchar](100) NOT NULL,
	[Name_fr] [nvarchar](100) NOT NULL,
	[Name_ar] [nvarchar](100) NOT NULL,
	[UpdateDate] [datetime] NOT NULL,
	[Status] [int] NULL,
	[TimeStamp] [timestamp] NOT NULL,
 CONSTRAINT [PK_Ledger] PRIMARY KEY CLUSTERED 
(
	[Id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[price_cost_date_history]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[price_cost_date_history](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[product_id] [int] NOT NULL,
	[old_price] [decimal](10, 2) NULL,
	[new_price] [decimal](10, 2) NULL,
	[old_cost_price] [decimal](10, 2) NULL,
	[new_cost_price] [decimal](10, 2) NULL,
	[change_date] [datetime] NULL DEFAULT (getdate()),
	[changed_by] [nvarchar](100) NULL,
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[products]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[products](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[product_name] [nvarchar](200) NOT NULL,
	[barcode] [nvarchar](50) NULL,
	[sku] [nvarchar](50) NULL,
	[description] [nvarchar](1000) NULL,
	[category_id] [int] NULL,
	[price] [decimal](10, 2) NOT NULL,
	[cost_price] [decimal](10, 2) NULL,
	[stock_quantity] [int] NULL DEFAULT ((0)),
	[min_stock_level] [int] NULL DEFAULT ((0)),
	[max_stock_level] [int] NULL DEFAULT ((0)),
	[supplier_id] [int] NULL,
	[created_at] [datetime] NULL DEFAULT (getdate()),
	[updated_at] [datetime] NULL DEFAULT (getdate()),
	[is_active] [bit] NULL DEFAULT ((1)),
	[photo] [nvarchar](500) NULL,
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY],
UNIQUE NONCLUSTERED 
(
	[barcode] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY],
UNIQUE NONCLUSTERED 
(
	[sku] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[purchase_items]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[purchase_items](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[purchase_id] [int] NOT NULL,
	[barcode] [varchar](50) NULL,
	[product_id] [int] NOT NULL,
	[quantity] [int] NOT NULL,
	[unit_cost] [decimal](10, 2) NOT NULL,
	[total_cost] [decimal](10, 2) NOT NULL,
	[unit_price] [decimal](10, 2) NULL,
	[profit] [decimal](10, 2) NULL,
	[discount_amount] [decimal](10, 2) NULL CONSTRAINT [DF__purchase___disco__0B91BA14]  DEFAULT ((0)),
	[created_at] [datetime] NULL CONSTRAINT [DF__purchase___creat__0C85DE4D]  DEFAULT (getdate()),
 CONSTRAINT [PK__purchase__3213E83FB633E5CD] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
SET ANSI_PADDING OFF
GO
/****** Object:  Table [dbo].[purchase_payment]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[purchase_payment](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[purchase_id] [int] NOT NULL,
	[purchase_invoice_number] [nvarchar](50) NOT NULL,
	[total_amount] [decimal](10, 2) NOT NULL,
	[purchase_date] [datetime] NOT NULL,
	[created_date] [datetime] NULL DEFAULT (getdate()),
	[supplier_id] [int] NOT NULL,
	[status] [nvarchar](50) NULL DEFAULT ('pending'),
	[amount_paid] [decimal](10, 2) NOT NULL,
	[payment_method] [nvarchar](50) NULL,
	[debit] [decimal](10, 2) NULL,
	[credit] [decimal](10, 2) NULL,
	[notes] [nvarchar](1000) NULL,
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[purchases]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[purchases](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[purchase_date] [datetime] NULL DEFAULT (getdate()),
	[supplier_id] [int] NULL,
	[subtotal] [decimal](10, 2) NOT NULL,
	[discount_amount] [decimal](10, 2) NULL DEFAULT ((0)),
	[tax_amount] [decimal](10, 2) NULL DEFAULT ((0)),
	[total_amount] [decimal](10, 2) NOT NULL,
	[payment_method] [nvarchar](50) NULL,
	[payment_status] [nvarchar](50) NULL DEFAULT ('completed'),
	[invoice_number] [nvarchar](50) NULL,
	[notes] [nvarchar](1000) NULL,
	[created_at] [datetime] NULL DEFAULT (getdate()),
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY],
UNIQUE NONCLUSTERED 
(
	[invoice_number] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[role_permissions]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[role_permissions](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[role_id] [int] NOT NULL,
	[page_name] [varchar](100) NOT NULL,
	[can_access] [bit] NULL DEFAULT ((1)),
	[created_at] [datetime] NULL DEFAULT (getdate()),
	[updated_at] [datetime] NULL DEFAULT (getdate()),
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY],
UNIQUE NONCLUSTERED 
(
	[role_id] ASC,
	[page_name] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
SET ANSI_PADDING OFF
GO
/****** Object:  Table [dbo].[roles]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[roles](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[name] [varchar](100) NOT NULL,
	[description] [varchar](255) NULL,
	[created_at] [datetime] NULL DEFAULT (getdate()),
	[updated_at] [datetime] NULL DEFAULT (getdate()),
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY],
UNIQUE NONCLUSTERED 
(
	[name] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
SET ANSI_PADDING OFF
GO
/****** Object:  Table [dbo].[sale_items]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[sale_items](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[sales_id] [int] NOT NULL,
	[barcode] [varchar](50) NULL,
	[product_id] [int] NOT NULL,
	[quantity] [int] NOT NULL,
	[unit_price] [decimal](10, 2) NOT NULL,
	[total_price] [decimal](10, 2) NOT NULL,
	[discount_amount] [decimal](10, 2) NULL CONSTRAINT [DF__sale_item__disco__3E52440B]  DEFAULT ((0)),
	[created_at] [datetime] NULL CONSTRAINT [DF__sale_item__creat__3F466844]  DEFAULT (getdate()),
 CONSTRAINT [PK__sale_ite__3213E83F07C1E0FE] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
SET ANSI_PADDING OFF
GO
/****** Object:  Table [dbo].[sales]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[sales](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[sale_date] [datetime] NULL CONSTRAINT [DF__sales__sale_date__36B12243]  DEFAULT (getdate()),
	[customer_id] [int] NULL,
	[subtotal] [decimal](10, 2) NOT NULL,
	[discount_amount] [decimal](10, 2) NULL CONSTRAINT [DF__sales__discount___37A5467C]  DEFAULT ((0)),
	[tax_amount] [decimal](10, 2) NULL CONSTRAINT [DF__sales__tax_amoun__38996AB5]  DEFAULT ((0)),
	[total_amount] [decimal](10, 2) NOT NULL,
	[payment_method] [nvarchar](50) NULL,
	[payment_status] [nvarchar](50) NULL CONSTRAINT [DF__sales__payment_s__398D8EEE]  DEFAULT ('completed'),
	[invoice_number] [nvarchar](50) NULL,
	[notes] [nvarchar](1000) NULL,
	[created_at] [datetime] NULL CONSTRAINT [DF__sales__created_a__3A81B327]  DEFAULT (getdate()),
 CONSTRAINT [PK__sales__3213E83FD961DD78] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY],
 CONSTRAINT [UQ__sales__8081A63AB834C4B7] UNIQUE NONCLUSTERED 
(
	[invoice_number] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[sales_payment]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[sales_payment](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[sales_id] [int] NOT NULL,
	[customer_id] [int] NOT NULL,
	[invoice_number] [nvarchar](50) NOT NULL,
	[total_amount] [decimal](10, 2) NOT NULL,
	[sale_date] [datetime] NOT NULL,
	[payment_status] [nvarchar](50) NULL DEFAULT ('pending'),
	[debit] [decimal](10, 2) NOT NULL DEFAULT ((0)),
	[credit] [decimal](10, 2) NOT NULL DEFAULT ((0)),
	[notes] [nvarchar](1000) NULL,
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[services]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[services](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[service_name] [nvarchar](100) NOT NULL,
	[description] [nvarchar](500) NULL,
	[duration_minutes] [int] NULL DEFAULT ((30)),
	[price] [decimal](10, 2) NULL,
	[is_active] [bit] NULL DEFAULT ((1)),
	[created_at] [datetime2](7) NULL DEFAULT (getdate()),
	[updated_at] [datetime2](7) NULL DEFAULT (getdate()),
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[stock_operation_items]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[stock_operation_items](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[operation_id] [int] NOT NULL,
	[product_id] [int] NOT NULL,
	[barcode] [nvarchar](50) NULL,
	[product_name] [nvarchar](200) NOT NULL,
	[previous_quantity] [int] NOT NULL,
	[adjusted_quantity] [int] NOT NULL,
	[operation_type] [nvarchar](20) NOT NULL,
	[reason] [nvarchar](500) NULL,
	[created_at] [datetime] NULL DEFAULT (getdate()),
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[stock_operations]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[stock_operations](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[operation_date] [datetime] NULL DEFAULT (getdate()),
	[user_id] [int] NOT NULL,
	[operation_type] [nvarchar](50) NOT NULL,
	[reference_number] [nvarchar](100) NULL,
	[notes] [nvarchar](1000) NULL,
	[total_items] [int] NULL DEFAULT ((0)),
	[created_at] [datetime] NULL DEFAULT (getdate()),
	[updated_at] [datetime] NULL DEFAULT (getdate()),
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[supplier_payment]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[supplier_payment](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[manual_reference] [nvarchar](100) NULL,
	[payment_date] [datetime] NULL DEFAULT (getdate()),
	[supplier_id] [int] NOT NULL,
	[amount] [decimal](10, 2) NOT NULL,
	[payment_method] [nvarchar](50) NULL,
	[status] [nvarchar](50) NULL DEFAULT ('completed'),
	[notes] [nvarchar](1000) NULL,
	[created_at] [datetime] NULL DEFAULT (getdate()),
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[suppliers]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[suppliers](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[name] [nvarchar](200) NOT NULL,
	[contact_person] [nvarchar](100) NULL,
	[email] [nvarchar](100) NULL,
	[phone] [nvarchar](20) NULL,
	[address] [nvarchar](500) NULL,
	[city] [nvarchar](100) NULL,
	[state] [nvarchar](100) NULL,
	[zip_code] [nvarchar](20) NULL,
	[country] [nvarchar](100) NULL CONSTRAINT [DF__suppliers__count__47DBAE45]  DEFAULT ('USA'),
	[balance] [decimal](10, 2) NULL,
	[created_at] [datetime] NULL,
	[updated_at] [datetime] NULL CONSTRAINT [DF__suppliers__creat__48CFD27E]  DEFAULT (getdate()),
	[is_active] [bit] NULL CONSTRAINT [DF__suppliers__is_ac__49C3F6B7]  DEFAULT ((1)),
 CONSTRAINT [PK__supplier__3213E83FBADECA74] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[user_sessions]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[user_sessions](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[user_id] [int] NOT NULL,
	[login_date] [date] NOT NULL,
	[login_time] [datetime] NOT NULL,
	[logout_date] [date] NULL,
	[logout_time] [datetime] NULL,
	[session_duration_minutes] [int] NULL,
	[created_at] [datetime] NULL DEFAULT (getdate()),
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[users]    Script Date: 2025-09-13 1:59:47 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[users](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[username] [varchar](255) NOT NULL,
	[password] [varchar](255) NOT NULL,
	[date_created] [datetime] NULL CONSTRAINT [DF__users__date_crea__44FF419A]  DEFAULT (getdate()),
	[session] [varchar](255) NULL,
	[login_time] [datetime] NULL,
	[logout_time] [datetime] NULL,
	[role] [int] NOT NULL,
 CONSTRAINT [PK__users__3213E83F8800625A] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY],
 CONSTRAINT [UQ__users__F3DBC572C2C8A83A] UNIQUE NONCLUSTERED 
(
	[username] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
SET ANSI_PADDING OFF
GO
ALTER TABLE [dbo].[appointments]  WITH CHECK ADD FOREIGN KEY([customer_id])
REFERENCES [dbo].[customers] ([id])
GO
ALTER TABLE [dbo].[appointments]  WITH CHECK ADD FOREIGN KEY([employee_id])
REFERENCES [dbo].[employees] ([id])
GO
ALTER TABLE [dbo].[appointments]  WITH CHECK ADD  CONSTRAINT [FK_appointments_service_id] FOREIGN KEY([service_id])
REFERENCES [dbo].[services] ([id])
GO
ALTER TABLE [dbo].[appointments] CHECK CONSTRAINT [FK_appointments_service_id]
GO
ALTER TABLE [dbo].[appointments]  WITH CHECK ADD  CONSTRAINT [FK_appointments_services] FOREIGN KEY([service_id])
REFERENCES [dbo].[services] ([id])
GO
ALTER TABLE [dbo].[appointments] CHECK CONSTRAINT [FK_appointments_services]
GO
ALTER TABLE [dbo].[cash_drawer_operations]  WITH CHECK ADD FOREIGN KEY([user_id])
REFERENCES [dbo].[users] ([id])
GO
ALTER TABLE [dbo].[customer_receipt]  WITH CHECK ADD FOREIGN KEY([customer_id])
REFERENCES [dbo].[customers] ([id])
GO
ALTER TABLE [dbo].[price_cost_date_history]  WITH CHECK ADD FOREIGN KEY([product_id])
REFERENCES [dbo].[products] ([id])
GO
ALTER TABLE [dbo].[products]  WITH CHECK ADD FOREIGN KEY([category_id])
REFERENCES [dbo].[categories] ([id])
GO
ALTER TABLE [dbo].[purchase_items]  WITH CHECK ADD  CONSTRAINT [FK__purchase___produ__0E6E26BF] FOREIGN KEY([product_id])
REFERENCES [dbo].[products] ([id])
GO
ALTER TABLE [dbo].[purchase_items] CHECK CONSTRAINT [FK__purchase___produ__0E6E26BF]
GO
ALTER TABLE [dbo].[purchase_items]  WITH CHECK ADD  CONSTRAINT [FK__purchase___purch__0D7A0286] FOREIGN KEY([purchase_id])
REFERENCES [dbo].[purchases] ([id])
GO
ALTER TABLE [dbo].[purchase_items] CHECK CONSTRAINT [FK__purchase___purch__0D7A0286]
GO
ALTER TABLE [dbo].[purchase_payment]  WITH CHECK ADD FOREIGN KEY([purchase_id])
REFERENCES [dbo].[purchases] ([id])
GO
ALTER TABLE [dbo].[purchase_payment]  WITH CHECK ADD FOREIGN KEY([supplier_id])
REFERENCES [dbo].[suppliers] ([id])
GO
ALTER TABLE [dbo].[purchases]  WITH CHECK ADD  CONSTRAINT [FK__purchases__suppl__08B54D69] FOREIGN KEY([supplier_id])
REFERENCES [dbo].[suppliers] ([id])
GO
ALTER TABLE [dbo].[purchases] CHECK CONSTRAINT [FK__purchases__suppl__08B54D69]
GO
ALTER TABLE [dbo].[role_permissions]  WITH CHECK ADD FOREIGN KEY([role_id])
REFERENCES [dbo].[roles] ([id])
GO
ALTER TABLE [dbo].[sale_items]  WITH CHECK ADD  CONSTRAINT [FK__sale_item__produ__412EB0B6] FOREIGN KEY([product_id])
REFERENCES [dbo].[products] ([id])
GO
ALTER TABLE [dbo].[sale_items] CHECK CONSTRAINT [FK__sale_item__produ__412EB0B6]
GO
ALTER TABLE [dbo].[sale_items]  WITH CHECK ADD  CONSTRAINT [FK__sale_item__sale___403A8C7D] FOREIGN KEY([sales_id])
REFERENCES [dbo].[sales] ([id])
GO
ALTER TABLE [dbo].[sale_items] CHECK CONSTRAINT [FK__sale_item__sale___403A8C7D]
GO
ALTER TABLE [dbo].[sales]  WITH CHECK ADD  CONSTRAINT [FK__sales__customer___3B75D760] FOREIGN KEY([customer_id])
REFERENCES [dbo].[customers] ([id])
GO
ALTER TABLE [dbo].[sales] CHECK CONSTRAINT [FK__sales__customer___3B75D760]
GO
ALTER TABLE [dbo].[sales_payment]  WITH CHECK ADD FOREIGN KEY([customer_id])
REFERENCES [dbo].[customers] ([id])
GO
ALTER TABLE [dbo].[sales_payment]  WITH CHECK ADD FOREIGN KEY([sales_id])
REFERENCES [dbo].[sales] ([id])
GO
ALTER TABLE [dbo].[stock_operation_items]  WITH CHECK ADD FOREIGN KEY([operation_id])
REFERENCES [dbo].[stock_operations] ([id])
GO
ALTER TABLE [dbo].[stock_operation_items]  WITH CHECK ADD FOREIGN KEY([product_id])
REFERENCES [dbo].[products] ([id])
GO
ALTER TABLE [dbo].[supplier_payment]  WITH CHECK ADD FOREIGN KEY([supplier_id])
REFERENCES [dbo].[suppliers] ([id])
GO
ALTER TABLE [dbo].[user_sessions]  WITH CHECK ADD FOREIGN KEY([user_id])
REFERENCES [dbo].[users] ([id])
GO
ALTER TABLE [dbo].[users]  WITH CHECK ADD  CONSTRAINT [FK_users_roles] FOREIGN KEY([role])
REFERENCES [dbo].[roles] ([id])
GO
ALTER TABLE [dbo].[users] CHECK CONSTRAINT [FK_users_roles]
GO
ALTER TABLE [dbo].[cash_drawer_operations]  WITH CHECK ADD CHECK  (([operation_type]='Out' OR [operation_type]='In'))
GO
