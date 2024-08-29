## samesystem-auto-time-registration

Automates time registration on SameSystem by clocking in and out so you can focus on working.

This script is designed to be automatically executed by a scheduled cron job or similar automation tool. It will clock you in if you are not already clocked in, or clock you out if you are.

Simply update the `main.py` file with your SameSystem login details, and customize the clock-in and clock-out time ranges to your liking. The script will select a random time within the start and end time ranges to clock in or out, in order to simulate natural human behavior.