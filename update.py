#!/usr/bin/python
import datetime
import json
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from bs4 import BeautifulSoup
import requests
import bs4

SCOPES = ['https://www.googleapis.com/auth/calendar']

# Class copied from https://github.com/HotDamnCoder/StuudiumScraper/blob/master/stuudium.py
# Added self.desc
class HomeWork:
    def __init__(self, text, check, is_test, duedate, due, desc):
        self.text = text
        self.checked = check
        self.test = is_test
        self.dateInTicks = duedate
        self.date = due
        self.desc = desc

def get_homework(source):
    # Code copied from https://github.com/HotDamnCoder/StuudiumScraper/blob/master/stuudium.py
    # Gets tasks from Stuudium
    # Edited a little bit
    source = BeautifulSoup(source.text, features="html.parser").findAll('div', {'class': 'todo_container'})
    tasks = []
    for div in source:
        desc = None
        date_in_tick = int(div.attrs['data-date_ts'])
        date = div.attrs['data-date']
        subject = div.find('a', {"class": "subject_name"})
        checked = 'is_marked' in div.attrs['class']
        if subject is not None:
            subject = subject.text + " "
        else:
            subject = ""
        test = not div.find('span', {"class": "test_indicator"}) is None
        task = div.find('span', {"class": "todo_content"})
        if task is not None:
            task = "".join([str(a) if type(a) is bs4.element.NavigableString else a.attrs[
                'href'] if 'href' in a.attrs.keys() else "" for a in task.contents])
            if test:
                desc = subject + "Kontrolltöö " + task
                task = subject + "Kontrolltöö"
            else:
                desc = subject + task
        else:
            if test:
                task = subject + "Kontrolltöö"
            else:
                task = subject.strip()
        task = task.strip()
        homework = HomeWork(task, checked, test, date_in_tick, date, desc)
        tasks.append(homework)
    return tasks

def add_test(service, task):
    # Time right now for searching events later
    now = str(datetime.datetime.now()).split(" ")
    now = now[0] + "T" + now[1].split(".")[0] + "+02:00"
    # Date of the task
    date = task.date
    y = date[:-4]       # Year
    d = date[-2:]       # Day
    m = date[-4:-2]     # Month
    # Format date
    new_date = datetime.date(year=int(y), month=int(m), day=int(d))

    # Event dict for Google API
    event = {
        'summary': str(task.text),
        'description': str(task.desc) if task.desc is not None else "",
        'start': {
            "date": str(new_date)
        },
        'reminders': {
            'useDefault': True,
            'overrides': [
            ]
        },
        'source': {
            'url': "https://nrg.ope.ee/",
            'title': "NRG Stuudium"
        },
        'end': {
            'date': str(new_date)
        },
        'colorId': "11"
    }
    # Max search time (2 days later)    Format: yyyy-mm-dd T hh:mm:ss+timezone
    time_max = str(new_date+datetime.timedelta(days=2)) + "T23:00:00+02:00"

    # Getting events from Google Calendar
    response_events = service.events().list(calendarId='primary', timeMin=now,
                                            timeMax=time_max).execute()

    adding = True   # Boolean to check if event exists  (if not, True)
    if len(response_events["items"]) != 0:
        for item in response_events["items"]:
            # If event exists, adding = False
            if item["summary"] == task.text:
                adding = False

    if adding:
        # Inserting event to Calendar
        service.events().insert(calendarId="primary", body=event).execute()
        print("task added!")


def get_service():
    # Code copied from Google Calendar API
    creds = None

    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service

def main():

    login_url = "https://nrg.ope.ee/auth/"
    data = {}
    with open("data.json") as file:
        info = json.load(file)
        data["data[User][password]"] = info["data[User][password]"]
        data["data[User][username]"] = info["data[User][username]"]


    with open("data.json", "w") as out:
        json.dump(data, out)

    # Start Google Service
    service = get_service()
    colors = service.colors().get().execute()["event"]

    # Get tasks from Stuudium
    session = requests.session()
    main_page = session.post(login_url, data)
    session.close()
    tasks = get_homework(main_page)

    # Add tests to Calendar
    for task in tasks:
        if task.test and not task.checked:
            add_test(service, task)


if __name__ == '__main__':
    main()
