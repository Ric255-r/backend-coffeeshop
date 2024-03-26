# https://medium.com/@miladev95/fastapi-crud-with-mysql-b06d33601a38
# Referensi ^
# Start. Add the project root directory to the Python path
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modelsnya.model import Item
from koneksi import conn
# End. ini Supaya Bisa Import dari Folder Lain

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd
import json

app = FastAPI()

# Router
@app.get("/testing") 
def hello_world() :
    cursor = conn.cursor()
    query = "SELECT * FROM tbtesting"
    cursor.execute(query)

    # Extract column names dynamically
    column_names = [col[0] for col in cursor.description]

    # Debugging: Print the cursor description
    print("Cursor description:", cursor.description)

    item = cursor.fetchall() #Ambil Data

    # Debugging: Print the items fetched from the database
    print("Fetched items:", item)
    cursor.close()

    if not item :
        raise HTTPException(status_code=404, detail="Item g Ad")
    
    # Convert hasil Ke DataFrame pandas. Ini Cara Manual
    # df = pd.DataFrame(item, columns=["id", "nama_barang", "deskripsi", "harga"])
    # Cara Looping (buat var column_names sblm fetchall())
    df = pd.DataFrame(item, columns=column_names)

    # Convert the 'testarray' column to a list. biar ga returns jd string
    # df['testarray'] = df['testarray'].apply(json.loads)
    # Ini Cara Ngecek Kalau String Empty, ga ush ubah ke json
    df['testarray'] = df["testarray"].apply(lambda x: json.loads(x) if x.strip() else x)

    """
    The elements of the column are automatically passed as arguments to the function, 
    and the parameter (in this case, x) 
    is automatically filled with the corresponding element.
    So, when you use df['testarray'].apply() each element of the "testarray" column 
    is passed as an argument
    and the x parameter inside the function is automatically filled with the current 
    element being processed.
    """

    # Convert DatFrame ke JSON 
    json_data = df.to_dict(orient="records")

    # Return JSONNYa pakai JSONResponse FastAPi
    return JSONResponse(content=json_data)

    # Bisa cara key-value jg
    # return {
    #     "Hai" : json_data,
    # }

@app.post("/testing", response_model=Item) # Ambil dari Model yg d Import
def create_item(isi: Item) :
    cursor = conn.cursor()
    # Setiap Mau Insert Harus Di Execute & Commit
    query = "INSERT INTO tbtesting (nama_barang, deskripsi, harga) values(%s, %s, %s)"
    cursor.execute(query, (isi.nama_barang, isi.deskripsi, isi.harga)) 
    # Execute ini ada 2 argumen. pertama buat letak query, kedua isi argumen field
    conn.commit()
    # End Insert
    # Andai KAta mau taruh Banyak QUery(udh ins, lalu mw select), harus letak diatas cursor close
    # Contoh
    # cursor.execute("SELECT * FROM tbtesting ORDER BY id DESC LIMIT 1")
    # last_inserted_row = cursor.fetchone()
    cursor.close()
    return isi

@app.put("/testing/{item_id}", response_model=Item)
def update_item(item_id: int, isi: Item) :
    try:
        cursor = conn.cursor()
        query = "UPDATE tbtesting SET nama_barang=%s, deskripsi=%s, harga=%s WHERE id=%s"
        cursor.execute(query, (isi.nama_barang, isi.deskripsi, isi.harga, item_id))
        conn.commit()
        cursor.close()
        return {**isi.dict()}
    except Exception as e :
        return {
            "Error" : str(e)
        }
    
@app.delete("/testing/{item_id}")
def delete_item(item_id: int) :
    try: 
        cursor = conn.cursor()
        query = "DELETE FROM tbtesting WHERE id = %s"
        cursor.execute(query, (item_id,)) # Harus dikoma stelah item_id, gtw knp
        conn.commit()
        cursor.close()
        return {
            "message": "Sukses Hapus"
        }
    except Exception as e :
        return {
            "Error": str(e)
        }

# Ini g perlu lg. udh didefine di main.py. supaya bisa akses berbagai route
# if __name__ == "__main__" :
#     import uvicorn
#     uvicorn.run(app, host="localhost", port=5500)
