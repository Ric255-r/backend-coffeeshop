from pydantic import BaseModel

class Item(BaseModel) :
    nama_barang : str
    deskripsi: str = None
    harga: float
