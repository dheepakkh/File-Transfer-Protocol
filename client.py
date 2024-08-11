import tkinter as tk
from tkinter import filedialog, messagebox,simpledialog
from functools import partial
import socket
import struct
import os
import ssl
import threading

SERVER_HOST = "192.168.163.245"
SERVER_PORT = 1456
BUFFER_SIZE = 1024
CLIENT_FILES_DIR = 'client_files'

ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
ssl_context.load_verify_locations("server-cert.pem")
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def connect_to_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SERVER_HOST, SERVER_PORT))
    conn = ssl_context.wrap_socket(s, server_hostname="deepak")
    print(f"Connected to {SERVER_HOST}:{SERVER_PORT}")
    return conn

def upload_file(file_name, s, output_label):
    print("Upload button clicked")  # Debug print
    if not os.path.exists(file_name):
        output_label.config(text="File does not exist")
        return

    try:
        print("Sending upload command")  # Debug print
        # Send the command to upload a file
        s.send(b"UPLD")

        print("Sending file name")  # Debug print
        # Send the file name to the server
        file_name_encoded = file_name.encode()
        s.send(struct.pack("h", len(file_name_encoded)) + file_name_encoded)

        # Check if the server responds with "EXIST" to indicate that the file already exists
        print("Waiting for response")  # Debug print
        response = s.recv(BUFFER_SIZE).decode().strip().upper()
        print("Response received:", response)  # Debug print
        if response == "EXIST":
            # Prompt the user to confirm whether they want to overwrite the existing file
            overwrite_response = messagebox.askyesno("File Exists", f"File '{file_name}' already exists on the server. Do you want to overwrite it?")
            if not overwrite_response:
                output_label.config(text="Upload canceled.")
                return
            else:
                s.send(overwrite_response.encode())  # Send the response to the server

        # Get the file size and send it to the server
        print("Sending file size")  # Debug print
        file_size = os.path.getsize(file_name)
        s.send(struct.pack("i", file_size))

        # Send the file data to the server
        print("Sending file data")  # Debug print
        with open(file_name, "rb") as file:
            while True:
                bytes_read = file.read(BUFFER_SIZE)
                if not bytes_read:
                    break
                s.send(bytes_read)

        output_label.config(text=f"File {file_name} uploaded successfully")
    except Exception as e:
        output_label.config(text=f"Error uploading file: {e}")



def download_file(file_name, s, output_label):
    s.send(b"DWLD")
    file_name_encoded = file_name.encode()
    s.send(struct.pack("h", len(file_name_encoded)) + file_name_encoded)
    file_size = struct.unpack("i", s.recv(4))[0]
    if file_size == -1:
        output_label.config(text="File not found on server")
        return
    
    # Ensure the client_files directory exists
    if not os.path.exists(CLIENT_FILES_DIR):
        os.makedirs(CLIENT_FILES_DIR)

    file_path = os.path.join(CLIENT_FILES_DIR, file_name)  # Use the base path for downloads
    with open(file_path, "wb") as file:
        bytes_received = 0
        while bytes_received < file_size:
            bytes_read = s.recv(BUFFER_SIZE)
            if not bytes_read:
                break  # Connection closed
            file.write(bytes_read)
            bytes_received += len(bytes_read)
    output_label.config(text=f"File {file_name} downloaded successfully")

def list_files(s, output_label):
    s.send(b"LIST")
    count = struct.unpack("i", s.recv(4))[0]
    files = []
    output_label.config(text="Files on server:")
    for _ in range(count):
        file_name_length = struct.unpack("i", s.recv(4))[0]
        file_name = s.recv(file_name_length).decode()
        files.append(file_name)
        output_label.config(text=output_label.cget("text") + f"\n- {file_name}")
    return files

def delete_file(file_name, s, output_label):
    try:
        # Prompt the user for authentication password
        password = simpledialog.askstring("Authentication", "Enter authentication password:", show='*')
        if not password:
            output_label.config(text="Password not provided. Deletion canceled.")
            return

        # Send the password to the server
        s.send(b"AUTH")
        s.send(password.encode())

        # Receive authentication result from the server
        auth_result = s.recv(1)
        if auth_result != b"1":
            output_label.config(text="Authentication failed. Deletion canceled.")
            return

        # Proceed with file deletion
        s.send(b"DELF")
        file_name_encoded = file_name.encode()
        s.send(struct.pack("h", len(file_name_encoded)) + file_name_encoded)
        result = s.recv(1)
        if result == b"1":
            output_label.config(text=f"File {file_name} deleted successfully")
        else:
            output_label.config(text="File not found on server")
    except Exception as e:
        output_label.config(text=f"Error deleting file: {e}")

def create_gui():
    conn = connect_to_server()

    

    root = tk.Tk()
    root.title("File Transfer Client")

    output_label = tk.Label(root, text="", wraplength=400)
    output_label.grid(row=0, column=0, columnspan=3)

    # Upload
    upload_label = tk.Label(root, text="Upload File:")
    upload_label.grid(row=1, column=0)
    upload_entry = tk.Entry(root)
    upload_entry.grid(row=1, column=1)
    upload_button = tk.Button(root, text="Upload", command=lambda: upload_file(upload_entry.get(), conn, output_label))
    upload_button.grid(row=1, column=2)
    # Download
    download_label = tk.Label(root, text="Download File:")
    download_label.grid(row=2, column=0)
    download_entry = tk.Entry(root)
    download_entry.grid(row=2, column=1)
    download_button = tk.Button(root, text="Download", command=lambda: download_file(download_entry.get(), conn, output_label))
    download_button.grid(row=2, column=2)

    # List
    list_button = tk.Button(root, text="List Files", command=partial(list_files, conn, output_label))
    list_button.grid(row=3, column=1)

    # Delete
    def delete_wrapper():
        delete_file(delete_entry.get(), conn, output_label)
    delete_label = tk.Label(root, text="Delete File:")
    delete_label.grid(row=4, column=0)
    delete_entry = tk.Entry(root)
    delete_entry.grid(row=4, column=1)
    delete_button = tk.Button(root, text="Delete", command=delete_wrapper)
    delete_button.grid(row=4, column=2)


    root.mainloop()

if __name__ == "__main__":
    create_gui()
