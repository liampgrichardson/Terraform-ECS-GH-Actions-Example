import boto3
import pandas as pd
from botocore.exceptions import ClientError
pd.set_option('display.max_columns', None)


def query_last_day(client, database_name, table_name):
    # Query to fetch the last record to one day before the last record
    query = f"""
        WITH last_record_time AS (
            SELECT MAX(time) AS last_time
            FROM "{database_name}"."{table_name}"
        )
        SELECT * 
        FROM "{database_name}"."{table_name}"
        WHERE time BETWEEN TIMESTAMPADD('MILLISECOND', -86400000, (SELECT last_time FROM last_record_time))
                       AND (SELECT last_time FROM last_record_time)
        ORDER BY time DESC
    """

    try:
        paginator = client.get_paginator("query")
        response_iterator = paginator.paginate(QueryString=query)

        rows = []
        columns = None

        for response in response_iterator:
            if "ColumnInfo" in response and not columns:
                columns = [col["Name"] for col in response["ColumnInfo"]]
            for row in response["Rows"]:
                rows.append([
                    datum.get("ScalarValue") for datum in row["Data"]
                ])

        if columns and rows:
            # Create DataFrame
            df = pd.DataFrame(rows, columns=columns)
            # Reorganize data to create new columns for each measure_name
            df_pivot = df.pivot_table(index='time', columns='measure_name', values=[col for col in df.columns if col.startswith('measure_value::')], aggfunc='first')
            df_pivot.columns = df_pivot.columns.droplevel(0)
            return df_pivot
        else:
            print("No data retrieved.")
            return None

    except ClientError as e:
        print(f"Error querying data: {e}")
        return None


def main():
    database_name = "my-timestream-database"  # Replace with your Timestream database name
    table_name = "TestTable"  # Replace with your desired table name

    # Initialize boto3 client
    timestream_client = boto3.client("timestream-query", region_name="eu-west-1")  # Replace region if necessary

    # Query the last day's data
    df = query_last_day(timestream_client, database_name, table_name)

    if df is not None:
        print("\nData retrieved from Timestream:")
        print(df)
        print("\nDataframe column structure:")
        print(df.columns)
        print("\nDataframe first value:")
        print(df.iloc[0])
        print("\nDataframe last value:")
        print(df.iloc[-1])
        # Optionally save to a file
        df.to_csv("last_day_data.csv", index=False)
        print("Data saved to 'last_day_data.csv'.")


if __name__ == "__main__":
    main()
