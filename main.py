import sys
import pandas as pd


def main():
    if len(sys.argv) < 2:
        print("Usage: py main.py <csv_file>")
        sys.exit(1)

    csv_file = sys.argv[1]

    try:
        # Read CSV
        df = pd.read_csv(csv_file)

        # Clean column names
        df.columns = (
            df.columns
            .str.strip()
            .str.replace("\ufeff", "", regex=False)
        )

        # Required columns
        required_columns = [
            "Net Sales",
            "Tender_Type",
            "Item Description"
        ]

        for column in required_columns:
            if column not in df.columns:
                print(f"\nERROR: Column '{column}' not found.")
                print("\nColumns found in CSV:")

                for col in df.columns:
                    print(f" - {repr(col)}")

                sys.exit(1)

        # ----------------------------------------
        # CLEAN NET SALES
        # ----------------------------------------

        df["Net Sales"] = (
            df["Net Sales"]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("₱", "", regex=False)
            .str.strip()
        )

        df["Net Sales"] = pd.to_numeric(
            df["Net Sales"],
            errors="coerce"
        ).fillna(0)

        # ----------------------------------------
        # CLEAN TENDER TYPE
        # ----------------------------------------

        df["Tender_Type_Clean"] = (
            df["Tender_Type"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        # ----------------------------------------
        # SALES SUMMARY
        # ----------------------------------------

        total_net_sales = df["Net Sales"].sum()

        cash_net_sales = df.loc[
            df["Tender_Type_Clean"].str.contains(
                "cash",
                case=False,
                na=False
            ),
            "Net Sales"
        ].sum()

        card_net_sales = df.loc[
            df["Tender_Type_Clean"].str.contains(
                "card",
                case=False,
                na=False
            ),
            "Net Sales"
        ].sum()

        # ----------------------------------------
        # DISPLAY SUMMARY
        # ----------------------------------------

        print()
        print("=" * 60)
        print("SALES SUMMARY")
        print("=" * 60)

        print(f"Total Net Sales       : {total_net_sales:,.2f}")
        print(f"Cash Net Sales        : {cash_net_sales:,.2f}")
        print(f"Credit Card Net Sales : {card_net_sales:,.2f}")

        print("=" * 60)

        # ----------------------------------------
        # DESCRIPTION WARNING
        # ----------------------------------------

        print()
        print("=" * 60)
        print("DESCRIPTION WARNING")
        print("=" * 60)

        warning_count = 0

        for index, row in df.iterrows():

            description = str(row["Item Description"]).strip()

            if "-" in description:

                warning_count += 1

                print(
                    f"WARNING: Row {index + 2} | "
                    f"Description: {description}"
                )

        if warning_count == 0:
            print("No description warnings found.")

        print("=" * 60)

        print(f"\nTotal warnings: {warning_count}")

    except FileNotFoundError:
        print(f"ERROR: File not found:")
        print(csv_file)
        sys.exit(1)

    except pd.errors.EmptyDataError:
        print("ERROR: CSV file is empty.")
        sys.exit(1)

    except pd.errors.ParserError as e:
        print(f"ERROR reading CSV: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()