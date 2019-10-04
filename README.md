# Calcul Québec's Certificate Generator

## Installation
* On Compute Canada clusters only: `module load python/3.6.3`
* `virtualenv venv`
* `source venv/bin/activate`
* `pip install -r requirements.txt`

## Preparation
* On Eventbrite, make sure selected participants are "Checked In" in **Manage** > **Manage Attendees** > **Check-in**
* The script requires a certificate template in SVG format with the following fields:
  - First name: `{{ first_name }}`
  - Last name: `{{ last_name }}`
  - Event title: `{{ workshop }}`
  - "on Month DD, YYYY": `{{ date }}`
  - Duration in hours: `{{ duration }}`
  - Order ID: `{{ order_id }}`
* The script requires an email template in YAML format with the following fields (see `sample_email.yml`):
  - First name: `{first_name}`
  - Last name: `{last_name}`
  - Event title: `{workshop}`
  - "on Month DD, YYYY": `{date}`
* For help and available options:  
  `python gen-certs.py --help`

## Execution examples
Make sure the Python virtual environment is loaded:
* To only generate PDFs:  
  `python gen-certs.py`
* To generate PDFs and send emails to YOU:  
  `python gen-certs.py --send_self`
* To generate PDFs and finally send emails to attendees:  
  `python gen-certs.py --send_atnd`

For convenience, environment variables can be set in advance (through some `source_file.sh`):
* `export CQCG_API_KEY=...`
* `export CQCG_EVENT_ID=...`
* `export CQCG_DATE="on Month DD, YYYY"`
* `export CQCG_DURATION=6.0`
* `export CQCG_SVG_TPLT=training.svg`
* `export CQCG_YML_TPLT=training.yml`
