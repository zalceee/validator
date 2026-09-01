import pandas as pd
import sys
import os

if len(sys.argv) != 3:
    print("Usage:")
    print("py dsr.py <csv_file> <date>")
    print()
    print("Example:")
    print("py dsr.py dsr-kiosk.csv 2026-01-13")
    sys.exit(1)


input_file = sys.argv[1]
target_date_input = sys.argv[2]


try:
    target_date = pd.to_datetime(
        target_date_input,
        format="%Y-%m-%d"
    ).date()

except Exception:
    print(f"Invalid date: {target_date_input}")
    print("Please use YYYY-MM-DD")
    print("Example: 2026-01-13")
    sys.exit(1)


# ============================================================
# CHECK INPUT FILE
# ============================================================

if not os.path.exists(input_file):
    print(f"File not found: {input_file}")
    sys.exit(1)


# ============================================================
# READ CSV
# ============================================================

try:
    df = pd.read_csv(
        input_file,
        dtype=str,
        keep_default_na=False
    )

except Exception as e:
    print(f"Error reading CSV:")
    print(e)
    sys.exit(1)


# ============================================================
# CLEAN COLUMN NAMES
# ============================================================

df.columns = (
    df.columns
    .str.replace("**", "", regex=False)
    .str.replace("\xa0", " ", regex=False)
    .str.strip()
    .str.replace(r"\s+", " ", regex=True)
)


# ============================================================
# REQUIRED COLUMNS
# ============================================================

required_columns = [
    "Date",
    "Manual SI Number",
    "Cashier",
    "Barcode",
    "LOT",
    "Item Description",
    "Quantity",
    "Price w/ Tax",
    "Gross Sales",
    "Discount Amount",
    "Disc Reason/ Promo Code",
    "Net Sales",
    "Amount Paid",
    "Tender Type",
    "Type of Card",
    "Approval Code",
    "Loyalty Card Number"
]


missing_columns = [
    col for col in required_columns
    if col not in df.columns
]


if missing_columns:

    print()
    print("Missing required columns:")
    print("----------------------------------------")

    for col in missing_columns:
        print(f"- {col}")

    print()
    print("Available columns:")
    print("----------------------------------------")

    for col in df.columns:
        print(f"- {col}")

    sys.exit(1)


# ============================================================
# CLEAN DATE
# ============================================================

df["Date"] = pd.to_datetime(
    df["Date"],
    errors="coerce"
)


# ============================================================
# FILTER BY DATE
# ============================================================

df = df[
    df["Date"].dt.date == target_date
].copy()


if df.empty:

    print()
    print("========================================")
    print("NO DATA FOUND")
    print("========================================")
    print(f"Date: {target_date}")
    print("========================================")

    sys.exit(0)


# ============================================================
# CLEAN TEXT COLUMNS
# ============================================================

text_columns = [
    "Manual SI Number",
    "Cashier",
    "Barcode",
    "LOT",
    "Item Description",
    "Disc Reason/ Promo Code",
    "Tender Type",
    "Type of Card",
    "Approval Code",
    "Loyalty Card Number"
]


for col in text_columns:

    df[col] = (
        df[col]
        .astype(str)
        .str.strip()
    )


# ============================================================
# CLEAN MANUAL SI NUMBER
#
# Example:
#
# 2686.0 -> 2686
# 10533.0 -> 10533
# ============================================================

def clean_si(value):

    if value == "":
        return ""

    try:

        number = float(value)

        if number.is_integer():
            return str(int(number))

        return str(number)

    except Exception:

        return value


df["Manual SI Number"] = (
    df["Manual SI Number"]
    .apply(clean_si)
)


# ============================================================
# CLEAN BARCODE
#
# Example:
#
# 7890732316370.0 -> 7890732316370
# ============================================================

def clean_barcode(value):

    if value == "":
        return ""

    try:

        number = float(value)

        if number.is_integer():
            return str(int(number))

        return str(number)

    except Exception:

        return value


df["Barcode"] = (
    df["Barcode"]
    .apply(clean_barcode)
)


# ============================================================
# CLEAN NUMERIC COLUMNS
# ============================================================

numeric_columns = [
    "Quantity",
    "Price w/ Tax",
    "Gross Sales",
    "Discount Amount",
    "Net Sales",
    "Amount Paid"
]


for col in numeric_columns:

    df[col] = (
        df[col]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
    )

    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )


# ============================================================
# CLEAN ITEM DESCRIPTION
#
# Example:
#
# SLIM-PINK FEVER-37/38
# ->
# SLIM
#
# FLASH URBAN-ROSE GOLD-37/38
# ->
# FLASH URBAN
#
# HAVAIANAS 2024 PAPER BAG
# ->
# HAVAIANAS 2024 PAPER BAG
# ============================================================

def clean_description(value):

    value = str(value).strip()

    if "-" in value:

        return value.split("-", 1)[0].strip()

    return value


df["Item Description"] = (
    df["Item Description"]
    .apply(clean_description)
)


# ============================================================
# HANDLE SPLIT PAYMENTS
#
# Same Manual SI Number = ONE TRANSACTION
#
# Example:
#
# Manual SI    Amount Paid    Tender
# 2542         1100           Credit Card
# 2542            1           Cash
#
# Output:
#
# Manual SI    Net Sales      Tender
# 2542         1100           Credit Card
# 2542            1           Cash
#
# Instead of:
#
# 2542         1099           Credit Card
# 2542            2           Cash
# ============================================================


# Count payment rows per Manual SI Number
payment_count = (
    df.groupby("Manual SI Number")["Amount Paid"]
    .transform("count")
)


# Calculate total Amount Paid per Manual SI Number
total_amount_paid = (
    df.groupby("Manual SI Number")["Amount Paid"]
    .transform("sum")
)


# Identify split-payment transactions
split_payment = (
    (payment_count > 1)
    &
    (total_amount_paid > 0)
)


# Use Amount Paid as Net Sales for split payments
df.loc[
    split_payment,
    "Net Sales"
] = (
    df.loc[
        split_payment,
        "Amount Paid"
    ]
)


# ============================================================
# CREATE DATE FORMAT
#
# Example:
#
# 2026-01-13
# ->
# 1/13/2026
#
# This is the normal Short Date style when opened in Excel.
# ============================================================

df["Date"] = df["Date"].apply(
    lambda x:
        f"{x.month}/{x.day}/{x.year}"
        if pd.notna(x)
        else ""
)


# ============================================================
# FORMAT WHOLE NUMBERS
#
# 1099.0 -> 1099
# 2.0    -> 2
# blank  -> blank
# ============================================================

def whole_number(value):

    if pd.isna(value):
        return ""

    try:

        value = float(value)

        if value.is_integer():
            return str(int(value))

        return str(value)

    except Exception:

        return str(value)


for col in [
    "Quantity",
    "Price w/ Tax",
    "Gross Sales",
    "Discount Amount",
    "Net Sales"
]:

    df[col] = (
        df[col]
        .apply(whole_number)
    )


# ============================================================
# CREATE OUTPUT DATAFRAME
# ============================================================

output = pd.DataFrame()


output["Date"] = df["Date"]


output["Manual SI Number"] = (
    df["Manual SI Number"]
)


output["Cashier"] = (
    df["Cashier"]
)


output["Barcode"] = (
    df["Barcode"]
)


output["LOT"] = (
    df["LOT"]
)


output["Item Description"] = (
    df["Item Description"]
)


output["Quantity"] = (
    df["Quantity"]
)


output["Item Price"] = (
    df["Price w/ Tax"]
)


output["Gross Sales"] = (
    df["Gross Sales"]
)


output["Discount Amount"] = (
    df["Discount Amount"]
)


output["Disc Reason|Promo Code"] = (
    df["Disc Reason/ Promo Code"]
)


output["Net Sales"] = (
    df["Net Sales"]
)


output["Tender_Type"] = (
    df["Tender Type"]
)


output["Type_of_Card"] = (
    df["Type of Card"]
)


output["Approval_Code"] = (
    df["Approval Code"]
)


# These fields are not present in the source CSV
output["Card_Expiry_Month"] = ""


output["Card_Expiry_Year"] = ""


output["Charge_Net_Days"] = ""


# Loyalty Card Number -> Customer_ID
output["Customer_ID"] = (
    df["Loyalty Card Number"]
)


# ============================================================
# CALCULATE TOTALS
# ============================================================

# Convert output Net Sales to numeric
net_sales_numeric = pd.to_numeric(
    output["Net Sales"],
    errors="coerce"
).fillna(0)


# ------------------------------------------------------------
# TOTAL NET SALES
# ------------------------------------------------------------

total_net_sales = (
    net_sales_numeric.sum()
)


# ------------------------------------------------------------
# CASH NET SALES
# ------------------------------------------------------------

cash_mask = (
    output["Tender_Type"]
    .astype(str)
    .str.strip()
    .str.lower()
    == "cash"
)


cash_net_sales = (
    net_sales_numeric[cash_mask]
    .sum()
)


# ------------------------------------------------------------
# CREDIT CARD NET SALES
# ------------------------------------------------------------

credit_card_mask = (
    output["Tender_Type"]
    .astype(str)
    .str.strip()
    .str.lower()
    .isin([
        "credit card",
        "creditcard"
    ])
)


credit_card_net_sales = (
    net_sales_numeric[credit_card_mask]
    .sum()
)


# ============================================================
# CREATE OUTPUT FILE NAME
# ============================================================

output_file = (
    f"{target_date.strftime('%Y-%m-%d')}_INVC.csv"
)


# ============================================================
# SAVE CSV
# ============================================================

try:

    output.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

except Exception as e:

    print()
    print("Error saving CSV:")
    print(e)

    sys.exit(1)


# ============================================================
# DISPLAY SUMMARY
# ============================================================

print()
print("="*50)
print("        INVC CSV CREATED")
print("="*50)

print(
    f"Source File           : {input_file}"
)

print(
    f"Date                  : {target_date}"
)

print(
    f"Manual SI Count       : {output['Manual SI Number'].nunique():,}"
)

print(
    f"Manual SI Start       : {output['Manual SI Number'].min()}"
)

print(
    f"Manual SI End         : {output['Manual SI Number'].max()}"
)

print(
    f"Output File           : {output_file}"
)

print("-"*50)

print(
    f"Total Net Sales       : {total_net_sales:,.2f}"
)

print(
    f"Cash Net Sales        : {cash_net_sales:,.2f}"
)


print(
    f"Credit Card Net Sales : {credit_card_net_sales:,.2f}"
)

print("="*50)
