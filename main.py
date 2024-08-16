import json
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta
import requests


# SameSystem login details
EMAIL    = "your@email.com"
PASSWORD = "YourPassword123"

# The script will sleep for a random duration between 0 and TIME_WINDOW_MINUTES before proceeding to clock in or out
TIME_WINDOW_MINUTES = 20

# Writes request responses to files for debugging purposes
DEBUG_MODE = False


def login():
    # URL to send the login request
    url = "https://in.samesystem.com/sessions"

    # Payload containing the login credentials
    payload = {
        "user_session[email]": EMAIL,
        "user_session[password]": PASSWORD
    }

    # Create a session object to persist cookies across requests
    session = requests.Session()

    # Send POST request to the login endpoint
    response = session.post(url, data=payload)
    
    return session, response


def get_shift_id(session, ctxpre):
    # Endpoint for fetching shift data
    url = f"https://in.samesystem.com/{ctxpre}/graphql/web?query:TimeRegistrations"

    payload = {
        "operationName": "TimeRegistrations",
        "variables": {
            "jsPart": "{\"unversioned\":\"\",\"versioned\":\"\"}"
        },
        "query": "query TimeRegistrations($jsPart: String) {\n  timeRegistrations(jsPart: $jsPart) {\n    basicData: basic_data {\n      general {\n        shift\n        unplannedShift\n        targetShopOptions {\n          id\n          name\n          __typename\n        }\n        __typename\n      }\n      registrations {\n        isManual\n        isCurrent\n        canCheckIn: can_check_in\n        date\n        plannedBreaks: planned_breaks {\n          duration {\n            minutes\n            __typename\n          }\n          endedAt: ended_at {\n            float\n            plain\n            __typename\n          }\n          isPaid: paid\n          startedAt: started_at {\n            float\n            plain\n            __typename\n          }\n          __typename\n        }\n        plannedEndTime: planned_end_time {\n          float\n          plain\n          __typename\n        }\n        plannedStartTime: planned_start_time {\n          float\n          plain\n          __typename\n        }\n        shiftId: shift_id\n        shop {\n          id\n          name\n          __typename\n        }\n        __typename\n      }\n      steppedCurrentTime: stepped_current_time {\n        plain\n        float\n        __typename\n      }\n      __typename\n    }\n    currentStatus: current_status {\n      breakReason: break_reason\n      breakReasonRequired: break_reason_required\n      breaks {\n        duration {\n          minutes\n          __typename\n        }\n        endedAt: ended_at {\n          float\n          plain\n          __typename\n        }\n        paid\n        startedAt: started_at {\n          float\n          plain\n          __typename\n        }\n        __typename\n      }\n      unadjustedBreaks: unadjusted_breaks {\n        endedAt: ended_at {\n          float\n          __typename\n        }\n        startedAt: started_at {\n          float\n          __typename\n        }\n        __typename\n      }\n      breaksReason: breaks_reason\n      endReasonRequired: end_reason_required\n      endTimeReason: end_time_reason\n      registeredEndTime: registered_end_time {\n        float\n        plain\n        __typename\n      }\n      registeredStartTime: registered_start_time {\n        float\n        plain\n        __typename\n      }\n      shiftId: shift_id\n      shop {\n        id\n        name\n        __typename\n      }\n      startReasonRequired: start_reason_required\n      startTimeReason: start_time_reason\n      swipedInReason: swiped_in_reason\n      swipedInRounded: swiped_in_rounded {\n        plain\n        __typename\n      }\n      swipedOutReason: swiped_out_reason\n      swipedOutRounded: swiped_out_rounded {\n        plain\n        __typename\n      }\n      __typename\n    }\n    fingerprintData: fingerprint_data {\n      complexity\n      passedFingerprint: passed_fingerprint\n      reason\n      __typename\n    }\n    settings {\n      breakInterval: break_interval\n      breaksPlacement: breaks_placement\n      includeBreaks: include_breaks\n      workingTimeInterval: working_time_interval\n      breakRegistrationMode: break_registration_type\n      allowedMinutesBeforeBreak: allowed_minutes_before_break\n      allowedMinutesAfterBreak: allowed_minutes_after_break\n      __typename\n    }\n    __typename\n  }\n}"
    }

    # Send the POST request to get all shifts
    print("Sending request to get all shifts...")
    response = session.post(url, json=payload)
    data = response.json()

    if DEBUG_MODE:
        with open("get_shift_id_response.json", "w") as file:
            json.dump(data, file, indent=4)

    # Extract the list of shifts
    shifts = data["data"]["timeRegistrations"]["currentStatus"]

    # Initialize variables
    shift_id = None
    is_planned = False
    should_clock_out = False

    # Extract the ID of the active shift
    for shift in shifts:
        # Check if the shift has a start time but no end time (i.e., not clocked out yet)
        if shift["registeredStartTime"] and not shift["registeredEndTime"]:
            shift_id = shift["shiftId"]
            print(f"Found ID of active shift to clock out of: {shift_id}")
            should_clock_out = True
            break
    
    # If no active shift was found, extract the ID of the planned shift if one exists
    if not shift_id:
        try:
            shift_id = data["data"]["timeRegistrations"]["basicData"]["registrations"][0]["shiftId"]
            print(f"Found ID of planned shift to clock in to: {shift_id}")
            is_planned = True
        except (KeyError, IndexError) as e:
            # No planned shift was found
            print("No planned shift found, will clock in manually as an unplanned shift.")

    return shift_id, is_planned, should_clock_out


def clock_in(session, ctxpre, shift_id, shop_id, current_time_decimal, is_planned):
    # Endpoint to register time
    url = f"https://in.samesystem.com/{ctxpre}/graphql/web?mutation:RegisterTimes"

    # Payload for clocking in
    payload = {
        "operationName": "RegisterTimes",
        "variables": {
            "punchIn": {
                "reason": "",
                "time": {
                    "format": "float",
                    "value": current_time_decimal
                }
            },
            "shopId": shop_id
        },
        "query": "mutation RegisterTimes($breaks: [BreakInputType], $breakReason: String, $punchIn: TimeRegistrationActionInput, $punchOut: TimeRegistrationActionInput, $shiftId: ID, $shopId: ID) {\n  registerTimes(\n    breaks: $breaks\n    punchIn: $punchIn\n    punchOut: $punchOut\n    shiftId: $shiftId\n    shopId: $shopId\n    breakReason: $breakReason\n  ) {\n    currentStatus: current_state {\n      breakReason: break_reason\n      breakReasonRequired: break_reason_required\n      breaks {\n        duration {\n          minutes\n          __typename\n        }\n        endedAt: ended_at {\n          plain\n          float\n          __typename\n        }\n        paid\n        startedAt: started_at {\n          plain\n          float\n          __typename\n        }\n        __typename\n      }\n      breaksReason: breaks_reason\n      endReasonRequired: end_reason_required\n      endTimeReason: end_time_reason\n      registeredEndTime: registered_end_time {\n        float\n        plain\n        __typename\n      }\n      registeredStartTime: registered_start_time {\n        float\n        plain\n        __typename\n      }\n      shiftId: shift_id\n      shop {\n        id\n        name\n        __typename\n      }\n      startReasonRequired: start_reason_required\n      startTimeReason: start_time_reason\n      swipedInReason: swiped_in_reason\n      swipedInRounded: swiped_in_rounded {\n        plain\n        __typename\n      }\n      swipedOutReason: swiped_out_reason\n      swipedOutRounded: swiped_out_rounded {\n        plain\n        __typename\n      }\n      __typename\n    }\n    messages\n    status\n    __typename\n  }\n}"
    }

    # Add shift ID only if shift is planned
    if is_planned:
        payload["variables"]["shiftId"] = shift_id

    # Send the POST request to clock in
    print("Sending clock in request...")
    response = session.post(url, json=payload)
    data = response.json()

    if DEBUG_MODE:
        with open("clock_in_response.json", "w") as file:
            json.dump(data, file, indent=4)

    if response.status_code == 200:
        # Check if clock in registration was successful
        if data["data"]["registerTimes"]["status"] == "success":
            print("Clocked in successfully!")
            time.sleep(3)
        else:
            print("An error occurred while clocking in:")
            print(data["data"]["registerTimes"]["messages"][0])
            #print(", ".join(data["data"]["registerTimes"]["messages"]))
    else:
        print(f"A {response.status_code} error occurred while clocking in:")
        print(response)
    
    return


def clock_out(session, ctxpre, shift_id, shop_id, current_time_decimal):
    # Endpoint to register time
    url = f"https://in.samesystem.com/{ctxpre}/graphql/web?mutation:RegisterTimes"

    # Payload for clocking out
    payload = {
        "operationName": "RegisterTimes",
        "variables": {
            "breakReason": "",
            "punchOut": {
                "reason": "",
                "time": {
                    "format": "float",
                    "value": current_time_decimal
                }
            },
            "shiftId": shift_id,
            "shopId": shop_id
        },
        "query": "mutation RegisterTimes($breaks: [BreakInputType], $breakReason: String, $punchIn: TimeRegistrationActionInput, $punchOut: TimeRegistrationActionInput, $shiftId: ID, $shopId: ID) {\n  registerTimes(\n    breaks: $breaks\n    punchIn: $punchIn\n    punchOut: $punchOut\n    shiftId: $shiftId\n    shopId: $shopId\n    breakReason: $breakReason\n  ) {\n    currentStatus: current_state {\n      breakReason: break_reason\n      breakReasonRequired: break_reason_required\n      breaks {\n        duration {\n          minutes\n          __typename\n        }\n        endedAt: ended_at {\n          plain\n          float\n          __typename\n        }\n        paid\n        startedAt: started_at {\n          plain\n          float\n          __typename\n        }\n        __typename\n      }\n      breaksReason: breaks_reason\n      endReasonRequired: end_reason_required\n      endTimeReason: end_time_reason\n      registeredEndTime: registered_end_time {\n        float\n        plain\n        __typename\n      }\n      registeredStartTime: registered_start_time {\n        float\n        plain\n        __typename\n      }\n      shiftId: shift_id\n      shop {\n        id\n        name\n        __typename\n      }\n      startReasonRequired: start_reason_required\n      startTimeReason: start_time_reason\n      swipedInReason: swiped_in_reason\n      swipedInRounded: swiped_in_rounded {\n        plain\n        __typename\n      }\n      swipedOutReason: swiped_out_reason\n      swipedOutRounded: swiped_out_rounded {\n        plain\n        __typename\n      }\n      __typename\n    }\n    messages\n    status\n    __typename\n  }\n}"
    }

    # Send the POST request to clock out
    print("Sending clock out request...")
    response = session.post(url, json=payload)
    data = response.json()

    if DEBUG_MODE:
        with open("clock_out_response.json", "w") as file:
            json.dump(data, file, indent=4)
    
    if response.status_code == 200:
        # Check if clock out registration was successful
        if data["data"]["registerTimes"]["status"] == "success":
            print("Clocked out successfully!")
            time.sleep(3)
        else:
            print(f"An error occurred while clocking out:")
            print(data["data"]["registerTimes"]["messages"][0])
            #print(", ".join(data["data"]["registerTimes"]["messages"]))
    else:
        print(f"A {response.status_code} error occurred while clocking out:")
        print(response)

    return


def get_decimal_time(time_str):
    # Split the time string into hours, minutes, and seconds
    parts = time_str.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = int(parts[2])
    
    # Convert time to decimal hours
    decimal_hours = hours + (minutes / 60) + (seconds / 3600)
    
    return str(decimal_hours)


def main(session, login_response):
    # Regular expressions to find the ctxpre and departmentId values
    ctxpre_match = re.search(r"ctxpre\s*=\s*'(.*?)';", login_response.text)
    shop_id_match = re.search(r'"departmentId"\s*:\s*"(.*?)"', login_response.text)

    # Extract the ctxpre value
    if ctxpre_match:
        ctxpre = ctxpre_match.group(1).lstrip("/")
    else:
        print("Error: 'ctxpre' value not found.")
        sys.exit()
    
    # Extract the departmentId value
    if shop_id_match:
        shop_id = shop_id_match.group(1)
    else:
        print("Error: 'departmentId' value not found.")
        sys.exit()

    if DEBUG_MODE:
        # Fetch dashboard page
        dashboard_url = f"https://in.samesystem.com/{ctxpre}/"
        dashboard_response = session.get(dashboard_url)  # Use "session" to interact with pages that require login
        with open("dashboard_response.html", "w", encoding="utf-8") as file:
            file.write(dashboard_response.text)

    # Get the current time
    current_time_str = datetime.now().strftime("%H:%M:%S")
    current_time_decimal = get_decimal_time(current_time_str)  # Convert the current time to decimals

    # Get the ID of the active shift if there is one
    shift_id, is_planned, should_clock_out = get_shift_id(session, ctxpre)

    if should_clock_out:
        clock_out(session, ctxpre, shift_id, shop_id, current_time_decimal)
    else:
        clock_in(session, ctxpre, shift_id, shop_id, current_time_decimal, is_planned)


if __name__ == "__main__":
    # Get the directory where the script is located
    script_directory = os.path.dirname(os.path.abspath(__file__))

    # Change the working directory to the script's directory
    os.chdir(script_directory)

    # Sleep for a randomized amount of time
    random_minutes = random.randint(0, TIME_WINDOW_MINUTES)
    current_time = datetime.now()
    start_time = (current_time + timedelta(minutes=random_minutes)).strftime("%H:%M:%S")

    print(f"Current time: {current_time.strftime('%H:%M:%S')}")
    print(f"Waiting for {random_minutes} {'minute' if random_minutes == 1 else 'minutes'} until {start_time} before proceeding...")

    time.sleep(random_minutes * 60)

    # Log in
    print("Attempting to log in...")
    session, response = login()

    if DEBUG_MODE:
        with open("login_response.html", "w", encoding="utf-8") as file:
            file.write(response.text)

    # Check if login was successful
    if response.status_code == 200:
        if "charset=UTF-8" in response.text:
            print("Logged in successfully!")
            main(session, response)
        else:
            print("Failed to log in. Check your credentials.")
    else:
        print(f"Failed to log in. Status code: {response.status_code}")
