import sqlite3
import hashlib
import pandas as pd
import json
import os
import matplotlib.pyplot as plt
import subprocess
import sys
from datetime import datetime

def get_db_path():
    """Prompt the user to enter the path to the WhatsApp folder and find msgstore.db."""
    while True:
        folder_path = input("Enter the path to your com.whatsapp folder: ").strip()
        db_path = os.path.join(folder_path, "databases", "msgstore.db")
        if os.path.exists(db_path):
            return db_path
        else:
            print(f"Database file not found at: {db_path}. Please try again.")

def categorize_data(db_path):
    """Fetch and categorize data based on chats, contacts, messages, and deleted messages."""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            chat_query = """
            SELECT j.raw_string AS chat_name, COUNT(m._id) AS message_count
            FROM jid j
            LEFT JOIN chat c ON j._id = c.jid_row_id
            LEFT JOIN message m ON c._id = m.chat_row_id
            GROUP BY j.raw_string
            ORDER BY message_count DESC;
            """
            cursor.execute(chat_query)
            chats = cursor.fetchall()
            
            contact_query = """
            SELECT j.raw_string AS contact, COUNT(m._id) AS message_count
            FROM message m
            LEFT JOIN jid j ON m.sender_jid_row_id = j._id
            GROUP BY j.raw_string
            ORDER BY message_count DESC;
            """
            cursor.execute(contact_query)
            contacts = cursor.fetchall()
            
            message_query = """
            SELECT m._id, j.raw_string, 
                   CASE WHEN m.from_me = 1 THEN 'Me' ELSE sender_j.raw_string END,
                   datetime(m.timestamp / 1000, 'unixepoch', 'localtime'), 
                   CASE WHEN m.text_data IS NULL THEN '[Deleted Message]' ELSE m.text_data END
            FROM message m
            LEFT JOIN jid j ON m.chat_row_id = j._id
            LEFT JOIN jid sender_j ON m.sender_jid_row_id = sender_j._id
            ORDER BY m.timestamp DESC;
            """
            cursor.execute(message_query)
            messages = cursor.fetchall()
            
            deleted_messages_query = """
            SELECT m._id, j.raw_string, 
                   CASE WHEN m.from_me = 1 THEN 'Me' ELSE sender_j.raw_string END,
                   datetime(m.timestamp / 1000, 'unixepoch', 'localtime'), 
                   '[Deleted Message]', mr.revoke_timestamp
            FROM message_revoked mr
            JOIN message m ON mr.message_row_id = m._id
            LEFT JOIN jid j ON m.chat_row_id = j._id
            LEFT JOIN jid sender_j ON m.sender_jid_row_id = sender_j._id
            ORDER BY mr.revoke_timestamp DESC;
            """
            cursor.execute(deleted_messages_query)
            deleted_messages = cursor.fetchall()
            
        return chats, contacts, messages, deleted_messages
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return [], [], [], []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return [], [], [], []

def save_to_files(chats, contacts, messages, deleted_messages):
    """Save categorized data into JSON files and generate visualizations."""
    chat_df = pd.DataFrame(chats, columns=["Chat Name", "Message Count"])
    contact_df = pd.DataFrame(contacts, columns=["Contact", "Message Count"])
    message_df = pd.DataFrame(messages, columns=["Message ID", "Chat Name", "Sender Identity", "Timestamp", "Message"])
    deleted_df = pd.DataFrame(deleted_messages, columns=["Message ID", "Chat Name", "Sender Identity", "Timestamp", "Message", "Revoke Timestamp"])
    
    data = {
        "Chats": chat_df.to_dict(orient='records'),
        "Contacts": contact_df.to_dict(orient='records'),
        "Messages": message_df.to_dict(orient='records'),
        "Deleted Messages": deleted_df.to_dict(orient='records')
    }
    
    with open("whatsapp_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print("Data successfully saved to whatsapp_data.json")
    print("Saved hash of datastore to msgstore.db.sha256")
    visualize_data(chat_df, contact_df, message_df)

def open_image(image_path):
    """Open an image file using the default image viewer."""
    if os.name == 'nt':  # Windows
        os.startfile(image_path)
    elif os.name == 'posix':  # macOS or Linux
        try:
            subprocess.run(['open', image_path]) if sys.platform == 'darwin' else subprocess.run(['xdg-open', image_path])
        except Exception as e:
            print(f"Error opening image: {e}")

def visualize_data(chat_df, contact_df, message_df):
    """Generate and save data visualizations."""
    
    # Plot and save the top 10 chats (message count)
    if not chat_df.empty:
        top_chats = chat_df.head(10)  # Limit to top 10
        top_chats.plot(kind='bar', x='Chat Name', y='Message Count', title='Top 10 Chats')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig("chats.png")
        plt.close()
        open_image("chats.png")  # Open the chart after saving
    
    # Plot and save the top 10 contacts (message count)
    if not contact_df.empty:
        top_contacts = contact_df.head(10)  # Limit to top 10
        top_contacts.plot(kind='bar', x='Contact', y='Message Count', title='Top 10 Contacts')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig("contacts.png")
        plt.close()
        open_image("contacts.png")  # Open the chart after saving
    
    # Plot and save messages over time (daily message count)
    if not message_df.empty:
        message_df['Timestamp'] = pd.to_datetime(message_df['Timestamp'], errors='coerce')
        message_df['Date'] = message_df['Timestamp'].dt.date
        message_counts = message_df.groupby('Date').size()
        message_counts.plot(kind='line', title='Messages Over Time')
        plt.xlabel('Date')
        plt.ylabel('Message Count')
        plt.grid()
        plt.tight_layout()
        plt.savefig("messages_over_time.png")
        plt.close()
        open_image("messages_over_time.png")  # Open the chart after saving

def calculate_metrics(conn):
    """Calculate the required metrics."""
    # Fetch data
    contacts_df = fetch_contacts(conn)
    messages_df = fetch_messages(conn)
    chats_df = fetch_chats(conn)

    # 1. Number of contacts
    num_contacts = len(contacts_df)

    # 2. Number of messages
    num_messages = len(messages_df)

    # 3. Number of chats
    num_chats = len(chats_df)

    # 4. 3 most active chats
    # Group messages by chat_id and count the number of messages per chat
    active_chats = messages_df.groupby("chat_id").size().reset_index(name="message_count")
    active_chats = active_chats.sort_values(by="message_count", ascending=False).head(3)

    # Merge with chats_df to get chat names
    active_chats = pd.merge(active_chats, chats_df, left_on="chat_id", right_on="chat_jid", how="left")
    active_chats = active_chats[["chat_name", "message_count"]]

    return num_contacts, num_messages, num_chats, active_chats

if __name__ == "__main__":
    DB_PATH = get_db_path()
    chats, contacts, messages, deleted_messages = categorize_data(DB_PATH)
    sha256_hash = hashlib.sha256(); [sha256_hash.update(chunk) for chunk in iter(open(DB_PATH, "rb").read, b"")]; hash_out=(sha256_hash.hexdigest())
    with open("msgstore.db.sha256","wt") as f:
        f.write(hash_out)
    if not chats and not contacts and not messages and not deleted_messages:
        print("No data found.")
    else:
        save_to_files(chats, contacts, messages, deleted_messages)
