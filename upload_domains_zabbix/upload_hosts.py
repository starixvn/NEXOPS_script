from pyzabbix import ZabbixAPI
import json
import traceback
import gspread

# Google Sheet configuration
gs = gspread.service_account("api-zabbix.json")
sht = gs.open_by_key("10Ml_kc3Wt3kMsaAnhR_RFcLg78ahteaLTvEBDuJoNw4")
worksheet = sht.sheet1  # Or sht.worksheet("Sheet1") if there's a specific name

# Zabbix configuration
ZABBIX_URL = "https://zabbix.nexdev.net"
ZABBIX_API_TOKEN = "592e96f767032d08e5f5faad359ae39cdfaac87b10998fd32c0cc9c6749fdece"

# Initialize Zabbix API connection with token authentication
zapi = ZabbixAPI(ZABBIX_URL)
zapi.login(api_token=ZABBIX_API_TOKEN)

def get_data_from_sheet():
    """Get data from Google Sheet"""
    try:
        # Get all data from sheet
        all_records = worksheet.get_all_records()
        
        if not all_records:
            print("No data found in Google Sheet")
            return []
            
        print(f"Found {len(all_records)} records in Google Sheet")
        return all_records
        
    except Exception as e:
        print(f"Error reading data from Google Sheet: {e}")
        return []

def update_status_in_sheet(row_index, status):
    """Update status column in Google Sheet"""
    try:
        # Find the Status column (assuming it exists or will be created)
        headers = worksheet.row_values(1)
        
        # Check if Status column exists
        if 'Status' not in headers:
            # Add Status column if it doesn't exist
            status_col = len(headers) + 1
            worksheet.update_cell(1, status_col, 'Status')
        else:
            status_col = headers.index('Status') + 1
        
        # Update the status for the specific row (row_index is 1-based, +1 for header)
        worksheet.update_cell(row_index + 2, status_col, status)
        print(f"  ✓ Updated Status column: {status}")
        
    except Exception as e:
        print(f"  ✗ Error updating status in sheet: {e}")

def get_hostgroup_ids(group_names):
    """Get host group IDs by names"""
    group_ids = []
    found_groups = []
    
    for group_name in group_names:
        try:
            groups = zapi.hostgroup.get(
                filter={"name": group_name},
                output=["groupid", "name"]
            )
            if groups:
                group_ids.append({"groupid": groups[0]['groupid']})
                found_groups.append(groups[0]['name'])
                print(f"✓ Found host group: {groups[0]['name']} (ID: {groups[0]['groupid']})")
            else:
                print(f"✗ Host group '{group_name}' not found!")
        except Exception as e:
            print(f"✗ Error getting host group '{group_name}': {e}")
    
    if not group_ids:
        print("\nNo valid host groups found. Available host groups:")
        try:
            all_groups = zapi.hostgroup.get(output=["groupid", "name"])
            for group in all_groups[:15]:  # Show first 15 groups
                print(f"  - {group['name']} (ID: {group['groupid']})")
        except Exception as e:
            print(f"Error listing host groups: {e}")
        return None, []
    
    return group_ids, found_groups

def get_template_ids(template_names):
    """Get template IDs by names"""
    template_ids = []
    found_templates = []
    
    for template_name in template_names:
        try:
            templates = zapi.template.get(
                filter={"host": template_name},
                output=["templateid", "host", "name"]
            )
            if templates:
                template_ids.append({"templateid": templates[0]['templateid']})
                found_templates.append(templates[0]['host'])
                print(f"✓ Found template: {templates[0]['host']} (ID: {templates[0]['templateid']})")
            else:
                print(f"✗ Template '{template_name}' not found!")
        except Exception as e:
            print(f"✗ Error getting template '{template_name}': {e}")
    
    if not template_ids:
        print("\nNo valid templates found. Available templates:")
        try:
            all_templates = zapi.template.get(output=["templateid", "host", "name"])
            for template in all_templates[:15]:  # Show first 15 templates
                print(f"  - {template['host']} (ID: {template['templateid']})")
        except Exception as e:
            print(f"Error listing templates: {e}")
        return None, []
    
    return template_ids, found_templates

def update_web_scenario_url(host_id, new_url):
    """Update the URL of the first step in a web scenario for a given host."""
    try:
        # Find web scenarios linked to the host
        httptests = zapi.httptest.get(
            hostids=[host_id],
            output="extend",
            selectSteps="extend"
        )
        
        if not httptests:
            print(f"  - No web scenarios found for host ID: {host_id}")
            return

        for httptest in httptests:
            httptestid = httptest['httptestid']
            scenario_name = httptest['name']
            steps = httptest['steps']
            
            if not steps:
                print(f"  - Web scenario '{scenario_name}' has no steps.")
                continue

            # Update the URL in the first step
            original_url = steps[0]['url']
            steps[0]['url'] = new_url
            
            print(f"  - Updating web scenario: '{scenario_name}' (ID: {httptestid})")
            print(f"    - Changing URL from: {original_url}")
            print(f"    - To new URL: {new_url}")

            # Only include the essential parameters for step updates
            clean_steps = []
            for step in steps:
                clean_step = {
                    'url': step.get('url', ''),
                    'timeout': step.get('timeout', '15'),
                    'posts': step.get('posts', ''),
                    'variables': step.get('variables', []),
                    'headers': step.get('headers', []),
                    'follow_redirects': step.get('follow_redirects', '1'),
                    'retrieve_mode': step.get('retrieve_mode', '0'),
                    'status_codes': step.get('status_codes', '200')
                }
                # Use 'httpstepid' instead of 'stepid' for templated scenarios
                if 'httpstepid' in step:
                    clean_step['httpstepid'] = step['httpstepid']
                elif 'stepid' in step:
                    clean_step['httpstepid'] = step['stepid']
                clean_steps.append(clean_step)

            # Update the web scenario with the modified steps
            zapi.httptest.update({
                "httptestid": httptestid,
                "steps": clean_steps
            })
            print(f"  ✓ Successfully updated web scenario '{scenario_name}'.")

    except Exception as e:
        print(f"✗ Error updating web scenario: {e}")
        traceback.print_exc()

def get_existing_host_groups(domain):
    """Get groups of an existing host by domain name"""
    try:
        print(f"  - Checking existing host groups for domain: {domain}")
        
        # Method 1: Get host with groups using selectGroups
        hosts = zapi.host.get(
            filter={"host": domain},
            output=["hostid", "host", "name"],
            selectGroups=["groupid", "name"]
        )
        
        if hosts and len(hosts) > 0:
            host = hosts[0]
            groups = host.get('groups', [])
            if groups:
                group_names = [group['name'] for group in groups]
                print(f"  - Found existing host '{domain}' in groups: {', '.join(group_names)}")
                return group_names
        
        # Method 2: Fallback - get host first, then get groups
        hosts = zapi.host.get(
            filter={"host": domain},
            output=["hostid", "host", "name"]
        )
        
        if hosts and len(hosts) > 0:
            host_id = hosts[0]['hostid']
            print(f"  - Found existing host '{domain}' with ID: {host_id}")
            
            # Get groups for this host
            host_groups = zapi.hostgroup.get(
                hostids=[host_id],
                output=["groupid", "name"]
            )
            
            if host_groups:
                group_names = [group['name'] for group in host_groups]
                print(f"  - Host belongs to groups: {', '.join(group_names)}")
                return group_names
            else:
                print(f"  - Host exists but no groups found")
                return []
        else:
            print(f"  - No existing host found for domain: {domain}")
            return []
            
    except Exception as e:
        print(f"  - Error getting existing host groups: {e}")
        return []

def process_host_from_sheet_data(record, row_index):
    """Process host creation from a Google Sheet record"""
    try:
        # Get data from corresponding columns
        domain = record.get('Domains', '').strip()
        groups_str = record.get('Groups', '').strip()
        templates_str = record.get('Templates', '').strip()
        health_check_path = record.get('Server health check', '').strip()
        
        if not domain:
            error_msg = "Missing domain"
            print(f"Skipping record due to missing domain: {record}")
            update_status_in_sheet(row_index, f"Failed: {error_msg}")
            return False
            
        # Convert groups and templates from string to list
        host_group_names = [g.strip() for g in groups_str.split(',') if g.strip()] if groups_str else []
        template_names = [t.strip() for t in templates_str.split(',') if t.strip()] if templates_str else []
        
        if not host_group_names:
            error_msg = "Missing host groups"
            print(f"Skipping domain {domain} due to missing host groups")
            update_status_in_sheet(row_index, f"Failed: {error_msg}")
            return False
            
        if not template_names:
            error_msg = "Missing templates"
            print(f"Skipping domain {domain} due to missing templates")
            update_status_in_sheet(row_index, f"Failed: {error_msg}")
            return False
        
        # Create health check URL using {HOSTNAME} format + path from Server health check column
        if health_check_path:
            # Ensure path starts with /
            if not health_check_path.startswith('/'):
                health_check_path = '/' + health_check_path
            # Use {HOSTNAME} placeholder instead of actual domain
            health_check_url = f"https://{{HOSTNAME}}{health_check_path}"
        else:
            health_check_url = ""
            
        print(f"\n" + "=" * 60)
        print(f"PROCESSING DOMAIN: {domain}")
        print(f"Host groups: {host_group_names}")
        print(f"Templates: {template_names}")
        print(f"Health check URL: {health_check_url}")
        print("=" * 60)
        
        # Get host group IDs
        group_ids, found_groups = get_hostgroup_ids(host_group_names)
        if not group_ids:
            error_msg = "No valid host groups found"
            print(f"Cannot create host {domain} because no valid host groups found")
            update_status_in_sheet(row_index, f"Failed: {error_msg}")
            return False
        
        # Get template IDs
        template_ids, found_templates = get_template_ids(template_names)
        if not template_ids:
            error_msg = "No valid templates found"
            print(f"Cannot create host {domain} because no valid templates found")
            update_status_in_sheet(row_index, f"Failed: {error_msg}")
            return False
        
        # Create host interface
        host_interface = {
            "type": 1,  # 1 is for agent
            "main": 1,
            "useip": 0,  # Use DNS name instead of IP
            "ip": "",
            "dns": domain,  # Use domain name
            "port": "10050"  # Default Zabbix agent port
        }
        
        # Create new host
        host_create = zapi.host.create({
            "host": domain,
            "name": domain,
            "groups": group_ids,
            "templates": template_ids,
            "interfaces": [host_interface]
        })
        
        new_host_id = host_create['hostids'][0]
        print(f"\n✓ Successfully created host with ID: {new_host_id}")
        print(f"✓ Host name: {domain}")
        print(f"✓ Using DNS resolution instead of IP")
        print(f"✓ Added to {len(found_groups)} host groups: {', '.join(found_groups)}")
        print(f"✓ Linked with {len(found_templates)} templates: {', '.join(found_templates)}")
        
        # Update web scenario URL if health check URL exists
        if health_check_url:
            print(f"\n--- UPDATING WEB SCENARIO FOR HOST: {domain} ---")
            update_web_scenario_url(new_host_id, health_check_url)
        else:
            print(f"\n--- No health check URL for host: {domain} ---")
        
        # Update status to Completed
        update_status_in_sheet(row_index, "Completed")
        return True
        
    except Exception as e:
        error_msg = str(e)
        
        # Check if error is about host already existing
        if "already exists" in error_msg.lower():
            print(f"\n✗ Host '{domain}' already exists in Zabbix")
            
            # Get existing host groups
            existing_groups = get_existing_host_groups(domain)
            
            if existing_groups:
                detailed_error = f"Host already exists in groups: {', '.join(existing_groups)}"
                print(f"✗ {detailed_error}")
                update_status_in_sheet(row_index, f"Failed: {detailed_error}")
            else:
                detailed_error = "Host already exists (unable to retrieve group information)"
                print(f"✗ {detailed_error}")
                update_status_in_sheet(row_index, f"Failed: {detailed_error}")
        else:
            print(f"✗ Error creating host from record {record}: {e}")
            traceback.print_exc()
            update_status_in_sheet(row_index, f"Failed: {error_msg}")
        
        return False

# Main execution
try:
    # Get data from Google Sheet
    print("Reading data from Google Sheet...")
    sheet_data = get_data_from_sheet()
    
    if not sheet_data:
        print("No data to process")
        exit(1)
    
    # Process each record
    successful_hosts = 0
    failed_hosts = 0
    
    for i, record in enumerate(sheet_data, 1):
        print(f"\n{'='*80}")
        print(f"PROCESSING RECORD {i}/{len(sheet_data)}")
        print(f"{'='*80}")
        
        if process_host_from_sheet_data(record, i-1):  # i-1 because enumerate starts from 1 but row index starts from 0
            successful_hosts += 1
        else:
            failed_hosts += 1
    
    # Summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"Total records: {len(sheet_data)}")
    print(f"Hosts created successfully: {successful_hosts}")
    print(f"Hosts creation failed: {failed_hosts}")
    print(f"{'='*80}")
    
except Exception as e:
    print(f"✗ General error: {e}")
    traceback.print_exc()
    exit(1)
