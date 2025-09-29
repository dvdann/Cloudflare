from flask import Flask, render_template, request, jsonify
import requests
import json

app = Flask(__name__)


email = 'cf.ninjaplay88@gmail.com'  
api_key = '602166b6f19f52dbeff5cf454a5428a5df6a3'  


url_add_zone = "https://api.cloudflare.com/client/v4/zones"
url_add_dns = "https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
url_get_nameservers = "https://api.cloudflare.com/client/v4/zones/{zone_id}"
url_add_page_rule = "https://api.cloudflare.com/client/v4/zones/{zone_id}/pagerules"


headers = {
    "X-Auth-Email": email,
    "X-Auth-Key": api_key,
    "Content-Type": "application/json"
}

@app.route('/favicon.ico')
def favicon():
    return '', 204  # Mengembalikan status 204 (No Content), tanpa body

@app.route('/')
def index():
    return render_template('index.html')  # Menampilkan halaman utama dengan UI


@app.route('/add_domains', methods=['POST'])
def add_domains():
    try:
        data = request.get_json()

        if not data or 'domains' not in data:
            return jsonify({"error": "No domains provided"}), 400

        domains = data['domains']
        results = []
        
        for domain in domains:
            result = add_domain(domain)
            results.append(result)
        
        return jsonify({'results': results})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def add_domain(domain):
    try:
        data = {
            "name": domain,
            "jump_start": True  # Enable automatic configuration on add
        }

        response = requests.post(url_add_zone, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            zone_id = response.json()['result']['id']
            nameservers = get_nameservers(zone_id)  # Mendapatkan nameservers
            return {"domain": domain, "status": "Success", "zone_id": zone_id, "nameservers": nameservers}
        else:
            return {"domain": domain, "status": "Failed", "zone_id": None, "message": response.json().get("errors", "Unknown error")}

    except Exception as e:
        return {"domain": domain, "status": "Failed", "zone_id": None, "message": str(e)}


def get_nameservers(zone_id):
    url = url_get_nameservers.format(zone_id=zone_id)
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        nameservers = response.json()['result']['name_servers']
        return nameservers
    else:
        return ["Failed to get nameservers"]


@app.route('/add_dns_record', methods=['POST'])
def add_dns_record():
    try:
        data = request.get_json()

        if not data or 'zone_id' not in data or 'record_type' not in data or 'name' not in data or 'content' not in data:
            return jsonify({"error": "Invalid data"}), 400

        zone_id = data['zone_id']
        record_type = data['record_type']
        name = data['name']
        content = data['content']
        proxied = data.get('proxied', True)  # Optional: Whether to proxy the request through Cloudflare
        
      
        dns_data = {
            "type": record_type,
            "name": name,
            "content": content,
            "proxied": proxied
        }

       
        response = requests.post(url_add_dns.format(zone_id=zone_id), headers=headers, data=json.dumps(dns_data))

        if response.status_code == 200:
            return jsonify({"status": "Success", "message": "DNS record added successfully"})
        else:
            return jsonify({"status": "Failed", "message": response.json().get("errors", "Unknown error")})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/add_page_rule', methods=['POST'])
def add_page_rule():
    try:
        data = request.get_json()

        if not data or 'zone_id' not in data or 'domain_name' not in data or 'destination_url' not in data:
            return jsonify({"error": "Invalid data, zone_id, domain_name, and destination_url are required"}), 400

        zone_id = data['zone_id']  
        domain_name = data['domain_name']
        destination_url = data['destination_url']

        # Validasi destination_url
        if not destination_url.startswith('http://') and not destination_url.startswith('https://'):
            return jsonify({"error": "Invalid destination_url, it should start with http:// or https://"}), 400

        # Membuat source URL dengan www dan tanpa www
        source_url_with_www = f"www.{domain_name}/*"
        source_url_without_www = f"{domain_name}/*"

        # Page Rule 1: Redirect www.domain.com/* to destination_url
        page_rule_1 = {
            "targets": [
                {
                    "target": "url",
                    "constraint": {
                        "operator": "matches",
                        "value": source_url_with_www  
                    }
                }
            ],
            "actions": [
                {
                    "id": "forwarding_url",
                    "value": {
                        "url": destination_url,  
                        "status_code": 301  
                    }
                }
            ],
            "priority": 1,
            "status": "active"
        }

        # Page Rule 2: Redirect domain.com/* to destination_url
        page_rule_2 = {
            "targets": [
                {
                    "target": "url",
                    "constraint": {
                        "operator": "matches",
                        "value": source_url_without_www  
                    }
                }
            ],
            "actions": [
                {
                    "id": "forwarding_url",
                    "value": {
                        "url": destination_url,  
                        "status_code": 301  
                    }
                }
            ],
            "priority": 2,
            "status": "active"
        }

        # Kirim request untuk membuat Page Rule
        url_add_page_rule = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/pagerules"
        response_1 = requests.post(url_add_page_rule, headers=headers, data=json.dumps(page_rule_1))
        response_2 = requests.post(url_add_page_rule, headers=headers, data=json.dumps(page_rule_2))

        if response_1.status_code == 200 and response_2.status_code == 200:
            return jsonify({"status": "Success", "message": "Page Rules created successfully"})
        else:
            return jsonify({
                "status": "Failed", 
                "message": f"Error creating Page Rules. Status Code 1: {response_1.status_code}, Status Code 2: {response_2.status_code}, Message: {response_1.text}"
            }), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get_zone_details', methods=['POST'])
def get_zone_details_by_domain():
    try:
        data = request.get_json()

        domain_name = data.get("domain_name", "").strip()
        if not domain_name:
            return jsonify({"error": "domain_name required"}), 400

        zone_id = get_zone_id_by_name(domain_name)
        if not zone_id:
            return jsonify({"error": "Zone ID not found for the domain"}), 404

        details = get_zone_details(zone_id)
        return jsonify({
            "zone_id": zone_id,
            "zone_name": details.get("name"),
            "status": details.get("status"),
            "created_on": details.get("created_on"),
            "updated_on": details.get("modified_on"),
            "nameservers": details.get("name_servers", [])
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_zone_id_by_name(domain_name):
    url = f"https://api.cloudflare.com/client/v4/zones?name={domain_name}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        zones = response.json()['result']
        if zones:
            return zones[0]['id']  
        else:
            return None
    else:
        return None


def get_zone_details(zone_id):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()['result']
    else:
        return {}


