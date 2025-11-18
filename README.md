
# Veracode Audit Log Exporter

This project provides a Python script that retrieves **Veracode Audit Log** data through the **Veracode Reporting REST API**.
It supports full extraction across any date range, handles the API’s asynchronous report generation, and automatically splits long ranges into API-safe six-month windows.
All results are combined and saved into a structured JSON file.

---

## Features

* Generates Veracode **AUDIT** reports for any date range
* Automatically handles asynchronous report processing
* Splits ranges longer than six months into consecutive windows
* Combines all report data into a single JSON output
* Minimal setup and easy to integrate into automation pipelines

---

## Prerequisites

1. **Python 3.8 or later**
2. Install required packages:

   ```bash
   pip install requests veracode-api-signing
   ```
3. Configure Veracode API credentials:

   Create the credentials file:

   **Linux/macOS:**

   ```
   mkdir -p ~/.veracode
   nano ~/.veracode/credentials
   ```

   **Windows:**

   ```
   mkdir %USERPROFILE%\.veracode
   notepad %USERPROFILE%\.veracode\credentials
   ```

   Add:

   ```
   [default]
   veracode_api_key_id = YOUR_API_ID
   veracode_api_key_secret = YOUR_API_KEY
   ```

---

## Usage

Run the script with a required start date and an optional end date:

```bash
python script.py --start-date 2025-08-25 --end-date 2025-11-18
```

The script accepts the following arguments:

| Argument          | Description                                         |
| ----------------- | --------------------------------------------------- |
| `--start-date`    | Required. Start date (YYYY-MM-DD).                  |
| `--end-date`      | Optional. End date (YYYY-MM-DD). Defaults to today. |
| `--sleep`         | Delay between window requests. Default: 1 second.   |
| `--poll-interval` | Delay between status checks. Default: 5 seconds.    |
| `--max-polls`     | Maximum status checks per report. Default: 40.      |

All results are saved to a file named:

```
veracode_audit_<start>_to_<end>.json
```

---

## Output

The output JSON contains, for each window:

* The date window used
* The generated report metadata
* The complete contents of `audit_logs` returned by the API

---

## Notes

* The Veracode Reporting API returns data asynchronously; the script handles this automatically.
* The script uses HTTPS HMAC authentication via the `veracode-api-signing` library.


