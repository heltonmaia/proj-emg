# PC code - serial_acquisition.py
import serial
import time
import numpy as np
from threading import Thread
from queue import Queue

SERIAL_PORT = '/dev/ttyACM0'
BAUDRATE = 115200  # Aumentado para 115200
BUFFER_SIZE = 1024
CHUNK_SIZE = 128

def read_serial_data(serial_conn, data_queue):
    """Função para leitura serial em thread separada"""
    buffer = bytearray()
    
    while True:
        if serial_conn.in_waiting:
            # Lê dados disponíveis
            data = serial_conn.read(CHUNK_SIZE)
            buffer.extend(data)
            
            # Processa buffer em chunks completos
            while b'\n' in buffer:
                idx = buffer.find(b'\n')
                line = buffer[:idx+1]
                buffer = buffer[idx+1:]
                data_queue.put(line)

def process_data(data_queue, filename):
    """Processa e salva dados em arquivo"""
    with open(filename, 'wb') as f:
        while True:
            # Coleta vários dados antes de escrever
            data_chunk = []
            for _ in range(BUFFER_SIZE):
                if not data_queue.empty():
                    data_chunk.append(data_queue.get())
                else:
                    break
                    
            if data_chunk:
                f.write(b''.join(data_chunk))
                f.flush()
            
            time.sleep(0.001)  # Pequeno delay para não sobrecarregar CPU

def main():
    # Configura conexão serial
    try:
        serial_conn = serial.Serial(SERIAL_PORT, BAUDRATE)
        time.sleep(2)  # Aguarda estabilização
    except Exception as e:
        print(f"Erro ao abrir porta serial: {e}")
        return

    # Configura filas e threads
    data_queue = Queue(maxsize=BUFFER_SIZE * 2)
    
    # Inicia threads
    reader_thread = Thread(target=read_serial_data, args=(serial_conn, data_queue))
    processor_thread = Thread(target=process_data, args=(data_queue, 'dados_alta_freq.txt'))
    
    reader_thread.daemon = True
    processor_thread.daemon = True
    
    reader_thread.start()
    processor_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Encerrando aquisição...")
        serial_conn.close()

if __name__ == "__main__":
    main()
