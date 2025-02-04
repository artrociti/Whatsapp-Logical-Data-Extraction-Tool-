import json
import pandas as pd
from colorama import Fore, Style
PADDING=80
with open(r"whatsapp_data.json", "r") as f:
    data=json.load(f)
#print(data.keys()) #REMOVE
messages=pd.DataFrame(data["Messages"])
subjects = list(set(messages["Chat Name"]))
#print(subjects)  #REMOVE
messages=messages.sort_values("Message ID",ignore_index=True)
#messages = messages.drop(messages[messages['Timestamp'] == 'None'].index)
print(Style.BRIGHT+Fore.YELLOW+"Parsing chats from json..."+Style.RESET_ALL)
for index, rows in messages.iterrows():
    if str(messages["Message"]) != "[Deleted Message]":
        if rows["Sender Identity"]=="Me":
            print(str("Chat ID: "+rows["Chat Name"]).rjust(PADDING))
            print(str("Sender: "+rows["Sender Identity"]).rjust(PADDING))
            print(str(Style.BRIGHT+Fore.GREEN+rows["Message"]+" <<< Message"+Style.RESET_ALL).rjust(PADDING))
            print(str("Timestamp: " + str(rows["Timestamp"])).rjust(PADDING))
            print("\n\n")
        else:
            if rows["Sender Identity"] == "null":
                print(Style.BRIGHT+Fore.RED+"<Undefined Sender Identity>"+Style.RESET_ALL)
            else:
                print("Chat ID: " + str(rows["Chat Name"]))
                print("Sender: "+str(rows["Sender Identity"]))
                print(str(Fore.CYAN+"Message "+Style.BRIGHT+">>> "+rows["Message"]+Style.RESET_ALL))
                print(str("Timestamp: " + str(rows["Timestamp"])))
                print("\n\n")
        

