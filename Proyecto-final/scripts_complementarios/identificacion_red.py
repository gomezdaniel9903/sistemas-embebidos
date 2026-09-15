import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("", 9999))
print("Esperando datos del robot...")
datos, addr = s.recvfrom(1024)
print("Robot en:", addr[0])          # <-- de paso, aqui tienes su IP
print(datos.decode())