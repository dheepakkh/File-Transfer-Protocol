import socket
import threading
import os
import struct
import ssl

# Server settings
SERVER_HOST = "192.168.163.245"
SERVER_PORT = 1456
BUFFER_SIZE = 1024

# Commands
CMD_UPLOAD = "UPLD"
CMD_DOWNLOAD = "DWLD"
CMD_LIST = "LIST"
CMD_DELETE = "DELF"
CMD_QUIT = "QUIT"

ssl_context=ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain(certfile="server-cert.pem",keyfile="server-key.pem")


def handle_client_connection(client_socket, addr):
    print(f"[+] New connection from {addr}")
    try:
        while True:
            # Receive the command from the client
            command = client_socket.recv(BUFFER_SIZE).decode().strip()
            if not command:
                break  # if connection is closed
            print(f"Received command from {addr}: {command}")

            if command == CMD_UPLOAD:
                handle_upload(client_socket)
            elif command == CMD_DOWNLOAD:
                handle_download(client_socket)
            elif command == CMD_LIST:
                handle_list(client_socket)
            elif command == CMD_DELETE:
                handle_delete(client_socket)
            elif command == CMD_QUIT:
                print(f"[-] Connection closed by {addr}")
                break
    finally:
        client_socket.close()

SERVER_FILES_DIR = 'server_files'
if not os.path.exists(SERVER_FILES_DIR):
    os.makedirs(SERVER_FILES_DIR)

# Modify the handle_upload function
# Inside handle_upload function
def handle_upload(client_socket):
    try:
        file_name_length = struct.unpack("h", client_socket.recv(2))[0]
        file_name = client_socket.recv(file_name_length).decode()
        file_path = os.path.join(SERVER_FILES_DIR, file_name)  # Use the base path
        
        # Check if the file already exists on the server
        if os.path.exists(file_path):
            client_socket.send(b"EXIST")  # Send message to client indicating file exists
            response = client_socket.recv(BUFFER_SIZE).decode().strip().upper()  # Receive response from client
            if response != "Y":
                print(f"Client chose not to overwrite file '{file_name}'. Upload canceled.")
                return
        
        # Continue with file upload process
        file_size_data = client_socket.recv(4)
        if len(file_size_data) < 4:
            print("Error: Incomplete file size data received.")
            return
        
        file_size = struct.unpack("i", file_size_data)[0]
        with open(file_path, "wb") as file:
            bytes_received = 0
            while bytes_received < file_size:
                data = client_socket.recv(min(BUFFER_SIZE, file_size - bytes_received))
                if not data:
                    break  # connection closed
                file.write(data)
                bytes_received += len(data)
        print(f"Uploaded file: {file_name}")
    except struct.error as e:
        print("Error unpacking data:", e)
    except IOError as e:
        print("Error writing file:", e)


# Modify the handle_download function
def handle_download(client_socket):
    file_name_length = struct.unpack("h", client_socket.recv(2))[0]
    file_name = client_socket.recv(file_name_length).decode()
    file_path = os.path.join(SERVER_FILES_DIR, file_name)  # Use the base path
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        client_socket.send(struct.pack("i", file_size))
        with open(file_path, "rb") as file:
            while True:
                bytes_read = file.read(BUFFER_SIZE)
                if not bytes_read:
                    break
                client_socket.send(bytes_read)
    else:
        client_socket.send(struct.pack("i", -1))

# Modify handle_list function if needed to list files from SERVER_FILES_DIR
def handle_list(client_socket):
    files = os.listdir(SERVER_FILES_DIR)
    client_socket.send(struct.pack("i", len(files)))
    for f in files:
        file_name_encoded = f.encode()
        client_socket.send(struct.pack("i", len(file_name_encoded)) + file_name_encoded)

# Modify handle_delete function to remove files from SERVER_FILES_DIR
def handle_delete(client_socket):
    try:
        # Prompt the client for authentication password
        client_socket.send(b"AUTH")
        password = client_socket.recv(BUFFER_SIZE).decode()

        # Compare the received password with the expected password
        expected_password = "your_password_here"  # Change this to your desired password
        if password != expected_password:
            client_socket.send(b"0")  # Authentication failed
            return
        
        # Authentication successful, continue with file deletion
        file_name_length = struct.unpack("h", client_socket.recv(2))[0]
        file_name = client_socket.recv(file_name_length).decode()
        file_path = os.path.join(SERVER_FILES_DIR, file_name)  # Use the base path
        if os.path.exists(file_path):
            os.remove(file_path)
            client_socket.send(b"1")  # Deletion successful
        else:
            client_socket.send(b"0")  # File not found on server
    except Exception as e:
        print("Error deleting file:", e)

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(5)
    print(f"[*] Listening as {SERVER_HOST}:{SERVER_PORT} ...")

    while True:
        client_socket, addr = server_socket.accept()
        conn_ssl=ssl_context.wrap_socket(client_socket, server_side=True)
        client_handler = threading.Thread(
            target=handle_client_connection,
            args=(conn_ssl, addr)
        )
        client_handler.start()

if __name__ == "__main__":
    start_server()