import cv2
import datetime
import os

# Configuração da captura da webcam
cap = cv2.VideoCapture(0)  # 0 é a webcam padrão
frame_width = int(cap.get(3))
frame_height = int(cap.get(4))
fps = 30  # Frames por segundo

# Variáveis de controle
recording = False
out = None

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Exibe o vídeo em tempo real
    cv2.imshow("Webcam", frame)

    # Se estiver gravando, escreve o frame no arquivo
    if recording and out is not None:
        out.write(frame)

    # Captura teclas pressionadas
    key = cv2.waitKey(1) & 0xFF

    # Inicia a gravação ao pressionar 's'
    if key == ord('s') and not recording:
        recording = True
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"video_{now}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec para MP4
        out = cv2.VideoWriter(filename, fourcc, fps, (frame_width, frame_height))
        print(f"📹 Gravando: {filename}")

    # Para a gravação ao pressionar 'e'
    elif key == ord('e') and recording:
        recording = False
        out.release()
        out = None
        print("⏹️ Gravação encerrada.")

    # Sai do loop ao pressionar 'q'
    elif key == ord('q'):
        break

# Libera os recursos
cap.release()
if out:
    out.release()
cv2.destroyAllWindows()
