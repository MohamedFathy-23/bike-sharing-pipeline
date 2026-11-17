# Data dictionary: hour.csv

Source: https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset (17,379 rows, 17 columns, 2011-2012)

| Column | CSV type | Description |
|---|---|---|
| instant | integer | Record index |
| dteday | text (YYYY-MM-DD) | Date |
| season | integer | 1 Spring, 2 Summer, 3 Fall, 4 Winter |
| yr | integer | 0 = 2011, 1 = 2012 |
| mnth | integer | Month, 1 to 12 |
| hr | integer | Hour, 0 to 23 |
| holiday | integer | 1 if holiday |
| weekday | integer | Day of week, 0 to 6 |
| workingday | integer | 1 if neither weekend nor holiday |
| weathersit | integer | 1 Clear, 2 Mist, 3 Light rain/snow, 4 Heavy rain/snow |
| temp | float | Normalized temperature (x 41 = degrees C) |
| atemp | float | Normalized feeling temperature (x 50 = degrees C) |
| hum | float | Normalized humidity (x 100 = percent) |
| windspeed | float | Normalized wind speed (x 67) |
| casual | integer | Rentals by casual users |
| registered | integer | Rentals by registered users |
| cnt | integer | Total rentals |
