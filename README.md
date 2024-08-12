## samesystem-auto-time-registration

Automates time registration on SameSystem by clocking in and out.

This script is designed to be executed by a scheduled cron job or similar automation tool. It will automatically clock in if you are not currently on shift, or clock out if you are already clocked in.

The `TIME_WINDOW_MINUTES` variable controls how much variability there is in the timing of clocking in or out. For example, with `TIME_WINDOW_MINUTES` set to 20, if the script is run at 7:50, it will choose a random time between 7:50 and 8:10 to clock in or out in order to simulate natural human behavior.