import json
import random

# courier id is random (each courier should have unique ID. in real life couriers should enter their ID)
courier_id_max_val = (2 ** 32) - 1
courier_id = random.randint(0, courier_id_max_val)

# value for each day of the week is a list of timeslot lists, each timeslot list contains starting time, end time and list of supported addresses
available_timeslots_dict = \
    {"courier_id": courier_id, "timeslots":
        {"17/07/2021": [["08:00", "10:00", ["Tel Aviv-Yafo", "Ramat Gan"]],
                        ["10:00", "12:00", ["Tel Aviv-Yafo", "Ramat Gan", "Bnei Brak"]],
                        ["12:00", "14:00", ["Ramat Gan", "Bnei Brak", "Petah Tikva"]], ["14:00", "16:00", ["Bnei Brak", "Petah Tikva", "Rosh Haayin"]],
                        ["16:00", "18:00", ["Bnei Brak", "Petah Tikva", "Tel Aviv-Yafo"]]],
        "18/07/2021":  [["08:00", "10:00", ["Tel Aviv-Yafo", "Ramat Gan"]], ["10:00", "12:00", ["Tel Aviv-Yafo", "Ramat Gan", "Bnei Brak"]],
                        ["12:00", "14:00", ["Ramat Gan", "Bnei Brak", "Petah Tikva"]], ["14:00", "16:00", ["Bnei Brak", "Petah Tikva", "Rosh Haayin"]]],
        "19/07/2021":  [["10:00", "12:00", ["Tel Aviv-Yafo", "Ramat Gan"]],
                        ["12:00", "14:00", ["Tel Aviv-Yafo", "Ramat Gan"]], ["14:00", "16:00", ["Bnei Brak", "Tel Aviv-Yafo", "Ramat Gan"]],
                        ["16:00", "18:00", ["Bnei Brak", "Petah Tikva", "Tel Aviv-Yafo"]]],
        "20/07/2021":  [["10:00", "12:00", ["Tel Aviv-Yafo", "Ramat Gan"]],
                        ["12:00", "14:00", ["Tel Aviv-Yafo", "Ramat Gan"]], ["14:00", "16:00", ["Bnei Brak", "Tel Aviv-Yafo", "Ramat Gan"]],
                        ["16:00", "18:00", ["Bnei Brak", "Petah Tikva", "Tel Aviv-Yafo"]]],
        "21/07/2021":  [["08:00", "10:00", ["Tel Aviv-Yafo", "Ramat Gan"]], ["10:00", "12:00", ["Tel Aviv-Yafo", "Ramat Gan"]],
                        ["12:00", "14:00", ["Tel Aviv-Yafo", "Ramat Gan"]], ["14:00", "16:00", ["Bnei Brak", "Tel Aviv-Yafo", "Ramat Gan"]],
                        ["16:00", "18:00", ["Bnei Brak", "Petah Tikva", "Tel Aviv-Yafo"]]],
        "22/07/2021":  [["08:00", "10:00", ["Tel Aviv-Yafo", "Ramat Gan"]], ["10:00", "12:00", ["Tel Aviv-Yafo", "Ramat Gan"]],
                        ["12:00", "14:00", ["Tel Aviv-Yafo", "Ramat Gan"]]]
        }
    }

with open('courier_timeslots.json', 'w') as f:
    json.dump(available_timeslots_dict, f, indent=2)