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
        self.borrar_canciones()
        self.borrar_listado()
        self.crear_tabla_cancion()
        self.crear_tabla_playlist()
        self.crear_tabla_current_pl()
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


    def crear_tabla_cancion(self):
        query = '''
            CREATE TABLE IF NOT EXISTS cancion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                artista TEXT
            )
        '''
        self.ejecutar_query(query)


    def crear_tabla_playlist(self):
        query = '''
            CREATE TABLE IF NOT EXISTS playlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT
            )
        '''
        self.ejecutar_query(query)

    def crear_tabla_current_pl(self):
        query = '''
            CREATE TABLE IF NOT EXISTS current_pl (
                pl TEXT
            )
        '''
        self.ejecutar_query(query)

    def insert_url(self, url:str):
        query = 'INSERT INTO playlist (url) VALUES (?)'
        values = (url,)
        self.ejecutar_query(query,values)

    def insert_cancion(self,nom:str, art:str):
        query = 'INSERT INTO cancion (nombre, artista) VALUES (?,?)'
        values = (nom, art)
        self.ejecutar_query(query,values)

    def insert_current_pl(self, pl):
        query = 'INSERT INTO current_pl (pl) VALUES (?)'
        values = (pl,)
        self.ejecutar_query(query,values)

    def generar_urls(self,playlist):
        playlist_urls : list = Playlist(playlist)
        for url in playlist_urls:
            self.insert_url(url)


    def selecionar_current_pl(self):
        query = 'SELECT pl FROM current_pl'
        self.ejecutar_query(query)
        pl = self.cursor.fetchone()
        return pl[0] if pl else None
    
    def selecionar_cancion(self,id):
        query = f'SELECT nombre, artista FROM cancion WHERE id = {id}'
        self.ejecutar_query(query)
        cancion = self.cursor.fetchall()
        return cancion[0]
    
    def seleccionar_id_cancion(self, nom, art):
        query = 'SELECT id FROM cancion WHERE nombre = ? AND artista = ?'
        self.ejecutar_query(query, (nom, art))
        id_can = self.cursor.fetchone()
        return id_can[0] if id_can else None
    
    def seleccionar_url(self,id):
        query = f'SELECT url FROM playlist WHERE id = {id}'
        self.ejecutar_query(query)
        url = self.cursor.fetchall()
        return url[0][0]
    
    def total_url_playlist(self):
        query = 'SELECT COUNT(*) FROM playlist'
        self.ejecutar_query(query)
        total = self.cursor.fetchall()
        return total[0][0]
    
    def borrar_listado(self):
        query = 'DROP TABLE IF EXISTS playlist'
        self.ejecutar_query(query)

    def borrar_canciones(self):
        query = 'DROP TABLE IF EXISTS cancion'
        self.ejecutar_query(query)
        if os.path.exists("canciones"):
            shutil.rmtree("canciones")


    def borrar_current_pl(self):
        query = 'DELETE FROM current_pl'
        self.ejecutar_query(query)


    def descargar_audio(self,url:str):
        try:
            yt = YouTube(url)

            #Descargar solo Audio
            video = yt.streams.filter(only_audio=True).first()
            art = yt.author
            nom = video.title
            self.insert_cancion(nom,art)
            id_can = self.seleccionar_id_cancion(nom, art)
            destination = "canciones"

            # download the file
            out_file = video.download(output_path=destination)
            new_file = "canciones" + '\\' + str(id_can) + '.mp3'
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
        self.borrar_current_pl()
        self.insert_current_pl(pl)
        total = self.total_url_playlist()


        
        random_indices = random.sample(range(1, total + 1), cant)
        random_indices.sort()

        for index in random_indices:
            url = self.seleccionar_url(index)
            self.descargar_audio(url)
        
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
            num = file_name.replace(".mp3", "")
            titulo, artista = self.selecionar_cancion(num)
            mp3_file = open(file_path, "rb")

            # Crear el JSON con la información de la canción
            song_data = {
                "id" : num,
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
    
        self.borrar_canciones()

if __name__ == "__main__":

    bd = BD()
    bd.hacer_todo_el_insert('https://www.youtube.com/playlist?list=PLyHdxlKXBjjlYLNeEm5_WYAIYPsEw-RBG', 5)