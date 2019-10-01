import getpass
import locale
import os
import re
import smtplib
import sys

import cairosvg
import click
import jinja2
import requests

from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header


EMAIL_SUBJECT = 'Attestation formation Calcul Québec'
EMAIL_BODY = """Bonjour {first_name} {last_name},

Ci-joint votre certification pour la formation {workshop} {date}.

Cordialement,
Calcul Québec
"""
api_url = "https://www.eventbriteapi.com/v3/"

def get_event(event_id, api_key):
    response = requests.get(
        "{}/events/{}/".format(api_url, event_id),
        headers = {
            "Authorization": "Bearer {}".format(api_key),
        },
        verify = True,
    )
    return response.json()

def get_venue(venue_id, api_key):
    response = requests.get(
        "{}/venues/{}/".format(api_url, venue_id),
        headers = {
            "Authorization": "Bearer {}".format(api_key),
        },
        verify = True,
    )
    return response.json()

def get_guests(event_id, api_key):
    response = requests.get(
        "{}/events/{}/attendees/".format(api_url, event_id),
        headers = {
            "Authorization": "Bearer {}".format(api_key),
        },
        verify = True,
    )
    guests = response.json()['attendees']
    while response.json()['pagination']['has_more_items']:
        continuation = response.json()['pagination']['continuation']
        response = requests.get(
            "{}/events/{}/attendees/?continuation={}".format(api_url, event_id, continuation),
            headers = { "Authorization": "Bearer {}".format(api_key), },
            verify = True,
        )
        guests.extend(response.json()['attendees'])
    return guests

def build_checkedin_list(event, venue, guests, duration, date):
    title = re.sub("(\[.*\])", "", event['name']['text']).strip()
    where = venue['name']
    time_start = datetime.strptime(event['start']['local'], '%Y-%m-%dT%H:%M:%S')
    time_end = datetime.strptime(event['end']['local'], '%Y-%m-%dT%H:%M:%S')
    date = "du " + time_start.strftime('%d %B %Y') if not date else date
    duration = (time_end - time_start).total_seconds() / 3600 if not duration else duration
    attended_guests = []
    # set locale in french for month name
    locale.setlocale(locale.LC_ALL, 'fr_FR')
    for guest in guests:
        if guest['checked_in']:
            first_name = guest['profile']['first_name']
            last_name = guest['profile']['last_name']
            email = guest['profile']['email']
            order_id = guest['order_id']
            context = {'workshop' : title, 
                       'first_name' : first_name.upper(), 
                       'last_name'  : last_name.upper(),
                       'email' : email,
                       'where' : where,
                       'date' : date,
                       'duration' : duration,
                       'order_id' : order_id,
                       'filename' : './certificates/Attestation_CQ_{}_{}_{}.pdf'.format(first_name.replace(" ", "_").upper(), 
                                                                                        last_name.replace(" ", "_").upper(),
                                                                                        order_id)
            }
            attended_guests.append(context)
    return attended_guests

def write_certificates(guests):
    try:
        os.mkdir('./certificates')
    except OSError:
        pass
    # certificate jinja2 template
    tpl = jinja2.Environment(loader=jinja2.FileSystemLoader('./')).get_template('template.svg')
    for guest in guests:
        cairosvg.svg2pdf(bytestring=tpl.render(guest).encode('utf-8'), 
                         write_to=guest['filename'])

def create_email(from_, guest, send_self):
    # Create email
    outer = MIMEMultipart()
    outer['From'] = from_
    if send_self:
        outer['To'] = from_
    else:
        outer['To'] = guest['email']
    outer['Reply-to'] = 'no-reply@calculquebec.ca'
    outer['Subject'] = Header(EMAIL_SUBJECT, 'utf-8')

    # Attach body
    body = MIMEText(EMAIL_BODY.format(**guest), 'plain', 'utf-8')
    outer.attach(body)

    # Attach PDF Certificate
    msg = MIMEBase('application', "octet-stream")
    with open(guest['filename'], 'rb') as file_:
        msg.set_payload(file_.read())
    encoders.encode_base64(msg)
    msg.add_header('Content-Disposition', 'attachment', filename=os.path.basename(guest['filename']))
    outer.attach(msg)
    return outer

def send_email(attended_guests, send_self):
    gmail_user = input('gmail username: ')
    gmail_password = getpass.getpass('gmail password: ')

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(gmail_user, gmail_password)

        for guest in attended_guests:
            email = create_email(gmail_user, guest, send_self)
            # Send email
            if send_self:
                print('sending email to YOU about: {first_name} ({email})...'.format(**guest))
            else:
                print('sending email to: {first_name} {last_name} ({email})...'.format(**guest))
            try:
                server.sendmail(email['From'], email['To'], email.as_string())
            except smtplib.SMTPAuthenticationError as e:
                # If the GMail account is now allowing secure apps, the script will fail.
                # read : http://stackabuse.com/how-to-send-emails-with-gmail-using-python/
                print('Go to https://myaccount.google.com/lesssecureapps and Allow less secure apps.')
                sys.exit(1)

@click.command()
@click.option('--event_id', prompt='Event ID', help='Event ID')
@click.option('--api_key', prompt='API Key', help='EventBrite API Key')
@click.option('--duration', default=0, type=float, help='Override workshop duration in hours')
@click.option('--email/--no-email', default=False, help="Send the certificate to each attendee")
@click.option('--send_self/--no-send_self', default=False, help="Send to self")
@click.option('--archive/--no-archive', default=False, help="Create a zip file with the certificates")
@click.option('--date', default=None, type=str, help="Specifies the date manually")
def main(event_id, api_key, duration, email, send_self, archive, date):
    event = get_event(event_id, api_key)
    venue = get_venue(event['venue_id'], api_key)
    guests = get_guests(event_id, api_key)
    attended_guests = build_checkedin_list(event, venue, guests, duration, date)
    write_certificates(attended_guests)
    if send_self or email:
        send_email(attended_guests, send_self)

if __name__ == "__main__":
    main()