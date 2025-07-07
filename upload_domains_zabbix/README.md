# Zabbix Host Management Script

A Python script to automatically create and manage hosts in Zabbix from Google Sheets data.

## Features

- Read host data from Google Sheets
- Automatically create hosts in Zabbix with:
  - Domain/hostname
  - Host groups
  - Templates
  - Web scenarios with health check URLs
- Update processing status to Google Sheets
- Handle errors when host already exists and display existing group information
- Detailed logging for debugging

## System Requirements

- Python 3.7+
- Zabbix API access
- Google Service Account with Google Sheets access

## File Structure
├── upload_hosts.py          # Main script
├── api-zabbix.json         # Google Service Account credentials
├── requirements.txt        # Python dependencies
└── README.md              # This documentation
## The Google Sheet containing the data will be upload to Zabbix:
    https://docs.google.com/spreadsheets/d/10Ml_kc3Wt3kMsaAnhR_RFcLg78ahteaLTvEBDuJoNw4/edit?gid=0#gid=0

## Installation
- Install dependencies
    pip install -r requirements.txt
- Update Google Sheet ID:
    sht = gs.open_by_key("your-google-sheet-id-here")
- Run the script:
    python3 upload_hosts.py