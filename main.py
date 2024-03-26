from fastapi import FastAPI
from router.routeBarang import app as barang_app
from router.routeTesting import app as testing_app
from router.routeUser import app as user_app
from router.routeJual import app as jual_app
from router.routeAdmin import app as admin_app

app = FastAPI()

app.mount("/apiBrg", barang_app)

# Cara Aksesnya 
# http://127.0.0.1:5500/apiTest/testing
app.mount("/apiTest", testing_app)
# jadi /apiTesting ini seperti parent URL

app.mount("/apiUser", user_app)
app.mount("/apiJual", jual_app)
app.mount("/apiAdmin", admin_app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=5500)


# Jikalau ad problem mysqlClient
# https://stackoverflow.com/questions/57461123/failed-to-build-mysqlclient-wheel-cannot-build-pip-install-mysqlclient-not-wor