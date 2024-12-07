import cv2
import os
from datetime import datetime

def live_stream():
    # Inicializando a captura de vídeo
    cap = cv2.VideoCapture(0)  # Use 0 para a câmera padrão (USB)

    # Verificando se a câmera foi aberta com sucesso
    if not cap.isOpened():
        print("Erro ao abrir a câmera.")
        return

    print("Transmissão ao vivo iniciada. Pressione 'q' para sair.")

    while True:
        # Capturando o frame
        ret, frame = cap.read()

        # Verificando se o frame foi capturado corretamente
        if not ret:
            print("Falha ao capturar o frame.")
            break

        # Exibindo o frame em uma janela
        cv2.imshow('Live Stream', frame)

        # Sair ao pressionar 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Liberação dos recursos
    cap.release()
    cv2.destroyAllWindows()
    print("Transmissão ao vivo finalizada.")

def live_stream_rec():
    # Inicializando a captura de vídeo
    cap = cv2.VideoCapture(0)  # Use 0 para a câmera padrão (USB)

    # Verificando se a câmera foi aberta com sucesso
    if not cap.isOpened():
        print("Erro ao abrir a câmera.")
        return

    # Configurações da gravação
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    # Criando o diretório de resultados se ele não existir
    if not os.path.exists('results'):
        os.makedirs('results')

    # Gerando o nome do arquivo com base na data e hora atual
    now = datetime.now()
    filename = now.strftime("rec_%Y%m%d_%H%M%S.avi")
    filepath = os.path.join('results', filename)

    # Configurando o codec e inicializando o writer de vídeo
    fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Codec para AVI
    out = cv2.VideoWriter(filepath, fourcc, fps, (frame_width, frame_height))

    print(f"Gravação iniciada. Arquivo: {filepath}. Pressione 'q' para sair.")

    while True:
        # Capturando o frame
        ret, frame = cap.read()

        # Verificando se o frame foi capturado corretamente
        if not ret:
            print("Falha ao capturar o frame.")
            break

        # Gravando o frame no arquivo de vídeo
        out.write(frame)

        # Exibindo o frame em uma janela
        cv2.imshow('Live Stream Recording', frame)

        # Sair ao pressionar 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Liberação dos recursos
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print("Gravação finalizada.")

def live_stream_rec_ttl():
    pass