from sqlite3 import connect
import time
from pytube import Playlist
from pytube import YouTube
from pathlib import Path
import shutil
import random
import os
import traceback
import requests
import json

class BD:

    def __init__(self):
        print("INIT")
        self.conn : connect = None
        self.cursor = None
        self.abrir_conexion()
        self.cursor = self.conn.cursor()
        self.crear_tabla_playlist()
        self.url_server = "http://localhost:8080/mp3"

    def abrir_conexion(self):
        self.conn = None
        self.conn = connect('ListaCanciones.db',check_same_thread=False)

    def hacer_commit(self):
        self.conn.commit()

    def ejecutar_query(self, query, par=None):
        if par == None:
            self.cursor.execute(query)
        else:
            self.cursor.execute(query,par)
        self.hacer_commit()

    def crear_tabla_playlist(self):
        query = '''
            CREATE TABLE IF NOT EXISTS playlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plain_url TEXT,
                video_id TEXT,
                nombre TEXT,
                artista TEXT
            )
        '''
        self.ejecutar_query(query)

    def insert_url(self, url:str):
        query = 'INSERT INTO playlist (plain_url) VALUES (?)'
        values = (url,)
        self.ejecutar_query(query,values)

    def update_cancion_info(self, plain_url: str, video_id: str, nom: str, art: str):
        query = '''
            UPDATE playlist
            SET video_id = ?, nombre = ?, artista = ?
            WHERE plain_url = ?
        '''
        values = (video_id, nom, art, plain_url)
        self.ejecutar_query(query, values)


    def generar_urls(self,playlist):
        playlist_urls : list = Playlist(playlist)
        for url in playlist_urls:
            existe = self.buscar_si_url_existe(url)

            print(f'Existe de Generar_url: {existe}')

            if (existe == None):
                self.insert_url(url)

    def buscar_si_url_existe(self, plain_url):
        query = 'SELECT id FROM playlist WHERE plain_url = ?'
        self.ejecutar_query(query, (plain_url,))
        video = self.cursor.fetchone()
        return video[0] if video else None
    
    def buscar_si_datos_guardados(self, plain_url):
        query = f'SELECT video_id FROM playlist WHERE plain_url = ?'
        self.ejecutar_query(query, (plain_url,))
        video_id = self.cursor.fetchone()
        return video_id[0] if video_id else None

    
    def buscar_info_cancion(self, video_id):
        query = f'SELECT nombre, artista FROM playlist WHERE video_id = ?'
        self.ejecutar_query(query, (video_id,))
        cancion = self.cursor.fetchall()
        return cancion[0]
    
    def seleccionar_url(self,id):
        query = f'SELECT plain_url FROM playlist WHERE id = ?'
        self.ejecutar_query(query, (id,))
        plain_url = self.cursor.fetchall()
        return plain_url[0][0]
    
    def total_url_playlist(self):
        query = 'SELECT COUNT(*) FROM playlist'
        self.ejecutar_query(query)
        total = self.cursor.fetchall()
        return total[0][0]
    
    def borrar_listado(self):
        query = 'DROP TABLE IF EXISTS playlist'
        self.ejecutar_query(query)


    def descargar_audio(self,plain_url:str):
        try:
            yt = YouTube(plain_url)
            #Descargar solo Audio
            video = yt.streams.filter(only_audio=True).first()
            art = yt.author
            nom = video.title
            video_id = yt.video_id

            existe = self.buscar_si_datos_guardados(plain_url)

            print(f'Existe de Descargar_audio {existe}')

            if (existe == None):
                self.update_cancion_info(plain_url, video_id, nom, art)
            destination = "canciones"

            # download the file
            out_file = video.download(output_path=destination)
            new_file = "canciones" + '\\' + str(video_id) + '.mp3'
            ruta = Path(out_file)
            ruta.rename(new_file)

        except Exception as e:
            print(f"Error al descargar el audio: {e}")
            traceback.print_exc()

    def hacer_todo_el_insert(self, pl, cant):
        if os.path.exists("canciones"):
            shutil.rmtree("canciones")

        path = os.path.join(os.getcwd(), "canciones")
        os.mkdir(path)

        self.generar_urls(pl)
        total = self.total_url_playlist()

        random_indices = random.sample(range(1, total + 1), cant)
        random_indices.sort()

        for index in random_indices:
            plain_url = self.seleccionar_url(index)
            self.descargar_audio(plain_url)
        
        self.vaciar_tabla_server()
        self.subir_a_server()

    def vaciar_tabla_server(self):
      try:
        response = requests.delete(self.url_server)
        print(response.text)
          
      except Exception as e:
          print(f'Error al procesar: {str(e)}')

    def subir_a_server(self):
        source_folder = 'canciones'
        files = os.listdir(source_folder)

        for file_name in files:
            # Construir la ruta completa al archivo
            file_path = os.path.join(source_folder, file_name)
            video_id = file_name.replace(".mp3", "")
            titulo, artista = self.buscar_info_cancion(video_id)
            mp3_file = open(file_path, "rb")

            # Crear el JSON con la información de la canción
            song_data = {
                "id" : video_id,
                "title": titulo,
                "artist": artista,
            }
            song_json = json.dumps(song_data)

            # Hacer la solicitud POST con form data
            files = {
                "file": ("file.mp3", mp3_file),
                "song": (None, song_json, "application/json")
            }

            response = requests.post(self.url_server, files=files)

            # Imprimir la respuesta del servidor
            print(response.text)

            # Cerrar el archivo MP3
            mp3_file.close()


if __name__ == "__main__":

    bd = BD()
    bd.hacer_todo_el_insert('https://www.youtube.com/playlist?list=PLyHdxlKXBjjlYLNeEm5_WYAIYPsEw-RBG', 2)